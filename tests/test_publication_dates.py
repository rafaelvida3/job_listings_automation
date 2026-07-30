from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from job_listings_automation.exporters import sort_listings_by_publication_date
from job_listings_automation.models import ListingData
from job_listings_automation.publication_dates import parse_relative_publication_datetime

FIXED_COLLECTED_AT = datetime(2026, 7, 30, 12, 3, tzinfo=ZoneInfo("America/Sao_Paulo"))


def parse(value: str) -> datetime | None:
    return parse_relative_publication_datetime(value, FIXED_COLLECTED_AT)


def test_parse_relative_publication_minutes() -> None:
    assert parse("há 15 minutos") == datetime(
        2026,
        7,
        30,
        11,
        48,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_one_hour() -> None:
    assert parse("há 1 hora") == datetime(
        2026,
        7,
        30,
        11,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_hours() -> None:
    assert parse("Anunciada há 23 horas") == datetime(
        2026,
        7,
        29,
        13,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_one_day() -> None:
    assert parse("há 1 dia") == datetime(
        2026,
        7,
        29,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_days() -> None:
    assert parse("há 2 dias") == datetime(
        2026,
        7,
        28,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_one_week() -> None:
    assert parse("há 1 semana") == datetime(
        2026,
        7,
        23,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_weeks() -> None:
    assert parse("há 3 semanas") == datetime(
        2026,
        7,
        9,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_one_month() -> None:
    assert parse("há 1 mês") == datetime(
        2026,
        6,
        30,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_months() -> None:
    assert parse("há 2 meses") == datetime(
        2026,
        5,
        31,
        12,
        3,
        tzinfo=ZoneInfo("America/Sao_Paulo"),
    )


def test_parse_relative_publication_invalid_text() -> None:
    assert parse("publicada recentemente") is None


def test_parse_relative_publication_missing_text() -> None:
    assert parse_relative_publication_datetime(None, FIXED_COLLECTED_AT) is None


def test_sort_listings_by_publication_date_descending() -> None:
    older = ListingData("1", "Older", None, None, "source", published_at=parse("há 2 dias"))
    newer = ListingData("2", "Newer", None, None, "source", published_at=parse("há 1 hora"))

    assert sort_listings_by_publication_date([older, newer]) == [newer, older]


def test_sort_listings_without_publication_date_last() -> None:
    missing = ListingData("1", "Missing", None, None, "source")
    dated = ListingData("2", "Dated", None, None, "source", published_at=parse("há 1 dia"))

    assert sort_listings_by_publication_date([missing, dated]) == [dated, missing]
