from __future__ import annotations

import logging
from pathlib import Path

from job_listings_automation.browser_session import BrowserSession
from job_listings_automation.settings import AppSettings

from .fakes import BrokenContext


def test_close_context_safely_should_ignore_recoverable_errors() -> None:
    session = BrowserSession(
        settings=AppSettings(),
        logger=logging.getLogger("test-browser-session"),
        profile_dir=Path("/tmp/profile"),
    )

    session.close_context_safely(BrokenContext())