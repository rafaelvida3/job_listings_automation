# Job Listings Automation

A Python automation tool that collects job listing data from configured search result pages, normalizes the extracted content, and exports structured outputs for later review.

This project is designed as a maintainable scraping/automation workflow rather than a one-off script. It emphasizes separation of concerns, predictable outputs, test coverage for core behaviors, and defensive handling for unstable browser flows.

## Highlights

- Persistent browser session for authenticated browsing when needed
- Config-driven input URLs
- Incremental extraction from paginated result pages
- Deduplication by stable listing identifiers
- Text and JSON export formats
- Error logging and optional screenshot capture
- Unit tests for core parsing and scraping behavior
- CLI flags for headless mode, page limits, input source, and output format

## Architecture

The codebase is split into focused modules:

- `main.py`: CLI entrypoint and runtime wiring
- `settings.py`: typed configuration, paths, timestamps, and config loading
- `browser_session.py`: browser/context lifecycle and access bootstrapping
- `pagination.py`: pagination state, empty-state detection, scrolling, and page transitions
- `listing_extractor.py`: card interaction, detail extraction, fallback handling, and deduplication flow
- `exporters.py`: output generation for text and JSON formats
- `logger_setup.py`: run-specific logging
- `models.py`: typed data model for listings
- `text_utils.py` and `url_utils.py`: normalization helpers

## Why this project is useful in a portfolio

This repository demonstrates more than basic browser automation:

- modular design instead of a single large script
- clear responsibility boundaries
- resilience against partial failures and DOM changes
- reusable configuration and output pipeline
- tests that validate critical scraping behaviors

In practice, this means the project is easier to extend, debug, and operate than a quick prototype.

## Data flow

1. Load configured search URLs from a JSON file
2. Start a persistent browser session
3. Open each search result page
4. Detect access readiness and result availability
5. Scroll and load visible listing cards
6. Open each listing and extract normalized data
7. Skip duplicates using listing ID or canonical URL
8. Continue through pagination until completion or configured limit
9. Export the collected dataset as `.txt` or `.json`

## Defensive behaviors

The scraper includes a few deliberate safeguards:

- fallback title/link extraction when detail content is incomplete
- duplicate prevention across pages
- tolerance for one-off card failures without aborting the whole run
- empty-result detection to avoid collecting unrelated recommendations
- optional screenshot capture on fatal errors

These choices make the workflow more reliable in real-world browser automation scenarios.

## CLI usage

Default run:

```bash
python run.py
```

Headless run with JSON output:

```bash
python run.py --headless --output-format json
```

Limit the number of processed pages:

```bash
python run.py --max-pages 2
```

Use a custom input config:

```bash
python run.py --input config/searches.json
```

Disable screenshot capture on fatal errors:

```bash
python run.py --no-take-screenshot-on-error
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

## Output formats

### Text output

The text export is designed for fast manual review and includes:

- generation timestamp
- source URLs
- total listings collected
- listing ID
- source URL
- title
- canonical link
- normalized description

### JSON output

The JSON export is better suited for downstream processing, integrations, or future persistence.

## Testing

Run the full test suite with:

```bash
pytest
```

The tests focus on behaviors that matter most in automation code:

- empty-state handling
- pagination transitions
- fallback extraction
- deduplication
- resilience when a single card fails
- output generation helpers
- CLI argument handling

## Trade-offs and limitations

This project intentionally favors simplicity over framework-heavy abstractions.

Current limitations:

- selectors are tailored to a specific page structure and may require maintenance if the UI changes
- dynamic anti-bot protections can still affect browser automation reliability
- there is no persistence layer yet; output is file-based by design
- tests are unit-focused, not full end-to-end browser validation

These are acceptable trade-offs for a portfolio project focused on maintainability, clarity, and practical automation.

## Possible next improvements

- add fixture-based integration tests for HTML snapshots
- persist runs to a database or lightweight local store
- add retry/backoff strategy for transient navigation failures
- support alternate selector profiles for different layouts
- generate summary metrics per run

## Setup

Install dependencies:

```bash
pip install -r requirements.txt
playwright install
```

Create the input config:

```bash
cp config/searches.example.json config/searches.json
```

Then run:

```bash
python run.py
```