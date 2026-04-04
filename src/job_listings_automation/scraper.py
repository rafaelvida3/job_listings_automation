from __future__ import annotations

import logging
import random
import re
from pathlib import Path
from typing import Optional

from playwright.sync_api import (BrowserContext, Locator, Page, TimeoutError,
                                 sync_playwright)

from .exporters import export_listings_to_text
from .models import ListingData
from .selectors import (DETAIL_DESCRIPTION_SELECTOR, DETAIL_TITLE_SELECTOR,
                        EMPTY_RESULTS_TEXTS, LISTING_CARD_SELECTOR,
                        LISTING_LINK_SELECTOR, NEXT_PAGE_BUTTON_SELECTOR,
                        PAGINATION_STATE_SELECTOR)
from .settings import AppSettings
from .text_utils import clean_multiline_text, clean_single_line
from .url_utils import normalize_listing_url


class ListingsScraper:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        profile_dir: Path,
        output_dir: Path,
        random_generator: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.profile_dir = profile_dir
        self.output_dir = output_dir
        self.random_generator = random_generator or random.Random()

    def run(self, search_urls: list[str], run_timestamp: str) -> Path:
        self.logger.info("Scraper started.")
        self.logger.info("Configured search URLs: %s", len(search_urls))

        page: Optional[Page] = None
        context: Optional[BrowserContext] = None

        try:
            with sync_playwright() as playwright:
                context = playwright.chromium.launch_persistent_context(
                    user_data_dir=str(self.profile_dir),
                    headless=self.settings.headless,
                    slow_mo=self.settings.slow_mo_ms,
                    args=["--start-maximized"],
                    viewport={"width": 1440, "height": 900},
                )
                context.set_default_timeout(self.settings.page_load_timeout_ms)
                page = context.pages[0] if context.pages else context.new_page()

                listings: list[ListingData] = []
                seen_keys: set[str] = set()
                has_checked_access = False

                for search_index, search_url in enumerate(search_urls, start=1):
                    self.logger.info("Opening source URL %s/%s", search_index, len(search_urls))
                    page.goto(search_url, wait_until="domcontentloaded")

                    if not has_checked_access:
                        self.wait_for_access_and_listing_list(page)
                        has_checked_access = True
                    else:
                        self.wait_for_listing_list(page)

                    total_pages = self.get_total_pages(page)
                    self.logger.info(
                        "Detected %s result page(s) for source URL %s.",
                        total_pages,
                        search_index,
                    )

                    while True:
                        current_page_number = self.get_current_page_number(page)
                        self.logger.info(
                            "Processing source URL %s/%s | result page %s of %s.",
                            search_index,
                            len(search_urls),
                            current_page_number,
                            total_pages,
                        )

                        if self.has_empty_search_results(page):
                            self.logger.info(
                                "No exact matches for this search. Recommended cards will be ignored."
                            )
                            break

                        self.collect_listings_from_current_page(
                            page,
                            listings,
                            seen_keys,
                            search_url,
                            self.get_base_origin(search_url),
                        )

                        if current_page_number >= total_pages:
                            self.logger.info("Reached the last result page for current source URL.")
                            break

                        moved_to_next_page = self.go_to_next_results_page(page)
                        if not moved_to_next_page:
                            self.logger.info("Could not move to the next page. Stopping pagination loop.")
                            break

                text_file = export_listings_to_text(
                    listings=listings,
                    output_dir=self.output_dir,
                    run_timestamp=run_timestamp,
                    logger=self.logger,
                    source_urls=search_urls,
                )

                self.logger.info("Scraper finished successfully.")
                return text_file

        except Exception as error:
            self.logger.exception("Fatal error during execution: %s", error)
            self.take_error_screenshot(page, run_timestamp)
            raise
        finally:
            self.close_context_safely(context)

    def get_base_origin(self, url: str) -> str:
        from urllib.parse import urlparse

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
        
    def has_empty_search_results(self, page: Page) -> bool:
        for text in EMPTY_RESULTS_TEXTS:
            locator = page.get_by_text(text, exact=False)

            if locator.count() == 0:
                continue

            try:
                if locator.first.is_visible():
                    self.logger.info("Empty search results detected: %s", text)
                    return True
            except Exception:
                continue

        return False

    def wait_for_access_and_listing_list(self, page: Page) -> None:
        try:
            page.wait_for_selector(LISTING_CARD_SELECTOR, timeout=15_000)
            self.logger.info("Listing list found without manual confirmation.")
            return
        except TimeoutError:
            self.logger.info("Listing list not found quickly. Manual confirmation may be required.")

        input(
            "\nOpen the browser session, complete any required access steps, "
            "then press Enter here to continue...\n"
        )
        page.wait_for_selector(LISTING_CARD_SELECTOR, timeout=60_000)
        self.logger.info("Listing list found after manual confirmation.")

    def wait_for_listing_list(self, page: Page) -> None:
        page.wait_for_selector(LISTING_CARD_SELECTOR, timeout=self.settings.page_load_timeout_ms)
        self.logger.info("Listing list is ready on the current source URL.")

    def safe_scroll_last_card(self, page: Page, retries: int | None = None) -> bool:
        total_retries = retries or self.settings.stale_scroll_retries

        for attempt in range(1, total_retries + 1):
            try:
                cards = page.locator(LISTING_CARD_SELECTOR)
                count = cards.count()
                if count == 0:
                    return False

                last_card = cards.nth(count - 1)
                last_card.scroll_into_view_if_needed(timeout=5_000)
                return True
            except Exception as error:
                self.logger.warning(
                    "Failed to scroll last card on attempt %s/%s: %s",
                    attempt,
                    total_retries,
                    error,
                )
                page.wait_for_timeout(700)

        return False

    def load_all_listing_cards(self, page: Page) -> int:
        previous_count = -1
        stable_rounds = 0

        for round_index in range(self.settings.max_scroll_rounds):
            cards = page.locator(LISTING_CARD_SELECTOR)
            current_count = cards.count()
            self.logger.info("Scroll round %s | found %s cards", round_index + 1, current_count)

            if current_count == 0:
                page.mouse.wheel(0, 1500)
                page.wait_for_timeout(1500)
                continue

            stable_rounds = stable_rounds + 1 if current_count == previous_count else 0
            previous_count = current_count

            if not self.safe_scroll_last_card(page):
                page.mouse.wheel(0, 1800)
                page.wait_for_timeout(1200)
                continue

            page.mouse.wheel(0, 1800)
            page.wait_for_timeout(1500)

            if stable_rounds >= 2:
                self.logger.info("No new cards detected. Stopping scroll.")
                break

        final_count = page.locator(LISTING_CARD_SELECTOR).count()
        self.logger.info("Final card count: %s", final_count)
        return final_count

    def get_current_page_number(self, page: Page) -> int:
        page_state_text = self.get_locator_text(page.locator(PAGINATION_STATE_SELECTOR))
        page_match = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", page_state_text, re.IGNORECASE)
        if page_match:
            return int(page_match.group(1))

        translated_match = re.search(r"Página\s+(\d+)\s+de\s+(\d+)", page_state_text, re.IGNORECASE)
        if translated_match:
            return int(translated_match.group(1))

        return 1

    def get_total_pages(self, page: Page) -> int:
        page_state_text = self.get_locator_text(page.locator(PAGINATION_STATE_SELECTOR))
        page_match = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", page_state_text, re.IGNORECASE)
        if page_match:
            return int(page_match.group(2))

        translated_match = re.search(r"Página\s+(\d+)\s+de\s+(\d+)", page_state_text, re.IGNORECASE)
        if translated_match:
            return int(translated_match.group(2))

        return 1

    def go_to_next_results_page(self, page: Page) -> bool:
        next_button = page.locator(NEXT_PAGE_BUTTON_SELECTOR)
        if next_button.count() == 0:
            self.logger.info("Next page button not found. Assuming last page.")
            return False

        previous_page_number = self.get_current_page_number(page)
        previous_page_state = self.get_locator_text(page.locator(PAGINATION_STATE_SELECTOR))

        next_button.first.scroll_into_view_if_needed()
        page.wait_for_timeout(800)
        next_button.first.click(timeout=10_000)

        try:
            page.wait_for_function(
                r"""
                ({ selector, previousState, previousPageNumber }) => {
                    const stateElement = document.querySelector(selector)
                    if (!stateElement) {
                        return false
                    }

                    const currentText = stateElement.innerText.trim()
                    if (currentText && currentText !== previousState) {
                        return true
                    }

                    const pageMatch = currentText.match(/Page\s+(\d+)\s+of\s+(\d+)/i)
                    if (pageMatch) {
                        return Number(pageMatch[1]) !== previousPageNumber
                    }

                    const translatedMatch = currentText.match(/Página\s+(\d+)\s+de\s+(\d+)/i)
                    if (translatedMatch) {
                        return Number(translatedMatch[1]) !== previousPageNumber
                    }

                    return false
                }
                """,
                arg={
                    "selector": PAGINATION_STATE_SELECTOR,
                    "previousState": previous_page_state,
                    "previousPageNumber": previous_page_number,
                },
                timeout=self.settings.page_load_timeout_ms,
            )
        except TimeoutError:
            self.logger.warning("Pagination state did not change after clicking the next page button.")
            return False

        page.wait_for_selector(LISTING_CARD_SELECTOR, timeout=self.settings.page_load_timeout_ms)
        page.wait_for_timeout(1_500)

        current_page_number = self.get_current_page_number(page)
        self.logger.info("Moved from page %s to page %s.", previous_page_number, current_page_number)
        return current_page_number > previous_page_number

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
                fallback_link = normalize_listing_url(card_link_locator.first.get_attribute("href"), base_origin=base_origin)
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
                detail_link = normalize_listing_url(detail_title_locator.first.get_attribute("href"), base_origin=base_origin)
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
        base_origin: str,
    ) -> None:
        current_page_number = self.get_current_page_number(page)
        self.load_all_listing_cards(page)

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

    def take_error_screenshot(self, page: Optional[Page], run_timestamp: str) -> None:
        if page is None:
            return

        try:
            screenshot_file = self.output_dir.parent / "logs" / f"job_listings_error_{run_timestamp}.png"
            page.screenshot(path=str(screenshot_file), full_page=True)
            self.logger.info("Error screenshot saved to %s", screenshot_file)
        except Exception as error:
            self.logger.warning("Failed to save error screenshot: %s", error)

    def close_context_safely(self, context: Optional[BrowserContext]) -> None:
        if context is None:
            return

        try:
            context.close()
        except Exception as error:
            self.logger.warning("Failed to close browser context cleanly: %s", error)
