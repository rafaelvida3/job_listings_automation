from __future__ import annotations

from job_listings_automation.url_utils import normalize_listing_url


def test_normalize_listing_url_should_build_canonical_path() -> None:
    result = normalize_listing_url("https://careers.example.com/positions/123?tracking=abc")
    assert result == "https://careers.example.com/positions/123/"


def test_normalize_listing_url_should_join_relative_url() -> None:
    result = normalize_listing_url("/positions/987", base_origin="https://careers.example.com")
    assert result == "https://careers.example.com/positions/987/"


def test_normalize_listing_url_should_return_empty_string_for_none() -> None:
    result = normalize_listing_url(None)
    assert result == ""


def test_normalize_listing_url_should_return_empty_string_without_base_origin() -> None:
    result = normalize_listing_url("/positions/987")
    assert result == ""
