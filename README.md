# Job Listings Automation

A Python browser automation project that collects listing data from configured result pages,
normalizes the extracted content, and exports deterministic outputs for later review.

This repository is intentionally structured as a maintainable automation workflow instead of a
single long script. The goal is to show practical engineering decisions: clear responsibility
boundaries, typed settings, predictable exports, and resilience around unstable browser behavior.

## What this project demonstrates

- Modular design instead of a monolithic scraper
- Typed runtime settings and explicit validation
- Selector abstraction for easier maintenance when the target layout changes
- Safe pagination handling with stop conditions and empty-state detection
- Deterministic text and JSON exporters
- Logging and optional fatal-error screenshots
- Unit tests focused on failure boundaries and scraping flow
- CI checks for lint, type checking, and tests

## Architecture

The codebase is split into focused modules:

- `main.py`: CLI entrypoint and runtime wiring
- `settings.py`: typed configuration, paths, timestamps, and config loading
- `browser_session.py`: browser/context lifecycle and access bootstrapping
- `pagination.py`: page state parsing, empty-state detection, scrolling, and navigation
- `listing_extractor.py`: card interaction, fallback extraction, normalization, and deduplication
- `selectors.py`: selector profile abstraction for the target page structure
- `exporters.py`: text and JSON output generation
- `logger_setup.py`: run-specific logger configuration
- `models.py`: typed listing model
- `text_utils.py` and `url_utils.py`: normalization helpers

## Why the selector abstraction matters

Automation code usually fails at the boundary with the external UI. In this project, selector
strings are grouped into a `SelectorProfile` instead of being spread across the codebase. That is
small on purpose, but it reduces coupling and makes layout maintenance more explicit.

## Data flow

1. Load search URLs from JSON configuration
2. Start a persistent browser session
3. Open each configured result page
4. Confirm that the listing area is accessible
5. Scroll until visible cards are loaded
6. Open each listing and extract normalized fields
7. Skip duplicates using listing ID or canonical URL
8. Paginate until the last page or the configured page limit
9. Export the collected listings as `.txt` or `.json`

## Defensive behaviors

The scraper includes a few deliberate safeguards:

- fallback title and link extraction when the detail panel is incomplete
- duplicate prevention across pages
- per-card failure isolation, so one broken card does not abort the entire page
- empty-result detection to avoid collecting unrelated recommendations
- optional screenshot capture on fatal errors
- explicit stop condition for `max_pages`

## Example output

### JSON

```json
{
  "generated_at": "2026-04-08T19:40:00-03:00",
  "source_urls": [
    "https://example.com/search?page=1"
  ],
  "total_listings": 1,
  "listings": [
    {
      "listing_id": "job-123",
      "source_url": "https://example.com/search?page=1",
      "title": "Senior Python Developer",
      "link": "https://example.com/jobs/123/",
      "description": "Build APIs and maintain automation workflows."
    }
  ]
}
```

### Log sample

```text
2026-04-08 19:40:00 | INFO | Scraper started.
2026-04-08 19:40:02 | INFO | Opening source URL 1/1
2026-04-08 19:40:04 | INFO | Processing source URL 1/1 | result page 1 of 3.
2026-04-08 19:40:08 | INFO | Collected 1 listings in total | current page 1 | Senior Python Developer
2026-04-08 19:40:10 | INFO | Reached the configured max_pages limit (1) for current source URL.
2026-04-08 19:40:10 | INFO | Scraper finished successfully.
```

## CLI usage

Run with the default configuration:

```bash
python -m job_listings_automation
```

Run headless and export JSON:

```bash
python -m job_listings_automation --headless --output-format json
```

Limit the number of processed pages per source URL:

```bash
python -m job_listings_automation --max-pages 2
```

Use a custom input config:

```bash
python -m job_listings_automation --input config/searches.json
```

Disable screenshot capture on fatal errors:

```bash
python -m job_listings_automation --no-take-screenshot-on-error
```

## Input format

Expected JSON structure:

```json
{
  "search_urls": [
    "https://example.com/search?page=1"
  ]
}
```

## Setup

Install the project and development dependencies:

```bash
pip install -e ".[dev]"
playwright install
```

Create the runtime config:

```bash
cp config/searches.example.json config/searches.json
```

Then run:

```bash
python -m job_listings_automation
```

## Testing

Run the full quality suite with:

```bash
ruff check .
mypy
pytest -q
```

## Trade-offs and limitations

This project intentionally favors clarity over framework-heavy abstractions.

Current limitations:

- selectors are still tied to one target layout, even though they are now centralized
- dynamic anti-bot protections can still affect automation reliability
- outputs are file-based by design; there is no persistence layer yet
- tests are unit-focused and use fakes instead of full browser sessions

These are reasonable trade-offs for a portfolio project focused on maintainability,
practicality, and clean automation code.
