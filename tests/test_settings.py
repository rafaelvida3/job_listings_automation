from __future__ import annotations

import pytest

from job_listings_automation.settings import AppSettings


def test_app_settings_should_reject_invalid_max_pages() -> None:
    with pytest.raises(ValueError, match="max_pages"):
        AppSettings(max_pages=0)


def test_app_settings_should_reject_invalid_reading_delay_range() -> None:
    with pytest.raises(ValueError, match="max_reading_delay_ms"):
        AppSettings(min_reading_delay_ms=5, max_reading_delay_ms=1)
