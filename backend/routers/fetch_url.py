"""
routers/fetch_url.py
--------------------
POST /api/fetch-url

Fetches a public article URL and returns clean extracted text.
This is a lightweight pre-processing step — the text is then passed
into the existing /api/analyze/stream endpoint unchanged.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, HttpUrl, field_validator

from core.exceptions import DistillError
from core.logging import get_logger
from services.url_extractor import extract_text_from_url

logger = get_logger(__name__)

router = APIRouter(tags=["URL"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class UrlFetchRequest(BaseModel):
    url: str

    @field_validator("url")
    @classmethod
    def url_must_be_non_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url must not be empty")
        # Ensure scheme is present so httpx doesn't choke
        if not v.startswith(("http://", "https://")):
            v = "https://" + v
        return v


class UrlFetchResponse(BaseModel):
    url: str
    title: str
    text: str
    char_count: int
    domain: str


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/fetch-url",
    response_model=UrlFetchResponse,
    summary="Fetch and extract text from a public article URL",
    responses={
        200: {"description": "Text extracted successfully"},
        422: {"description": "Validation error (bad URL format)"},
        400: {"description": "Could not extract content (paywall, 404, etc.)"},
    },
)
async def fetch_url(payload: UrlFetchRequest) -> UrlFetchResponse:
    """
    Fetches the given URL and returns clean article text.

    Supports Medium, Substack, dev.to, Hashnode, and most public blogs.
    Paywalled or JavaScript-only pages will return a clear error message.

    The returned `text` field can be passed directly into
    `POST /api/analyze/stream` as the `transcript` field.
    """
    logger.info("fetch_url.request", url=payload.url)

    try:
        content = await extract_text_from_url(payload.url)
    except DistillError:
        # Re-raise so the global exception handler returns a clean 400 JSON
        raise
    except Exception as exc:
        logger.error("fetch_url.unexpected_error", url=payload.url, error=str(exc))
        raise DistillError(
            "An unexpected error occurred while fetching the URL. "
            "Please try again or paste the text manually."
        ) from exc

    return UrlFetchResponse(
        url=content.url,
        title=content.title,
        text=content.text,
        char_count=content.char_count,
        domain=content.domain,
    )
