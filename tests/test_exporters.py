from __future__ import annotations

import json
import logging
from pathlib import Path

from job_listings_automation.exporters import export_listings
from job_listings_automation.models import ListingData


def test_export_listings_should_create_json_file(tmp_path: Path) -> None:
    logger = logging.getLogger("test-exporters")
    listings = [
        ListingData(
            listing_id="job-1",
            title="Python Developer",
            link="https://example.com/jobs/1/",
            description="Build APIs",
            source_url="https://example.com/search/python",
        )
    ]

    output_file = export_listings(
        listings=listings,
        output_dir=tmp_path,
        run_timestamp="2026-04-08_18-00-00",
        logger=logger,
        source_urls=["https://example.com/search/python"],
        output_format="json",
    )

    assert output_file.suffix == ".json"
    payload = json.loads(output_file.read_text(encoding="utf-8"))
    assert payload["total_listings"] == 1
    assert payload["listings"][0]["title"] == "Python Developer"


def test_export_listings_should_create_text_file(tmp_path: Path) -> None:
    logger = logging.getLogger("test-exporters")
    listings = [
        ListingData(
            listing_id="job-1",
            title="Python Developer",
            link="https://example.com/jobs/1/",
            description="Build APIs",
            source_url="https://example.com/search/python",
        )
    ]

    output_file = export_listings(
        listings=listings,
        output_dir=tmp_path,
        run_timestamp="2026-04-08_18-00-00",
        logger=logger,
        source_urls=["https://example.com/search/python"],
    )

    content = output_file.read_text(encoding="utf-8")
    assert output_file.suffix == ".txt"
    assert "Python Developer" in content


def test_export_listings_should_render_na_in_text_when_fields_are_missing(tmp_path: Path) -> None:
    logger = logging.getLogger("test-exporters")
    listings = [
        ListingData(
            listing_id="",
            title=None,
            link=None,
            description=None,
            source_url="https://example.com/search/python",
        )
    ]

    output_file = export_listings(
        listings=listings,
        output_dir=tmp_path,
        run_timestamp="2026-04-08_18-00-00",
        logger=logger,
        source_urls=["https://example.com/search/python"],
    )

    content = output_file.read_text(encoding="utf-8")
    assert "Title: N/A" in content
    assert "Link: N/A" in content
    assert "Description:\nN/A" in content


def test_export_listings_should_keep_null_in_json_when_fields_are_missing(tmp_path: Path) -> None:
    logger = logging.getLogger("test-exporters")
    listings = [
        ListingData(
            listing_id="",
            title=None,
            link=None,
            description=None,
            source_url="https://example.com/search/python",
        )
    ]

    output_file = export_listings(
        listings=listings,
        output_dir=tmp_path,
        run_timestamp="2026-04-08_18-00-00",
        logger=logger,
        source_urls=["https://example.com/search/python"],
        output_format="json",
    )

    payload = json.loads(output_file.read_text(encoding="utf-8"))
    listing = payload["listings"][0]
    assert listing["title"] is None
    assert listing["link"] is None
    assert listing["description"] is None
