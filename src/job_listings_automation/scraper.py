from __future__ import annotations

import logging
import random
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, sync_playwright
from playwright.sync_api import Error as PlaywrightError

from .browser_session import BrowserSession
from .exporters import OutputFormat, export_listings
from .listing_extractor import ListingExtractor
from .models import ListingData
from .pagination import PaginationNavigator
from .selectors import DEFAULT_SELECTOR_PROFILE, SelectorProfile
from .settings import AppSettings

RECOVERABLE_SCREENSHOT_EXCEPTIONS = (PlaywrightError, RuntimeError, OSError)


class ListingsScraper:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        profile_dir: Path,
        output_dir: Path,
        selectors: SelectorProfile = DEFAULT_SELECTOR_PROFILE,
        random_generator: random.Random | None = None,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.profile_dir = profile_dir
        self.output_dir = output_dir
        self.selectors = selectors
        self.random_generator = random_generator or random.Random()

        self.browser_session = BrowserSession(
            settings=settings,
            logger=logger,
            profile_dir=profile_dir,
            selectors=selectors,
        )
        self.pagination_navigator = PaginationNavigator(
            settings=settings,
            logger=logger,
            selectors=selectors,
        )
        self.listing_extractor = ListingExtractor(
            settings=settings,
            logger=logger,
            pagination_navigator=self.pagination_navigator,
            selectors=selectors,
            random_generator=self.random_generator,
        )

    def run(
        self,
        search_urls: list[str],
        run_timestamp: str,
        output_format: OutputFormat = "txt",
    ) -> Path:
        self.logger.info("Scraper started.")
        self.logger.info("Configured search URLs: %s", len(search_urls))

        page: Page | None = None
        context: BrowserContext | None = None

        try:
            with sync_playwright() as playwright:
                context, page = self.browser_session.create_context(playwright)
                listings, seen_keys = self._collect_all_listings(page, search_urls)
                output_file = export_listings(
                    listings=listings,
                    output_dir=self.output_dir,
                    run_timestamp=run_timestamp,
                    logger=self.logger,
                    source_urls=search_urls,
                    output_format=output_format,
                )
                self.logger.info("Scraper finished successfully.")
                return output_file
        except Exception as error:
            self.logger.exception("Fatal error during execution: %s", error)
            self.take_error_screenshot(page, run_timestamp)
            raise
        finally:
            self.browser_session.close_context_safely(context)

    def take_error_screenshot(self, page: Page | None, run_timestamp: str) -> None:
        if page is None or not self.settings.take_screenshot_on_error:
            return

        try:
            screenshot_file = (
                self.output_dir.parent / "logs" / f"job_listings_error_{run_timestamp}.png"
            )
            page.screenshot(path=str(screenshot_file), full_page=True)
            self.logger.info("Error screenshot saved to %s", screenshot_file)
        except RECOVERABLE_SCREENSHOT_EXCEPTIONS as error:
            self.logger.warning("Failed to save error screenshot: %s", error)

    def _collect_all_listings(
        self,
        page: Page,
        search_urls: list[str],
    ) -> tuple[list[ListingData], set[str]]:
        listings: list[ListingData] = []
        seen_keys: set[str] = set()
        has_checked_access = False

        for search_index, search_url in enumerate(search_urls, start=1):
            self._open_search_url(
                page=page,
                search_url=search_url,
                search_index=search_index,
                total_sources=len(search_urls),
                has_checked_access=has_checked_access,
            )
            has_checked_access = True
            self._collect_from_search_url(
                page=page,
                search_url=search_url,
                search_index=search_index,
                total_sources=len(search_urls),
                listings=listings,
                seen_keys=seen_keys,
            )

        return listings, seen_keys

    def _open_search_url(
        self,
        page: Page,
        search_url: str,
        search_index: int,
        total_sources: int,
        has_checked_access: bool,
    ) -> None:
        self.logger.info("Opening source URL %s/%s", search_index, total_sources)
        page.goto(search_url, wait_until="domcontentloaded")

        if has_checked_access:
            self.browser_session.wait_for_listing_list(page)
            return

        self.browser_session.wait_for_access_and_listing_list(page)

    def _collect_from_search_url(
        self,
        page: Page,
        search_url: str,
        search_index: int,
        total_sources: int,
        listings: list[ListingData],
        seen_keys: set[str],
    ) -> None:
        total_pages = self.pagination_navigator.get_total_pages(page)
        self.logger.info(
            "Detected %s result page(s) for source URL %s.",
            total_pages,
            search_index,
        )

        while True:
            current_page_number = self.pagination_navigator.get_current_page_number(page)
            self.logger.info(
                "Processing source URL %s/%s | result page %s of %s.",
                search_index,
                total_sources,
                current_page_number,
                total_pages,
            )

            if self.pagination_navigator.has_empty_search_results(page):
                self.logger.info(
                    "No exact matches for this search. Recommended cards will be ignored."
                )
                break

            self.listing_extractor.collect_listings_from_current_page(
                page=page,
                listings=listings,
                seen_keys=seen_keys,
                source_url=search_url,
            )

            if self._should_stop_pagination(current_page_number, total_pages):
                break

            if not self.pagination_navigator.go_to_next_results_page(page):
                self.logger.info("Could not move to the next page. Stopping pagination loop.")
                break

    def _should_stop_pagination(self, current_page_number: int, total_pages: int) -> bool:
        if current_page_number >= total_pages:
            self.logger.info("Reached the last result page for current source URL.")
            return True

        if self.settings.max_pages is None:
            return False

        if current_page_number >= self.settings.max_pages:
            self.logger.info(
                "Reached the configured max_pages limit (%s) for current source URL.",
                self.settings.max_pages,
            )
            return True

        return False
