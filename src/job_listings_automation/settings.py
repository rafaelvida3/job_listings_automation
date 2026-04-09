from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

TIMEZONE = ZoneInfo("America/Sao_Paulo")
ROOT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logs"
PROFILE_DIR = ROOT_DIR / "browser_profile"
CONFIG_FILE = ROOT_DIR / "config" / "searches.json"


@dataclass(frozen=True, slots=True)
class AppSettings:
    headless: bool = False
    slow_mo_ms: int = 150
    page_load_timeout_ms: int = 60_000
    detail_load_timeout_ms: int = 15_000
    min_reading_delay_ms: int = 1_200
    max_reading_delay_ms: int = 3_200
    max_scroll_rounds: int = 30
    stale_scroll_retries: int = 3
    max_pages: int | None = None
    take_screenshot_on_error: bool = True

    def __post_init__(self) -> None:
        numeric_fields = {
            "slow_mo_ms": self.slow_mo_ms,
            "page_load_timeout_ms": self.page_load_timeout_ms,
            "detail_load_timeout_ms": self.detail_load_timeout_ms,
            "min_reading_delay_ms": self.min_reading_delay_ms,
            "max_reading_delay_ms": self.max_reading_delay_ms,
            "max_scroll_rounds": self.max_scroll_rounds,
            "stale_scroll_retries": self.stale_scroll_retries,
        }

        for field_name, value in numeric_fields.items():
            if value < 0:
                raise ValueError(f"{field_name} must be greater than or equal to zero.")

        if self.max_reading_delay_ms < self.min_reading_delay_ms:
            raise ValueError(
                "max_reading_delay_ms must be greater than or equal to min_reading_delay_ms."
            )

        if self.max_pages is not None and self.max_pages <= 0:
            raise ValueError("max_pages must be greater than zero when provided.")


def get_now() -> datetime:
    return datetime.now(TIMEZONE)


def build_timestamp() -> str:
    return get_now().strftime("%Y-%m-%d_%H-%M-%S")


def ensure_directories() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def load_search_urls(config_file: Path = CONFIG_FILE) -> list[str]:
    if not config_file.exists():
        raise FileNotFoundError(
            "Search config not found. Copy config/searches.example.json to config/searches.json."
        )

    raw_data = json.loads(config_file.read_text(encoding="utf-8"))
    search_urls = [str(url).strip() for url in raw_data.get("search_urls", []) if str(url).strip()]

    if not search_urls:
        raise ValueError("The search config must contain at least one non-empty URL.")

    return search_urls
