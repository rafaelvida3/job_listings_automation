from __future__ import annotations

import logging
import re

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, TimeoutError

from .selectors import DEFAULT_SELECTOR_PROFILE, SelectorProfile
from .settings import AppSettings
from .text_utils import clean_single_line

RECOVERABLE_PAGINATION_EXCEPTIONS = (PlaywrightError, RuntimeError)
PAGE_STATE_PATTERNS = (
    re.compile(r"Page\s+(\d+)\s+of\s+(\d+)", re.IGNORECASE),
    re.compile(r"Página\s+(\d+)\s+de\s+(\d+)", re.IGNORECASE),
)


class PaginationNavigator:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        selectors: SelectorProfile = DEFAULT_SELECTOR_PROFILE,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.selectors = selectors

    def get_locator_text(self, locator: Locator) -> str:
        try:
            if locator.count() == 0:
                return ""
            return clean_single_line(locator.first.inner_text(timeout=5_000))
        except RECOVERABLE_PAGINATION_EXCEPTIONS:
            return ""

    def has_empty_search_results(self, page: Page) -> bool:
        for text in self.selectors.empty_results_texts:
            locator = page.get_by_text(text, exact=False)
            if locator.count() == 0:
                continue

            try:
                if locator.first.is_visible():
                    self.logger.info("Empty search results detected: %s", text)
                    return True
            except RECOVERABLE_PAGINATION_EXCEPTIONS:
                continue

        return False

    def get_current_page_number(self, page: Page) -> int:
        current_page, _ = self._parse_page_state(page)
        return current_page

    def get_total_pages(self, page: Page) -> int:
        _, total_pages = self._parse_page_state(page)
        return total_pages

    def safe_scroll_last_card(self, page: Page, retries: int | None = None) -> bool:
        total_retries = retries or self.settings.stale_scroll_retries

        for attempt in range(1, total_retries + 1):
            try:
                cards = page.locator(self.selectors.listing_card)
                count = cards.count()
                if count == 0:
                    return False

                last_card = cards.nth(count - 1)
                last_card.scroll_into_view_if_needed(timeout=5_000)
                return True
            except RECOVERABLE_PAGINATION_EXCEPTIONS as error:
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
            cards = page.locator(self.selectors.listing_card)
            current_count = cards.count()
            self.logger.info("Scroll round %s | found %s cards", round_index + 1, current_count)

            if current_count == 0:
                page.mouse.wheel(0, 1_500)
                page.wait_for_timeout(1_500)
                continue

            stable_rounds = stable_rounds + 1 if current_count == previous_count else 0
            previous_count = current_count

            if not self.safe_scroll_last_card(page):
                page.mouse.wheel(0, 1_800)
                page.wait_for_timeout(1_200)
                continue

            page.mouse.wheel(0, 1_800)
            page.wait_for_timeout(1_500)

            if stable_rounds >= 2:
                self.logger.info("No new cards detected. Stopping scroll.")
                break

        final_count = page.locator(self.selectors.listing_card).count()
        self.logger.info("Final card count: %s", final_count)
        return final_count

    def go_to_next_results_page(self, page: Page) -> bool:
        next_button = page.locator(self.selectors.next_page_button)
        if next_button.count() == 0:
            self.logger.info("Next page button not found. Assuming last page.")
            return False

        previous_page_number = self.get_current_page_number(page)
        previous_page_state = self.get_locator_text(page.locator(self.selectors.pagination_state))

        next_button.first.scroll_into_view_if_needed(timeout=5_000)
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

                    const englishMatch = currentText.match(/Page\s+(\d+)\s+of\s+(\d+)/i)
                    if (englishMatch) {
                        return Number(englishMatch[1]) !== previousPageNumber
                    }

                    const translatedMatch = currentText.match(/Página\s+(\d+)\s+de\s+(\d+)/i)
                    if (translatedMatch) {
                        return Number(translatedMatch[1]) !== previousPageNumber
                    }

                    return false
                }
                """,
                arg={
                    "selector": self.selectors.pagination_state,
                    "previousState": previous_page_state,
                    "previousPageNumber": previous_page_number,
                },
                timeout=self.settings.page_load_timeout_ms,
            )
        except TimeoutError:
            self.logger.warning(
                "Pagination state did not change after clicking the next page button."
            )
            return False

        page.wait_for_selector(
            self.selectors.listing_card,
            timeout=self.settings.page_load_timeout_ms,
        )
        page.wait_for_timeout(1_500)

        current_page_number = self.get_current_page_number(page)
        self.logger.info(
            "Moved from page %s to page %s.",
            previous_page_number,
            current_page_number,
        )
        return current_page_number > previous_page_number

    def _parse_page_state(self, page: Page) -> tuple[int, int]:
        page_state_text = self.get_locator_text(page.locator(self.selectors.pagination_state))
        for pattern in PAGE_STATE_PATTERNS:
            match = pattern.search(page_state_text)
            if match:
                return int(match.group(1)), int(match.group(2))
        return 1, 1
