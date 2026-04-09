from __future__ import annotations

import argparse
from pathlib import Path

from .logger_setup import setup_logger
from .scraper import ListingsScraper
from .settings import (
    CONFIG_FILE,
    LOG_DIR,
    OUTPUT_DIR,
    PROFILE_DIR,
    AppSettings,
    build_timestamp,
    ensure_directories,
    load_search_urls,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect and export job listings from configured result pages.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=CONFIG_FILE,
        help="Path to the JSON file containing search_urls.",
    )
    parser.add_argument(
        "--output-format",
        choices=["txt", "json"],
        default="txt",
        help="Output file format.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run the browser in headless mode.",
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=None,
        help="Limit the number of result pages processed per source URL.",
    )
    parser.add_argument(
        "--take-screenshot-on-error",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable screenshot capture when a fatal error happens.",
    )
    return parser.parse_args()


def build_settings(args: argparse.Namespace) -> AppSettings:
    return AppSettings(
        headless=args.headless,
        max_pages=args.max_pages,
        take_screenshot_on_error=args.take_screenshot_on_error,
    )


def run_scraper() -> None:
    args = parse_args()
    run_timestamp = build_timestamp()
    ensure_directories()

    settings = build_settings(args)
    logger = setup_logger(LOG_DIR, run_timestamp)
    search_urls = load_search_urls(config_file=args.input)

    scraper = ListingsScraper(
        settings=settings,
        logger=logger,
        profile_dir=PROFILE_DIR,
        output_dir=OUTPUT_DIR,
    )
    output_file = scraper.run(
        search_urls=search_urls,
        run_timestamp=run_timestamp,
        output_format=args.output_format,
    )
    logger.info("Output file: %s", output_file)


if __name__ == "__main__":
    run_scraper()
