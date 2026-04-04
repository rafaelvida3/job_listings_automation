# Job Listings Automation

Python project using Playwright to automate the extraction of job listings from dynamic pages with pagination, side detail panels, and persistent session authentication.

The goal of this project is to demonstrate:
- automated navigation in dynamic interfaces
- structured extraction of job listing data
- handling of pagination and incremental scrolling
- text and URL normalization
- clear logging for debugging and traceability
- automated tests for core utilities

## What the project does

The application:

1. reads a list of search URLs from `config/searches.json`  
2. opens each search in a Playwright browser with a persistent profile  
3. waits for the job listings to be available  
4. ignores pages that enter an empty search state  
5. loads all visible cards via incremental scrolling  
6. opens each job and extracts title, link, and description  
7. removes duplicates across searches  
8. saves the final output to `.txt` and logs the execution  

## Requirements

- Python 3.11+  
- Linux with graphical environment for Playwright browser  
- dependencies installed via `pip`  

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Configuration

```bash
cp config/searches.example.json config/searches.json
```

## Run

```bash
python run.py
```

## Tests

```bash
pytest
```

## Notes

- runtime folders are ignored (`logs/`, `output/`, `browser_profile/`)
- selectors may require updates if target UI changes

## Responsible use

Respect terms of service and applicable laws when using automation.