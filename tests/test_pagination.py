from __future__ import annotations

import logging

from job_listings_automation.pagination import PaginationNavigator
from job_listings_automation.selectors import DEFAULT_SELECTOR_PROFILE
from job_listings_automation.settings import AppSettings

from .fakes import BrokenScrollCard, FakeLocator, FakePage


def build_navigator() -> PaginationNavigator:
    return PaginationNavigator(
        AppSettings(stale_scroll_retries=2),
        logging.getLogger("test-pagination"),
    )


def test_safe_scroll_last_card_should_return_false_after_retries() -> None:
    navigator = build_navigator()
    cards = FakeLocator(items=[BrokenScrollCard("job-1")])
    page = FakePage(locator_map={DEFAULT_SELECTOR_PROFILE.listing_card: cards})

    moved = navigator.safe_scroll_last_card(page)

    assert moved is False
    assert page.waited_timeouts == [700, 700]


def test_go_to_next_results_page_should_return_true_when_page_changes(monkeypatch) -> None:
    navigator = build_navigator()
    next_button = FakeLocator(items=[FakeLocator()])
    pagination_state = FakeLocator(text="Page 1 of 3")
    page = FakePage(
        locator_map={
            DEFAULT_SELECTOR_PROFILE.pagination_state: pagination_state,
            DEFAULT_SELECTOR_PROFILE.next_page_button: next_button,
            DEFAULT_SELECTOR_PROFILE.listing_card: FakeLocator(items=[FakeLocator(text="card")]),
        }
    )

    page_numbers = iter([1, 2])
    monkeypatch.setattr(
        navigator,
        "get_current_page_number",
        lambda current_page: next(page_numbers),
    )

    moved = navigator.go_to_next_results_page(page)

    assert moved is True
    assert next_button.first.clicked is True
    assert page.waited_functions[0]["arg"]["previousPageNumber"] == 1
