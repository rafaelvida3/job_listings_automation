from __future__ import annotations

from typing import Protocol

from lingua import Language, LanguageDetector, LanguageDetectorBuilder

from .models import ListingData


class ListingLanguageFilter(Protocol):
    def is_portuguese(self, listing: ListingData) -> bool: ...


class PortugueseListingFilter:
    def __init__(self, detector: LanguageDetector | None = None) -> None:
        self._detector = detector

    @property
    def detector(self) -> LanguageDetector:
        if self._detector is None:
            self._detector = LanguageDetectorBuilder.from_all_languages().build()
        return self._detector

    def is_portuguese(self, listing: ListingData) -> bool:
        text = "\n".join(value for value in (listing.title, listing.description) if value).strip()
        if not text:
            return False

        return self.detector.detect_language_of(text) == Language.PORTUGUESE
