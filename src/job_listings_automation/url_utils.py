from __future__ import annotations

from typing import Optional
from urllib.parse import urljoin, urlparse, urlunparse


def normalize_listing_url(raw_url: Optional[str], base_origin: str = "") -> str:
    if not raw_url:
        return ""

    parsed_url = urlparse(raw_url)
    if parsed_url.scheme and parsed_url.netloc:
        clean_path = parsed_url.path.rstrip("/")
        if clean_path:
            clean_path = f"{clean_path}/"
        return urlunparse((parsed_url.scheme, parsed_url.netloc, clean_path, "", "", ""))

    if not base_origin:
        return ""

    combined_url = urljoin(base_origin, raw_url)
    parsed_combined_url = urlparse(combined_url)
    if not parsed_combined_url.scheme or not parsed_combined_url.netloc:
        return ""

    clean_path = parsed_combined_url.path.rstrip("/")
    if clean_path:
        clean_path = f"{clean_path}/"
    return urlunparse(
        (
            parsed_combined_url.scheme,
            parsed_combined_url.netloc,
            clean_path,
            "",
            "",
            ""
        )
    )
