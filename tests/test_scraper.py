from __future__ import annotations

import logging
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from job_listings_automation.scraper import ListingsScraper
from job_listings_automation.settings import AppSettings

from .fakes import FakePage


@pytest.fixture
def scraper() -> ListingsScraper:
    return ListingsScraper(
        settings=AppSettings(take_screenshot_on_error=True),
        logger=logging.getLogger("test-scraper"),
        profile_dir=Path("/tmp/profile"),
        output_dir=Path("/tmp/output"),
    )


def test_run_should_stop_when_empty_state_is_detected(
    monkeypatch: pytest.MonkeyPatch,
    scraper: ListingsScraper,
) -> None:
    page = MagicMock()
    context = MagicMock()

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return MagicMock()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    collect_mock = MagicMock()
    export_mock = MagicMock(return_value=Path("/tmp/output/result.txt"))

    monkeypatch.setattr(
        "job_listings_automation.scraper.sync_playwright",
        lambda: FakePlaywrightContext(),
    )
    monkeypatch.setattr("job_listings_automation.scraper.export_listings", export_mock)
    monkeypatch.setattr(
        scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(scraper.browser_session, "wait_for_access_and_listing_list", MagicMock())
    monkeypatch.setattr(scraper.browser_session, "wait_for_listing_list", MagicMock())
    monkeypatch.setattr(scraper.browser_session, "close_context_safely", MagicMock())
    monkeypatch.setattr(scraper.pagination_navigator, "get_total_pages", MagicMock(return_value=1))
    monkeypatch.setattr(
        scraper.pagination_navigator,
        "get_current_page_number",
        MagicMock(return_value=1),
    )
    monkeypatch.setattr(
        scraper.pagination_navigator,
        "has_empty_search_results",
        MagicMock(return_value=True),
    )
    monkeypatch.setattr(
        scraper.listing_extractor,
        "collect_listings_from_current_page",
        collect_mock,
    )

    result = scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    assert result == Path("/tmp/output/result.txt")
    scraper.browser_session.wait_for_access_and_listing_list.assert_called_once_with(page)
    collect_mock.assert_not_called()
    export_mock.assert_called_once()
    scraper.browser_session.close_context_safely.assert_called_once_with(context)


def test_run_should_stop_pagination_when_max_pages_is_reached(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    test_scraper = ListingsScraper(
        settings=AppSettings(max_pages=1),
        logger=logging.getLogger("test-scraper-max-pages"),
        profile_dir=Path("/tmp/profile"),
        output_dir=Path("/tmp/output"),
    )
    page = MagicMock()
    context = MagicMock()

    class FakePlaywrightContext:
        def __enter__(self) -> Any:
            return MagicMock()

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
            return False

    export_mock = MagicMock(return_value=Path("/tmp/output/result.txt"))

    monkeypatch.setattr(
        "job_listings_automation.scraper.sync_playwright",
        lambda: FakePlaywrightContext(),
    )
    monkeypatch.setattr("job_listings_automation.scraper.export_listings", export_mock)
    monkeypatch.setattr(
        test_scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(
        test_scraper.browser_session,
        "wait_for_access_and_listing_list",
        MagicMock(),
    )
    monkeypatch.setattr(test_scraper.browser_session, "close_context_safely", MagicMock())
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "get_total_pages",
        MagicMock(return_value=3),
    )
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "get_current_page_number",
        MagicMock(return_value=1),
    )
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "has_empty_search_results",
        MagicMock(return_value=False),
    )
    monkeypatch.setattr(
        test_scraper.listing_extractor,
        "collect_listings_from_current_page",
        MagicMock(),
    )
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "go_to_next_results_page",
        MagicMock(return_value=True),
    )

    test_scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    test_scraper.pagination_navigator.go_to_next_results_page.assert_not_called()
    export_mock.assert_called_once()


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

    monkeypatch.setattr(
        "job_listings_automation.scraper.sync_playwright",
        lambda: FakePlaywrightContext(),
    )
    monkeypatch.setattr(
        test_scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(
        test_scraper.browser_session,
        "wait_for_access_and_listing_list",
        MagicMock(),
    )
    monkeypatch.setattr(test_scraper.browser_session, "close_context_safely", MagicMock())
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "get_total_pages",
        MagicMock(return_value=1),
    )
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "get_current_page_number",
        MagicMock(return_value=1),
    )
    monkeypatch.setattr(
        test_scraper.pagination_navigator,
        "has_empty_search_results",
        MagicMock(return_value=True),
    )
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

    monkeypatch.setattr(
        "job_listings_automation.scraper.sync_playwright",
        lambda: FakePlaywrightContext(),
    )
    monkeypatch.setattr(
        test_scraper.browser_session,
        "create_context",
        MagicMock(return_value=(context, page)),
    )
    monkeypatch.setattr(
        test_scraper.browser_session,
        "wait_for_access_and_listing_list",
        MagicMock(side_effect=RuntimeError("boom")),
    )
    monkeypatch.setattr(test_scraper.browser_session, "close_context_safely", MagicMock())

    with pytest.raises(RuntimeError, match="boom"):
        test_scraper.run(["https://example.com/search"], "2026-04-08_18-00-00")

    assert len(page.screenshot_calls) == 1
    test_scraper.browser_session.close_context_safely.assert_called_once_with(context)
