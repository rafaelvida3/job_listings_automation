from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import BrowserContext, Page, Playwright, TimeoutError

from .selectors import LISTING_CARD_SELECTOR
from .settings import AppSettings


class BrowserSession:
    def __init__(
        self,
        settings: AppSettings,
        logger: logging.Logger,
        profile_dir: Path,
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.profile_dir = profile_dir

    def create_context(self, playwright: Playwright) -> tuple[BrowserContext, Page]:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=str(self.profile_dir),
            headless=self.settings.headless,
            slow_mo=self.settings.slow_mo_ms,
            args=["--start-maximized"],
            viewport={"width": 1440, "height": 900},
        )
        context.set_default_timeout(self.settings.page_load_timeout_ms)
        page = context.pages[0] if context.pages else context.new_page()

        return context, page

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

    def close_context_safely(self, context: BrowserContext | None) -> None:
        if context is None:
            return

        try:
            context.close()
        except Exception as error:
            self.logger.warning("Failed to close browser context cleanly: %s", error)