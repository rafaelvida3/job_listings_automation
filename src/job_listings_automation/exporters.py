from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal, Optional

from .models import ListingData
from .settings import get_now

OutputFormat = Literal["txt", "json"]


def build_output_file_path(
        output_dir: Path,
        run_timestamp: str,
        output_format: OutputFormat
    ) -> Path:
    return output_dir / f"job_listings_{run_timestamp}.{output_format}"


def format_text_field(value: Optional[str]) -> str:
    return value if value else "N/A"


def export_listings_to_text(
    listings: list[ListingData],
    output_dir: Path,
    run_timestamp: str,
    logger: logging.Logger,
    source_urls: list[str],
) -> Path:
    output_file = build_output_file_path(output_dir, run_timestamp, "txt")

    with output_file.open("w", encoding="utf-8") as file:
        file.write(f"Generated at: {get_now().isoformat()}\n")
        file.write("Source URLs:\n")
        for source_url in source_urls:
            file.write(f"- {source_url}\n")
        file.write(f"Total listings: {len(listings)}\n\n")

        for index, listing in enumerate(listings, start=1):
            file.write("=" * 100 + "\n")
            file.write(f"LISTING #{index}\n")
            file.write(f"Listing ID: {format_text_field(listing.listing_id)}\n")
            file.write(f"Source URL: {listing.source_url}\n")
            file.write(f"Title: {format_text_field(listing.title)}\n")
            file.write(f"Link: {format_text_field(listing.link)}\n")
            file.write("Description:\n")
            file.write(format_text_field(listing.description))
            file.write("\n\n")

    logger.info("Text output saved to %s", output_file)
    return output_file


def export_listings_to_json(
    listings: list[ListingData],
    output_dir: Path,
    run_timestamp: str,
    logger: logging.Logger,
    source_urls: list[str],
) -> Path:
    output_file = build_output_file_path(output_dir, run_timestamp, "json")
    payload = {
        "generated_at": get_now().isoformat(),
        "source_urls": source_urls,
        "total_listings": len(listings),
        "listings": [
            {
                "listing_id": listing.listing_id,
                "source_url": listing.source_url,
                "title": listing.title,
                "link": listing.link,
                "description": listing.description,
            }
            for listing in listings
        ],
    }

    output_file.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    logger.info("JSON output saved to %s", output_file)
    return output_file


def export_listings(
    listings: list[ListingData],
    output_dir: Path,
    run_timestamp: str,
    logger: logging.Logger,
    source_urls: list[str],
    output_format: OutputFormat = "txt",
) -> Path:
    if output_format == "json":
        return export_listings_to_json(
            listings=listings,
            output_dir=output_dir,
            run_timestamp=run_timestamp,
            logger=logger,
            source_urls=source_urls,
        )

    return export_listings_to_text(
        listings=listings,
        output_dir=output_dir,
        run_timestamp=run_timestamp,
        logger=logger,
        source_urls=source_urls,
    )
