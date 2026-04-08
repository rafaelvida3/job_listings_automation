from __future__ import annotations

import logging
import random
from typing import Optional
from urllib.parse import urlparse

from playwright.sync_api import Locator, Page, TimeoutError

from .models import ListingData
from .pagination import PaginationNavigator
from .selectors import (DETAIL_DESCRIPTION_SELECTOR, DETAIL_TITLE_SELECTOR,
                        LISTING_CARD_SELECTOR, LISTING_LINK_SELECTOR)
from .settings import AppSettings
from .text_utils import clean_multiline_text, clean_single_line
from .url_utils import normalize_listing_url


class ListingExtractor:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        pagination_navigator: PaginationNavigator,
        random_generator: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.pagination_navigator = pagination_navigator
        self.random_generator = random_generator or random.Random()

    def get_base_origin(self, url: str) -> str:
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            return f"{parsed_url.scheme}://{parsed_url.netloc}"

        return "https://example.com"

    def get_locator_text(self, locator: Locator, multiline: bool = False) -> str:
        try:
            if locator.count() == 0:
                return ""

            raw_text = locator.first.inner_text(timeout=5_000)
            return clean_multiline_text(raw_text) if multiline else clean_single_line(raw_text)
        except Exception:
            return ""

    def simulate_description_scroll(self, page: Page) -> None:
        try:
            container = page.locator(DETAIL_DESCRIPTION_SELECTOR).first
            if container.count() == 0:
                return

            scroll_rounds = self.random_generator.randint(2, 4)
            for _ in range(scroll_rounds):
                scroll_amount = self.random_generator.randint(200, 500)
                container.evaluate("(element, amount) => { element.scrollTop += amount; }", scroll_amount)
                page.wait_for_timeout(self.random_generator.randint(800, 1800))
        except Exception:
            return

    def click_listing_card(self, card: Locator, listing_id: str) -> None:
        link_locator = card.locator(LISTING_LINK_SELECTOR)

        try:
            if link_locator.count() > 0:
                link_locator.first.scroll_into_view_if_needed()
                link_locator.first.click(timeout=10_000)
            else:
                card.scroll_into_view_if_needed()
                card.click(timeout=10_000)

            self.logger.info("Clicked listing card %s", listing_id or "<unknown>")
        except Exception as error:
            self.logger.warning(
                "Standard click failed for listing %s. Trying script click. Error: %s",
                listing_id or "<unknown>",
                error,
            )
            if link_locator.count() > 0:
                link_locator.first.evaluate("(element) => element.click()")
            else:
                card.evaluate("(element) => element.click()")

    def extract_listing_data(
        self,
        page: Page,
        card: Locator,
        source_url: str,
        base_origin: str,
    ) -> Optional[ListingData]:
        listing_id = card.get_attribute("data-occludable-job-id") or card.get_attribute("data-job-id") or ""

        card_link_locator = card.locator(LISTING_LINK_SELECTOR)
        fallback_title = self.get_locator_text(card_link_locator)
        fallback_link = ""

        try:
            if card_link_locator.count() > 0:
                fallback_link = normalize_listing_url(
                    card_link_locator.first.get_attribute("href"),
                    base_origin=base_origin,
                )
        except Exception:
            fallback_link = ""

        self.click_listing_card(card, listing_id)
        page.wait_for_timeout(1_200)

        try:
            page.wait_for_selector(DETAIL_TITLE_SELECTOR, timeout=self.settings.detail_load_timeout_ms)
        except TimeoutError:
            self.logger.warning("Detail title did not load for listing %s", listing_id or "<unknown>")

        page.wait_for_timeout(
            self.random_generator.randint(
                self.settings.min_reading_delay_ms,
                self.settings.max_reading_delay_ms,
            )
        )
        self.simulate_description_scroll(page)
        page.wait_for_timeout(
            self.random_generator.randint(
                self.settings.min_reading_delay_ms,
                self.settings.max_reading_delay_ms,
            )
        )

        detail_title_locator = page.locator(DETAIL_TITLE_SELECTOR)
        detail_description_locator = page.locator(DETAIL_DESCRIPTION_SELECTOR)

        title = self.get_locator_text(detail_title_locator) or fallback_title
        description = self.get_locator_text(detail_description_locator, multiline=True)

        detail_link = ""
        try:
            if detail_title_locator.count() > 0:
                detail_link = normalize_listing_url(
                    detail_title_locator.first.get_attribute("href"),
                    base_origin=base_origin,
                )
        except Exception:
            detail_link = ""

        link = detail_link or fallback_link

        if not title and not link:
            self.logger.warning("Skipping card because neither title nor link was found.")
            return None

        return ListingData(
            listing_id=listing_id,
            title=title or "Untitled listing",
            link=link or "Link not found",
            description=description or "Description not found",
            source_url=source_url,
        )

    def collect_listings_from_current_page(
        self,
        page: Page,
        listings: list[ListingData],
        seen_keys: set[str],
        source_url: str,
    ) -> None:
        current_page_number = self.pagination_navigator.get_current_page_number(page)
        self.pagination_navigator.load_all_listing_cards(page)
        base_origin = self.get_base_origin(source_url)

        initial_cards = page.locator(LISTING_CARD_SELECTOR)
        total_cards = initial_cards.count()
        self.logger.info(
            "Starting extraction for %s cards on page %s.",
            total_cards,
            current_page_number,
        )

        for index in range(total_cards):
            try:
                current_cards = page.locator(LISTING_CARD_SELECTOR)
                current_count = current_cards.count()
                if index >= current_count:
                    self.logger.info(
                        "Card index %s no longer exists after DOM update on page %s. Current count: %s",
                        index,
                        current_page_number,
                        current_count,
                    )
                    break

                card = current_cards.nth(index)
                card.scroll_into_view_if_needed(timeout=5_000)
                page.wait_for_timeout(500)

                listing_data = self.extract_listing_data(page, card, source_url, base_origin)
                if listing_data is None:
                    continue

                unique_key = listing_data.listing_id or listing_data.link
                if unique_key in seen_keys:
                    self.logger.info("Skipping duplicate listing %s", unique_key)
                    continue

                seen_keys.add(unique_key)
                listings.append(listing_data)
                self.logger.info(
                    "Collected %s listings in total | current page %s | %s",
                    len(listings),
                    current_page_number,
                    listing_data.title,
                )
            except Exception as error:
                self.logger.exception(
                    "Error while processing card %s on page %s: %s",
                    index + 1,
                    current_page_number,
                    error,
                )
                page.wait_for_timeout(1_000)