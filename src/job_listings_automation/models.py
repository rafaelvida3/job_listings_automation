from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ListingData:
    listing_id: str
    title: str | None
    link: str | None
    description: str | None
    source_url: str
