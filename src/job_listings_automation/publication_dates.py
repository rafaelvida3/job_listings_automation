from __future__ import annotations

import re
import unicodedata
from datetime import datetime, timedelta

RELATIVE_PUBLICATION_PATTERN = re.compile(
    r"\bha\s+(?P<amount>\d+)\s+"
    r"(?P<unit>minuto|minutos|hora|horas|dia|dias|semana|semanas|mes|meses)\b",
    re.IGNORECASE,
)


def normalize_relative_publication_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(
        character for character in normalized if not unicodedata.combining(character)
    )
    return " ".join(without_accents.casefold().split())


def find_relative_publication_text(value: str) -> str | None:
    normalized = normalize_relative_publication_text(value)

    match = RELATIVE_PUBLICATION_PATTERN.search(normalized)
    if match is None:
        return None

    return f"há {match.group('amount')} {match.group('unit')}"


def parse_relative_publication_datetime(
    relative_text: str | None,
    collected_at: datetime,
) -> datetime | None:
    if relative_text is None:
        return None

    normalized = normalize_relative_publication_text(relative_text)
    match = RELATIVE_PUBLICATION_PATTERN.search(normalized)

    if match is None:
        return None

    amount = int(match.group("amount"))
    unit = match.group("unit")

    if unit in {"minuto", "minutos"}:
        delta = timedelta(minutes=amount)
    elif unit in {"hora", "horas"}:
        delta = timedelta(hours=amount)
    elif unit in {"dia", "dias"}:
        delta = timedelta(days=amount)
    elif unit in {"semana", "semanas"}:
        delta = timedelta(weeks=amount)
    elif unit in {"mes", "meses"}:
        delta = timedelta(days=amount * 30)
    else:
        return None

    return collected_at - delta


def format_brazilian_datetime(value: datetime | None) -> str:
    if value is None:
        return "N/A"

    return value.strftime("%d/%m/%Y às %H:%M")


def publication_sort_key(published_at: datetime | None) -> tuple[int, float]:
    if published_at is None:
        return (1, 0.0)

    return (0, -published_at.timestamp())
