from __future__ import annotations

import logging

import pytest

from job_listings_automation.listing_extractor import ListingExtractor
from job_listings_automation.models import ListingData
from job_listings_automation.pagination import PaginationNavigator
from job_listings_automation.selectors import DEFAULT_SELECTOR_PROFILE
from job_listings_automation.settings import AppSettings

from .fakes import BrokenLocator, FakeCard, FakeLocator, FakePage


@pytest.fixture
def listing_extractor() -> ListingExtractor:
    settings = AppSettings(
        min_reading_delay_ms=0,
        max_reading_delay_ms=0,
        max_scroll_rounds=1,
    )
    logger = logging.getLogger("test-listing-extractor")
    navigator = PaginationNavigator(settings, logger)
    return ListingExtractor(settings=settings, logger=logger, pagination_navigator=navigator)


def test_get_locator_text_should_return_empty_string_for_recoverable_errors(
    listing_extractor: ListingExtractor,
) -> None:
    assert listing_extractor.get_locator_text(BrokenLocator(text="anything")) == ""


def test_extract_listing_data_should_use_fallback_title_and_link_when_detail_data_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    listing_extractor: ListingExtractor,
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
            DEFAULT_SELECTOR_PROFILE.detail_title: detail_title,
            DEFAULT_SELECTOR_PROFILE.detail_description: detail_description,
        }
    )

    monkeypatch.setattr(listing_extractor, "click_listing_card", lambda card, listing_id: None)
    monkeypatch.setattr(listing_extractor, "simulate_description_scroll", lambda current_page: None)

    listing = listing_extractor.extract_listing_data(
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
    listing_extractor: ListingExtractor,
) -> None:
    cards = FakeLocator(items=[FakeCard("job-1"), FakeCard("job-1"), FakeCard("job-2")])
    page = FakePage(locator_map={DEFAULT_SELECTOR_PROFILE.listing_card: cards})
    listings: list[ListingData] = []
    seen_keys: set[str] = set()

    extracted_items = iter(
        [
            ListingData("job-1", "Role A", "https://example.com/jobs/1/", "desc", "source"),
            ListingData(
                "job-1",
                "Role A duplicate",
                "https://example.com/jobs/1/",
                "desc",
                "source",
            ),
            ListingData("job-2", "Role B", "https://example.com/jobs/2/", "desc", "source"),
        ]
    )

    monkeypatch.setattr(
        listing_extractor.pagination_navigator,
        "load_all_listing_cards",
        lambda current_page: 3,
    )
    monkeypatch.setattr(
        listing_extractor.pagination_navigator,
        "get_current_page_number",
        lambda current_page: 1,
    )
    monkeypatch.setattr(
        listing_extractor,
        "extract_listing_data",
        lambda *args, **kwargs: next(extracted_items),
    )

    listing_extractor.collect_listings_from_current_page(
        page=page,
        listings=listings,
        seen_keys=seen_keys,
        source_url="https://example.com/search",
    )

    assert [item.listing_id for item in listings] == ["job-1", "job-2"]
    assert seen_keys == {"job-1", "job-2"}


def test_collect_listings_from_current_page_should_continue_when_one_card_fails(
    monkeypatch: pytest.MonkeyPatch,
    listing_extractor: ListingExtractor,
) -> None:
    cards = FakeLocator(items=[FakeCard("job-1"), FakeCard("job-2")])
    page = FakePage(locator_map={DEFAULT_SELECTOR_PROFILE.listing_card: cards})
    listings: list[ListingData] = []
    seen_keys: set[str] = set()
    calls = {"count": 0}

    def fake_extract_listing_data(*args, **kwargs) -> ListingData:
        calls["count"] += 1
        if calls["count"] == 1:
            raise RuntimeError("Broken card")
        return ListingData("job-2", "Role B", "https://example.com/jobs/2/", "desc", "source")

    monkeypatch.setattr(
        listing_extractor.pagination_navigator,
        "load_all_listing_cards",
        lambda current_page: 2,
    )
    monkeypatch.setattr(
        listing_extractor.pagination_navigator,
        "get_current_page_number",
        lambda current_page: 1,
    )
    monkeypatch.setattr(listing_extractor, "extract_listing_data", fake_extract_listing_data)

    listing_extractor.collect_listings_from_current_page(
        page=page,
        listings=listings,
        seen_keys=seen_keys,
        source_url="https://example.com/search",
    )

    assert len(listings) == 1
    assert listings[0].listing_id == "job-2"
    assert seen_keys == {"job-2"}
    assert 1_000 in page.waited_timeouts
