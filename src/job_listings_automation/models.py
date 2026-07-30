from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class ListingData:
    listing_id: str
    title: str | None
    link: str | None
    description: str | None
    source_url: str
    published_relative_text: str | None = None
    published_at: datetime | None = None
    collected_at: datetime | None = None
