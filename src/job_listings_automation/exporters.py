from __future__ import annotations

import logging
from pathlib import Path

from .models import ListingData
from .settings import get_now


def export_listings_to_text(
    listings: list[ListingData],
    output_dir: Path,
    run_timestamp: str,
    logger: logging.Logger,
    source_urls: list[str],
) -> Path:
    output_file = output_dir / f"job_listings_{run_timestamp}.txt"

    with output_file.open("w", encoding="utf-8") as file:
        file.write(f"Generated at: {get_now().isoformat()}\n")
        file.write("Source URLs:\n")
        for source_url in source_urls:
            file.write(f"- {source_url}\n")
        file.write(f"Total listings: {len(listings)}\n\n")

        for index, listing in enumerate(listings, start=1):
            file.write("=" * 100 + "\n")
            file.write(f"LISTING #{index}\n")
            file.write(f"Listing ID: {listing.listing_id or 'N/A'}\n")
            file.write(f"Source URL: {listing.source_url}\n")
            file.write(f"Title: {listing.title}\n")
            file.write(f"Link: {listing.link}\n")
            file.write("Description:\n")
            file.write(listing.description)
            file.write("\n\n")

    logger.info("Text output saved to %s", output_file)
    return output_file
