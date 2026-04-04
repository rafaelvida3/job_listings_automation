from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ListingData:
    listing_id: str
    title: str
    link: str
    description: str
    source_url: str
