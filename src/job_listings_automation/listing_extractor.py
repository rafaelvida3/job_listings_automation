from __future__ import annotations

import logging
import random
from typing import Any, cast
from urllib.parse import urlparse

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, TimeoutError

from .models import ListingData
from .pagination import PaginationNavigator
from .selectors import DEFAULT_SELECTOR_PROFILE, SelectorProfile
from .settings import AppSettings
from .text_utils import clean_multiline_text, clean_single_line
from .url_utils import normalize_listing_url

RECOVERABLE_EXTRACTION_EXCEPTIONS = (PlaywrightError, RuntimeError)


class ListingExtractor:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        pagination_navigator: PaginationNavigator,
        selectors: SelectorProfile = DEFAULT_SELECTOR_PROFILE,
        random_generator: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.pagination_navigator = pagination_navigator
        self.selectors = selectors
        self.random_generator = random_generator or random.Random()

    def get_base_origin(self, url: str) -> str:
        parsed_url = urlparse(url)
        if parsed_url.scheme and parsed_url.netloc:
            return f"{parsed_url.scheme}://{parsed_url.netloc}"
        return ""

    def get_locator_text(self, locator: Locator, *, multiline: bool = False) -> str:
        try:
            if locator.count() == 0:
                return ""

            raw_text = locator.first.inner_text(timeout=5_000)
        except RECOVERABLE_EXTRACTION_EXCEPTIONS:
            return ""

        if multiline:
            return clean_multiline_text(raw_text)
        return clean_single_line(raw_text)

    def get_first_attribute(
        self, locator: Locator, attribute_name: str
    ) -> str | None:
        try:
            if locator.count() == 0:
                return None

            value = locator.first.get_attribute(attribute_name)
            return cast(str | None, value)

        except RECOVERABLE_EXTRACTION_EXCEPTIONS:
            return None

    def get_listing_id(self, card: Any) -> str:
        return (
            card.get_attribute("data-occludable-job-id")
            or card.get_attribute("data-job-id")
            or ""
        )

    def simulate_description_scroll(self, page: Page) -> None:
        try:
            container = page.locator(self.selectors.detail_description).first
            if container.count() == 0:
                return

            for _ in range(self.random_generator.randint(2, 4)):
                scroll_amount = self.random_generator.randint(200, 500)
                container.evaluate(
                    "(element, amount) => { element.scrollTop += amount; }",
                    scroll_amount,
                )
                page.wait_for_timeout(self.random_generator.randint(800, 1_800))
        except RECOVERABLE_EXTRACTION_EXCEPTIONS as error:
            self.logger.debug("Skipping description scroll due to recoverable error: %s", error)

    def click_listing_card(self, card: Any, listing_id: str) -> None:
        link_locator = card.locator(self.selectors.listing_link)

        try:
            if link_locator.count() > 0:
                link_locator.first.scroll_into_view_if_needed(timeout=5_000)
                link_locator.first.click(timeout=10_000)
            else:
                card.scroll_into_view_if_needed(timeout=5_000)
                card.click(timeout=10_000)

            self.logger.info("Clicked listing card %s", listing_id or "<unknown>")
            return
        except RECOVERABLE_EXTRACTION_EXCEPTIONS as error:
            self.logger.warning(
                "Standard click failed for listing %s. Trying script click. Error: %s",
                listing_id or "<unknown>",
                error,
            )

        if link_locator.count() > 0:
            link_locator.first.evaluate("(element) => element.click()")
        else:
            card.evaluate("(element) => element.click()")

    def get_fallback_listing_data(
        self,
        card: Any,
        base_origin: str,
    ) -> tuple[str | None, str | None]:
        card_link_locator = card.locator(self.selectors.listing_link)
        fallback_title = self.get_locator_text(card_link_locator) or None
        fallback_link = normalize_listing_url(
            self.get_first_attribute(card_link_locator, "href"),
            base_origin=base_origin,
        )
        return fallback_title, fallback_link or None

    def get_detail_link(self, detail_title_locator: Locator, base_origin: str) -> str | None:
        detail_link = normalize_listing_url(
            self.get_first_attribute(detail_title_locator, "href"),
            base_origin=base_origin,
        )
        return detail_link or None

    def extract_listing_data(
        self,
        page: Page,
        card: Any,
        source_url: str,
        base_origin: str,
    ) -> ListingData | None:
        listing_id = self.get_listing_id(card)
        fallback_title, fallback_link = self.get_fallback_listing_data(card, base_origin)

        self.click_listing_card(card, listing_id)
        page.wait_for_timeout(1_200)

        try:
            page.wait_for_selector(
                self.selectors.detail_title,
                timeout=self.settings.detail_load_timeout_ms,
            )
        except TimeoutError:
            self.logger.warning(
                "Detail title did not load for listing %s",
                listing_id or "<unknown>",
            )

        self._simulate_reading_delay(page)
        self.simulate_description_scroll(page)
        self._simulate_reading_delay(page)

        detail_title_locator = page.locator(self.selectors.detail_title)
        detail_description_locator = page.locator(self.selectors.detail_description)

        title = self.get_locator_text(detail_title_locator) or fallback_title
        description_text = self.get_locator_text(detail_description_locator, multiline=True)
        description = description_text or None
        detail_link = self.get_detail_link(detail_title_locator, base_origin)
        link = detail_link or fallback_link

        if not title and not link:
            self.logger.warning("Skipping card because neither title nor link was found.")
            return None

        return ListingData(
            listing_id=listing_id,
            title=title,
            link=link,
            description=description,
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

        cards = page.locator(self.selectors.listing_card)
        total_cards = cards.count()
        self.logger.info(
            "Starting extraction for %s cards on page %s.",
            total_cards,
            current_page_number,
        )

        for index in range(total_cards):
            try:
                self._collect_single_card(
                    page=page,
                    listings=listings,
                    seen_keys=seen_keys,
                    source_url=source_url,
                    base_origin=base_origin,
                    current_page_number=current_page_number,
                    index=index,
                )
            except IndexError:
                self.logger.info(
                    "Card index %s no longer exists after DOM update on page %s.",
                    index,
                    current_page_number,
                )
                break
            except Exception as error:
                self.logger.warning(
                    "Failed to extract card %s on page %s: %s",
                    index,
                    current_page_number,
                    error,
                )
                page.wait_for_timeout(1_000)

    def _collect_single_card(
        self,
        page: Page,
        listings: list[ListingData],
        seen_keys: set[str],
        source_url: str,
        base_origin: str,
        current_page_number: int,
        index: int,
    ) -> None:
        current_cards = page.locator(self.selectors.listing_card)
        current_count = current_cards.count()
        if index >= current_count:
            raise IndexError(index)

        card = current_cards.nth(index)
        card.scroll_into_view_if_needed(timeout=5_000)
        page.wait_for_timeout(500)

        listing_data = self.extract_listing_data(page, card, source_url, base_origin)
        if listing_data is None:
            return

        unique_key = listing_data.listing_id or listing_data.link
        if not unique_key:
            self.logger.info("Skipping listing without a stable unique key.")
            return

        if unique_key in seen_keys:
            self.logger.info("Skipping duplicate listing %s", unique_key)
            return

        seen_keys.add(unique_key)
        listings.append(listing_data)
        self.logger.info(
            "Collected %s listings in total | current page %s | %s",
            len(listings),
            current_page_number,
            listing_data.title or listing_data.link or "<unknown>",
        )

    def _simulate_reading_delay(self, page: Page) -> None:
        page.wait_for_timeout(
            self.random_generator.randint(
                self.settings.min_reading_delay_ms,
                self.settings.max_reading_delay_ms,
            )
        )
