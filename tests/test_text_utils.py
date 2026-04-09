from __future__ import annotations

from job_listings_automation.text_utils import clean_multiline_text, clean_single_line


def test_clean_single_line_should_collapse_whitespace() -> None:
    result = clean_single_line("  Senior   Python   Developer   ")
    assert result == "Senior Python Developer"


def test_clean_multiline_text_should_keep_meaningful_lines() -> None:
    source = "\n  Remote role  \n\n  Python and APIs \n  \n"
    result = clean_multiline_text(source)
    assert result == "Remote role\nPython and APIs"
