from __future__ import annotations
"""
url_extractor.py
----------------
Fetches a public URL and extracts clean article text.
Uses trafilatura's built-in fetcher for reliable browser emulation.
Handles Medium, Substack, dev.to, Hashnode, and most public blogs.

Dependencies:
    pip install trafilatura
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse

import trafilatura
from trafilatura.settings import use_config

from core.exceptions import DistillError
from core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MIN_CONTENT_CHARS = 100
MAX_CONTENT_CHARS = 500_000  # map-reduce handles any length beyond this


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ExtractedContent:
    url: str
    title: str
    text: str
    char_count: int
    domain: str


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_domain(url: str) -> str:
    """Return bare domain, e.g. 'medium.com' from 'https://www.medium.com/...'"""
    parsed = urlparse(url)
    return re.sub(r"^www\.", "", parsed.netloc.lower())


def _validate_url(url: str) -> None:
    """Raise DistillError if URL is structurally invalid."""
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise DistillError(
            "Only http:// and https:// URLs are supported. "
            "Please paste the full article URL."
        )
    if not parsed.netloc:
        raise DistillError(
            "The URL appears to be invalid. Please check and try again."
        )


def _build_trafilatura_config():
    """Return a trafilatura config tuned for article extraction."""
    cfg = use_config()
    cfg.set("DEFAULT", "EXTRACTION_TIMEOUT", "30")
    return cfg


def _extract_with_trafilatura(html: str, url: str) -> tuple[str, str]:
    """
    Run trafilatura extraction on raw HTML.
    Returns (title, body_text).
    Raises DistillError if extracted content is too short.
    """
    cfg = _build_trafilatura_config()

    metadata = trafilatura.extract_metadata(html, default_url=url)
    title = (metadata.title or "") if metadata else ""

    body = trafilatura.extract(
        html,
        url=url,
        config=cfg,
        include_comments=False,
        include_tables=True,
        no_fallback=False,   # allow readability fallback
        favor_precision=False,
    )

    if not body or len(body.strip()) < MIN_CONTENT_CHARS:
        raise DistillError(
            "Could not extract readable content from this URL. "
            "The page may be paywalled, JavaScript-rendered, or empty. "
            "Try copying and pasting the article text instead."
        )

    return title, body.strip()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def extract_text_from_url(url: str) -> ExtractedContent:
    """
    Fetch *url* and return clean article text.

    Uses trafilatura's built-in fetcher which sets realistic browser headers
    and handles redirects — works where raw httpx requests get blocked.

    Raises:
        DistillError — for all user-facing failure cases.
    """
    url = url.strip()
    _validate_url(url)

    domain = _get_domain(url)
    logger.info("url_extractor.fetch_start", url=url, domain=domain)

    # trafilatura.fetch_url handles headers, redirects, and encoding
    html = trafilatura.fetch_url(url)

    if not html:
        raise DistillError(
            f"Could not retrieve content from {domain}. "
            "The page may require JavaScript or block automated access. "
            "Try copying and pasting the article text instead."
        )

    title, body = _extract_with_trafilatura(html, url)

    if len(body) > MAX_CONTENT_CHARS:
        logger.info(
            "url_extractor.truncating",
            original=len(body),
            limit=MAX_CONTENT_CHARS,
        )
        body = body[:MAX_CONTENT_CHARS]

    content = ExtractedContent(
        url=url,
        title=title,
        text=body,
        char_count=len(body),
        domain=domain,
    )

    logger.info(
        "url_extractor.fetch_done",
        domain=domain,
        title=title,
        char_count=content.char_count,
    )
    return content
