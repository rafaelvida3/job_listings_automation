from __future__ import annotations

import sys
from pathlib import Path

from job_listings_automation.main import parse_args


def test_parse_args_should_read_cli_options(monkeypatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run.py",
            "--headless",
            "--output-format",
            "json",
            "--input",
            "config/custom.json",
            "--max-pages",
            "2",
            "--no-take-screenshot-on-error",
        ],
    )

    args = parse_args()

    assert args.headless is True
    assert args.output_format == "json"
    assert args.input == Path("config/custom.json")
    assert args.max_pages == 2
    assert args.take_screenshot_on_error is False
