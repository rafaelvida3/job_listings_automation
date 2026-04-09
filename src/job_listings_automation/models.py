from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(slots=True)
class ListingData:
    listing_id: str
    title: Optional[str]
    link: Optional[str]
    description: Optional[str]
    source_url: str
