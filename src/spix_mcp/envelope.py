"""Universal envelope parser for Spix API responses."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import orjson

if TYPE_CHECKING:
    import httpx


@dataclass
class ApiResponse:
    """Parsed universal envelope from the Spix API.

    Every API response is wrapped in this envelope format:
    - ok: boolean indicating success
    - data: response payload (dict for single items, list for collections)
    - error: error details when ok=False
    - pagination: cursor info for paginated responses
    - warnings: non-fatal warnings to surface to the user
    - meta: request metadata (request_id, timestamp, dry_run)
    """

    ok: bool
    status_code: int
    data: dict | list | None = None
    error: dict | None = None
    pagination: dict | None = None
    warnings: list[str] = field(default_factory=list)
    meta: dict = field(default_factory=dict)
    raw_body: str = ""
    headers: dict[str, str] = field(default_factory=dict)

    @property
    def is_list(self) -> bool:
        """Check if response data is a list (collection response)."""
        return isinstance(self.data, list)

    @property
    def request_id(self) -> str:
        """Get the request ID from metadata."""
        return self.meta.get("request_id", "unknown")

    @property
    def dry_run(self) -> bool:
        """Check if this was a dry-run request."""
        return self.meta.get("dry_run", False)

    @property
    def error_code(self) -> str | None:
        """Get the error code if present."""
        return self.error.get("code") if self.error else None

    @property
    def error_message(self) -> str | None:
        """Get the error message if present."""
        return self.error.get("message") if self.error else None

    @property
    def retry_after(self) -> str | None:
        """Get the Retry-After header value if present."""
        return self.headers.get("retry-after")

    @property
    def retryable(self) -> bool:
        """Check if the error is retryable."""
        return self.error.get("retryable", False) if self.error else False

    @staticmethod
    def connection_error() -> ApiResponse:
        """Create a response for connection failures."""
        return ApiResponse(
            ok=False,
            status_code=0,
            error={
                "code": "connection_error",
                "message": "Could not connect to the API server. Check your network and SPIX_API_URL.",
                "retryable": True,
            },
        )

    @staticmethod
    def timeout_error() -> ApiResponse:
        """Create a response for request timeouts."""
        return ApiResponse(
            ok=False,
            status_code=0,
            error={
                "code": "timeout",
                "message": "Request timed out",
                "retryable": True,
            },
        )


def parse_envelope(response: httpx.Response) -> ApiResponse:
    """Parse the universal JSON envelope from any API response.

    Args:
        response: The httpx Response object to parse.

    Returns:
        ApiResponse with parsed envelope fields.
    """
    # Fix 1: HTTP 204 No Content is a success with no body
    if response.status_code == 204:
        return ApiResponse(
            ok=True,
            status_code=204,
            headers=dict(response.headers),
        )

    try:
        body = orjson.loads(response.content)
    except (orjson.JSONDecodeError, ValueError):
        # Non-JSON response — likely HTML error page from reverse proxy or Django
        if response.status_code == 404:
            msg = "Resource not found."
        elif response.status_code == 405:
            msg = "Method not allowed."
        else:
            msg = f"Non-JSON response from API (HTTP {response.status_code})."
        return ApiResponse(
            ok=False,
            status_code=response.status_code,
            error={"code": "invalid_response", "message": msg},
            raw_body=response.content[:500].decode("utf-8", errors="replace"),
        )

    return ApiResponse(
        ok=body.get("ok", False),
        status_code=response.status_code,
        data=body.get("data"),
        error=body.get("error"),
        pagination=body.get("pagination"),
        warnings=body.get("warnings", []),
        meta=body.get("meta", {}),
        raw_body=response.text,
        headers=dict(response.headers),
    )
