from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock

from playwright.sync_api import Locator, Page

from job_listings_automation.browser_session import BrowserSession
from job_listings_automation.listing_extractor import ListingExtractor
from job_listings_automation.pagination import PaginationNavigator
from job_listings_automation.settings import AppSettings


class FakeLocator:
    def __init__(
        self, items: list[Any] | None = None, text: str = "", visible: bool = True
    ) -> None:
        self.items = items or []
        self.text = text
        self.visible = visible

    @property
    def first(self) -> Any:
        return self.items[0] if self.items else self

    def count(self) -> int:
        return len(self.items) if self.items else (1 if self.text else 0)

    def nth(self, index: int) -> Any:
        return self.items[index]

    def inner_text(self, timeout: int = 0) -> str:
        return self.text

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        return None


class BrokenLocator(FakeLocator):
    def inner_text(self, timeout: int = 0) -> str:
        raise RuntimeError("locator is stale")


class FakeCard:
    def __init__(self, listing_id: str = "") -> None:
        self.attributes = {
            "data-occludable-job-id": listing_id,
            "data-job-id": "",
        }

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        return None


class BrokenScrollCard(FakeCard):
    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        raise RuntimeError("scroll failed")


class FakePage:
    def __init__(self, locator_map: dict[str, Any]) -> None:
        self.locator_map = locator_map
        self.mouse = MagicMock()
        self.waited_timeouts: list[int] = []

    def locator(self, selector: str) -> Any:
        return self.locator_map[selector]

    def wait_for_timeout(self, timeout: int) -> None:
        self.waited_timeouts.append(timeout)


class BrokenContext:
    def close(self) -> None:
        raise RuntimeError("close failed")


def test_listing_extractor_get_locator_text_should_return_empty_string_for_recoverable_errors() -> (
    None
):
    extractor = ListingExtractor(
        settings=AppSettings(),
        logger=logging.getLogger("test-listing-extractor"),
        pagination_navigator=PaginationNavigator(
            AppSettings(), logging.getLogger("test-pagination")
        ),
    )

    assert extractor.get_locator_text(cast(Locator, BrokenLocator(text="anything"))) == ""


def test_pagination_safe_scroll_last_card_should_return_false_after_retries() -> None:
    navigator = PaginationNavigator(
        AppSettings(stale_scroll_retries=2), logging.getLogger("test-pagination")
    )
    cards = FakeLocator(items=[BrokenScrollCard("job-1")])
    page = FakePage(locator_map={"li[data-occludable-job-id]": cards})

    moved = navigator.safe_scroll_last_card(cast(Page, page))

    assert moved is False
    assert page.waited_timeouts == [700, 700]


def test_browser_session_close_context_safely_should_ignore_recoverable_errors() -> None:
    session = BrowserSession(
        settings=AppSettings(),
        logger=logging.getLogger("test-browser-session"),
        profile_dir=Path("/tmp/profile"),
    )

    session.close_context_safely(BrokenContext())