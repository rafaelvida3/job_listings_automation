from __future__ import annotations

import logging
import re

from playwright.sync_api import Locator, Page, TimeoutError

from .selectors import (EMPTY_RESULTS_TEXTS, LISTING_CARD_SELECTOR,
                        NEXT_PAGE_BUTTON_SELECTOR, PAGINATION_STATE_SELECTOR)
from .settings import AppSettings
from .text_utils import clean_single_line


class PaginationNavigator:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
    ) -> None:
        self.settings = settings
        self.logger = logger

    def get_locator_text(self, locator: Locator) -> str:
        try:
            if locator.count() == 0:
                return ""

            return clean_single_line(locator.first.inner_text(timeout=5_000))
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