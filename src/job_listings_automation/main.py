from __future__ import annotations

from .logger_setup import setup_logger
from .scraper import ListingsScraper
from .settings import (LOG_DIR, OUTPUT_DIR, PROFILE_DIR, AppSettings,
                       build_timestamp, ensure_directories, load_search_urls)


def run_scraper() -> None:
    run_timestamp = build_timestamp()
    ensure_directories()
    settings = AppSettings()
    logger = setup_logger(LOG_DIR, run_timestamp)
    search_urls = load_search_urls()

    scraper = ListingsScraper(
        settings=settings,
        logger=logger,
        profile_dir=PROFILE_DIR,
        output_dir=OUTPUT_DIR,
    )
    text_file = scraper.run(search_urls=search_urls, run_timestamp=run_timestamp)

    logger.info("Text file: %s", text_file)


if __name__ == "__main__":
    run_scraper()
