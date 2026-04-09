from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from job_listings_automation.models import ListingData
from job_listings_automation.scraper import ListingsScraper
from job_listings_automation.settings import AppSettings


class FakeLocator:
    def __init__(self, items: list[Any] | None = None, text: str = "", visible: bool = True) -> None:
        self.items = items or []
        self.text = text
        self.visible = visible
        self.clicked = False
        self.scrolled = False
        self.evaluated_scripts: list[tuple[str, Any]] = []
        self.href: str | None = None

    @property
    def first(self) -> Any:
        return self.items[0] if self.items else self

    def count(self) -> int:
        return len(self.items) if self.items else (1 if (self.text or self.href is not None) else 0)

    def nth(self, index: int) -> Any:
        return self.items[index]

    def inner_text(self, timeout: int = 0) -> str:
        return self.text

    def is_visible(self) -> bool:
        return self.visible

    def click(self, timeout: int = 0) -> None:
        self.clicked = True

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        self.scrolled = True

    def evaluate(self, script: str, value: Any = None) -> None:
        self.evaluated_scripts.append((script, value))

    def get_attribute(self, name: str) -> str | None:
        if name == "href":
            return self.href
        return None


class FakeLinkLocator(FakeLocator):
    def __init__(self, text: str = "", href: str | None = None) -> None:
        super().__init__(text=text)
        self.href = href


class FakeCard:
    def __init__(
        self,
        listing_id: str = "",
        fallback_title: str = "",
        fallback_href: str | None = None,
    ) -> None:
        self.attributes = {
            "data-occludable-job-id": listing_id,
            "data-job-id": "",
        }
        self.link_locator = FakeLinkLocator(text=fallback_title, href=fallback_href)
        self.clicked = False
        self.scrolled = False
        self.evaluated_scripts: list[tuple[str, Any]] = []

    def get_attribute(self, name: str) -> str | None:
        return self.attributes.get(name)

    def locator(self, selector: str) -> FakeLocator:
        return self.link_locator

    def click(self, timeout: int = 0) -> None:
        self.clicked = True

    def scroll_into_view_if_needed(self, timeout: int = 0) -> None:
        self.scrolled = True

    def evaluate(self, script: str, value: Any = None) -> None:
        self.evaluated_scripts.append((script, value))


class FakePage:
    def __init__(self, *, locator_map: dict[str, Any] | None = None, text_map: dict[str, FakeLocator] | None = None) -> None:
        self.locator_map = locator_map or {}
        self.text_map = text_map or {}
        self.mouse = MagicMock()
        self.waited_timeouts: list[int] = []
        self.waited_selectors: list[tuple[str, int | None]] = []
        self.waited_functions: list[dict[str, Any]] = []
        self.goto_calls: list[tuple[str, str | None]] = []
        self.screenshot_calls: list[dict[str, Any]] = []

    def locator(self, selector: str) -> Any:
        return self.locator_map[selector]

    def get_by_text(self, text: str, exact: bool = False) -> FakeLocator:
        return self.text_map.get(text, FakeLocator())

    def wait_for_timeout(self, timeout: int) -> None:
        self.waited_timeouts.append(timeout)

    def wait_for_selector(self, selector: str, timeout: int | None = None) -> None:
        self.waited_selectors.append((selector, timeout))

    def wait_for_function(self, script: str, arg: dict[str, Any], timeout: int) -> None:
        self.waited_functions.append({"script": script, "arg": arg, "timeout": timeout})

    def goto(self, url: str, wait_until: str | None = None) -> None:
        self.goto_calls.append((url, wait_until))

    def screenshot(self, path: str, full_page: bool) -> None:
        self.screenshot_calls.append({"path": path, "full_page": full_page})


@pytest.fixture
def scraper() -> ListingsScraper:
    return ListingsScraper(
        settings=AppSettings(
            min_reading_delay_ms=0,
            max_reading_delay_ms=0,
            max_scroll_rounds=1,
        ),
        logger=logging.getLogger("test-scraper"),
        profile_dir=Path("/tmp/profile"),
        output_dir=Path("/tmp/output"),
    )


def test_run_should_stop_when_empty_state_is_detected(monkeypatch: pytest.MonkeyPatch, scraper: ListingsScraper) -> None:
    page = MagicMock()
    context = MagicMock()
    context.pages = [page]

    chromium = MagicMock()
    chromium.launch_persistent_context.return_value = context
    playwright = MagicMock()
    playwright.chromium = chromium

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return playwright

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    collect_mock = MagicMock()
    export_mock = MagicMock(return_value=Path("/tmp/output/result.txt"))

    monkeypatch.setattr("job_listings_automation.scraper.sync_playwright", lambda: FakePlaywrightContext())
    monkeypatch.setattr("job_listings_automation.scraper.export_listings", export_mock)

    scraper.browser_session.create_context = MagicMock(return_value=(context, page))
    scraper.browser_session.wait_for_access_and_listing_list = MagicMock()
    scraper.browser_session.wait_for_listing_list = MagicMock()
    scraper.browser_session.close_context_safely = MagicMock()
    scraper.pagination_navigator.get_total_pages = MagicMock(return_value=1)
    scraper.pagination_navigator.get_current_page_number = MagicMock(return_value=1)
    scraper.pagination_navigator.has_empty_search_results = MagicMock(return_value=True)
    scraper.listing_extractor.collect_listings_from_current_page = collect_mock

    result = scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    assert result == Path("/tmp/output/result.txt")
    scraper.browser_session.wait_for_access_and_listing_list.assert_called_once_with(page)
    collect_mock.assert_not_called()
    export_mock.assert_called_once()
    scraper.browser_session.close_context_safely.assert_called_once_with(context)


def test_go_to_next_results_page_should_return_true_when_page_changes(
    monkeypatch: pytest.MonkeyPatch,
    scraper: ListingsScraper,
) -> None:
    next_button = FakeLocator(items=[FakeLocator()])
    pagination_state = FakeLocator(text="Page 1 of 3")
    page = FakePage(
        locator_map={
            ".jobs-search-pagination__page-state": pagination_state,
            "button.jobs-search-pagination__button--next, button[aria-label='Ver próxima página'], button[aria-label='View next page']": next_button,
            "li[data-occludable-job-id]": FakeLocator(items=[FakeCard("1")]),
        }
    )

    page_numbers = iter([1, 2])
    monkeypatch.setattr(scraper.pagination_navigator, "get_current_page_number", lambda current_page: next(page_numbers))

    moved = scraper.pagination_navigator.go_to_next_results_page(page)

    assert moved is True
    assert next_button.first.clicked is True
    assert page.waited_functions[0]["arg"]["previousPageNumber"] == 1


def test_extract_listing_data_should_use_fallback_title_and_link_when_detail_data_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    scraper: ListingsScraper,
) -> None:
    fallback_card = FakeCard(
        listing_id="job-123",
        fallback_title="Senior Python Developer",
        fallback_href="/jobs/view/123",
    )
    detail_title = FakeLocator(text="")
    detail_description = FakeLocator(text="Build APIs\n\nMaintain automations")
    page = FakePage(
        locator_map={
            "div.job-details-jobs-unified-top-card__job-title h1 a, div.job-details-jobs-unified-top-card__job-title h1": detail_title,
            "#job-details": detail_description,
        }
    )

    monkeypatch.setattr(scraper.listing_extractor, "click_listing_card", lambda card, listing_id: None)
    monkeypatch.setattr(scraper.listing_extractor, "simulate_description_scroll", lambda current_page: None)

    listing = scraper.listing_extractor.extract_listing_data(
        page=page,
        card=fallback_card,
        source_url="https://example.com/search?keywords=python",
        base_origin="https://example.com",
    )

    assert listing is not None
    assert listing.title == "Senior Python Developer"
    assert listing.link == "https://example.com/jobs/view/123/"
    assert listing.description == "Build APIs\nMaintain automations"


def test_collect_listings_from_current_page_should_deduplicate_by_listing_id(
    monkeypatch: pytest.MonkeyPatch,
    scraper: ListingsScraper,
) -> None:
    cards = FakeLocator(items=[FakeCard("job-1"), FakeCard("job-1"), FakeCard("job-2")])
    page = FakePage(locator_map={"li[data-occludable-job-id]": cards})
    listings: list[ListingData] = []
    seen_keys: set[str] = set()

    extracted_items = iter(
        [
            ListingData("job-1", "Role A", "https://example.com/jobs/1/", "desc", "source"),
            ListingData("job-1", "Role A duplicate", "https://example.com/jobs/1/", "desc", "source"),
            ListingData("job-2", "Role B", "https://example.com/jobs/2/", "desc", "source"),
        ]
    )

    monkeypatch.setattr(scraper.pagination_navigator, "load_all_listing_cards", lambda current_page: 3)
    monkeypatch.setattr(scraper.pagination_navigator, "get_current_page_number", lambda current_page: 1)
    monkeypatch.setattr(scraper.listing_extractor, "extract_listing_data", lambda *args, **kwargs: next(extracted_items))

    scraper.listing_extractor.collect_listings_from_current_page(
        page=page,
        listings=listings,
        seen_keys=seen_keys,
        source_url="https://example.com/search",
    )

    assert [item.listing_id for item in listings] == ["job-1", "job-2"]
    assert seen_keys == {"job-1", "job-2"}


def test_collect_listings_from_current_page_should_continue_when_one_card_fails(
    monkeypatch: pytest.MonkeyPatch,
    scraper: ListingsScraper,
) -> None:
    cards = FakeLocator(items=[FakeCard("job-1"), FakeCard("job-2")])
    page = FakePage(locator_map={"li[data-occludable-job-id]": cards})
    listings: list[ListingData] = []
    seen_keys: set[str] = set()

    calls = {"count": 0}

    def fake_extract_listing_data(*args: Any, **kwargs: Any) -> ListingData:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Broken card")

        return ListingData("job-2", "Role B", "https://example.com/jobs/2/", "desc", "source")

    monkeypatch.setattr(scraper.pagination_navigator, "load_all_listing_cards", lambda current_page: 2)
    monkeypatch.setattr(scraper.pagination_navigator, "get_current_page_number", lambda current_page: 1)
    monkeypatch.setattr(scraper.listing_extractor, "extract_listing_data", fake_extract_listing_data)

    scraper.listing_extractor.collect_listings_from_current_page(
        page=page,
        listings=listings,
        seen_keys=seen_keys,
        source_url="https://example.com/search",
    )

    assert len(listings) == 1
    assert listings[0].listing_id == "job-2"
    assert seen_keys == {"job-2"}
    assert 1000 in page.waited_timeouts


def test_run_should_close_context_on_success_and_not_take_error_screenshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_scraper = ListingsScraper(
        settings=AppSettings(take_screenshot_on_error=True),
        logger=logging.getLogger("test-scraper-success"),
        profile_dir=Path("/tmp/profile"),
        output_dir=Path("/tmp/output"),
    )
    page = FakePage()
    context = MagicMock()

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return MagicMock()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    monkeypatch.setattr("job_listings_automation.scraper.sync_playwright", lambda: FakePlaywrightContext())
    monkeypatch.setattr(
        test_scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(test_scraper.browser_session, "wait_for_access_and_listing_list", MagicMock())
    monkeypatch.setattr(test_scraper.browser_session, "close_context_safely", MagicMock())
    monkeypatch.setattr(test_scraper.pagination_navigator, "get_total_pages", MagicMock(return_value=1))
    monkeypatch.setattr(test_scraper.pagination_navigator, "get_current_page_number", MagicMock(return_value=1))
    monkeypatch.setattr(test_scraper.pagination_navigator, "has_empty_search_results", MagicMock(return_value=True))
    monkeypatch.setattr(
        "job_listings_automation.scraper.export_listings",
        MagicMock(return_value=Path("/tmp/output/result.txt")),
    )

    result = test_scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    assert result == Path("/tmp/output/result.txt")
    test_scraper.browser_session.close_context_safely.assert_called_once_with(context)
    assert page.screenshot_calls == []


def test_run_should_take_screenshot_on_error_and_still_close_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_scraper = ListingsScraper(
        settings=AppSettings(take_screenshot_on_error=True),
        logger=logging.getLogger("test-scraper-error"),
        profile_dir=Path("/tmp/profile"),
        output_dir=Path("/tmp/output"),
    )
    page = FakePage()
    context = MagicMock()

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return MagicMock()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    monkeypatch.setattr("job_listings_automation.scraper.sync_playwright", lambda: FakePlaywrightContext())
    monkeypatch.setattr(
        test_scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(test_scraper.browser_session, "wait_for_access_and_listing_list", MagicMock(side_effect=RuntimeError("boom")))
    monkeypatch.setattr(test_scraper.browser_session, "close_context_safely", MagicMock())

    with pytest.raises(RuntimeError, match="boom"):
        test_scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    assert len(page.screenshot_calls) == 1
    test_scraper.browser_session.close_context_safely.assert_called_once_with(context)
