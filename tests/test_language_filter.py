from __future__ import annotations

from unittest.mock import MagicMock

from lingua import Language

from job_listings_automation.language_filter import PortugueseListingFilter
from job_listings_automation.models import ListingData


def build_listing(title: str | None, description: str | None) -> ListingData:
    return ListingData(
        listing_id="job-1",
        title=title,
        link="https://example.com/jobs/1/",
        description=description,
        source_url="https://example.com/search",
    )


def test_should_accept_listing_detected_as_portuguese() -> None:
    detector = MagicMock()
    detector.detect_language_of.return_value = Language.PORTUGUESE
    language_filter = PortugueseListingFilter(detector=detector)

    listing = build_listing(
        "Desenvolvedor Python",
        "Desenvolva aplicações e participe das decisões técnicas.",
    )

    assert language_filter.is_portuguese(listing) is True
    detector.detect_language_of.assert_called_once_with(
        "Desenvolvedor Python\nDesenvolva aplicações e participe das decisões técnicas."
    )


def test_should_reject_listing_detected_as_another_language() -> None:
    detector = MagicMock()
    detector.detect_language_of.return_value = Language.ENGLISH
    language_filter = PortugueseListingFilter(detector=detector)

    assert (
        language_filter.is_portuguese(
            build_listing("Python Developer", "Build and maintain web applications.")
        )
        is False
    )


def test_should_reject_listing_without_text_without_using_detector() -> None:
    detector = MagicMock()
    language_filter = PortugueseListingFilter(detector=detector)

    assert language_filter.is_portuguese(build_listing(None, None)) is False
    detector.detect_language_of.assert_not_called()
