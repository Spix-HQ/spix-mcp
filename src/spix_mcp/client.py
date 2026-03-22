"""HTTP client wrapper for Spix API."""

from __future__ import annotations

import logging
import os
import uuid

import httpx
import orjson

__version__ = "0.0.1"
from spix_mcp.envelope import ApiResponse, parse_envelope

logger = logging.getLogger("spix.api")

# Default API URL, can be overridden via SPIX_API_URL env var or config
DEFAULT_API_URL = "https://api.spix.sh/v1"

# Explicit timeouts per architecture spec Section 4:
# connect=5s, read=30s, write=10s
DEFAULT_TIMEOUT = httpx.Timeout(
    connect=5.0,
    read=30.0,
    write=10.0,
    pool=5.0,
)


class SpixClient:
    """Thin HTTP client wrapper for Spix API.

    All requests return ApiResponse objects with parsed universal envelope.

    IMPORTANT: Create ONE client per CLI invocation and reuse it.
    Never create per-request clients as this destroys connection pooling.

    Timeout Configuration:
    - connect: 5 seconds (TCP connection establishment)
    - read: 30 seconds (waiting for response data)
    - write: 10 seconds (sending request data)
    """

    def __init__(
        self,
        api_key: str | None = None,
        timeout_ms: int | None = None,
        debug: bool = False,
        dry_run: bool = False,
        base_url: str | None = None,
    ):
        """Initialize the client.

        Args:
            api_key: API key for authentication.
            timeout_ms: Optional overall timeout in milliseconds. If not set,
                uses explicit per-operation timeouts (connect=5s, read=30s, write=10s).
            debug: Enable debug logging of requests/responses.
            dry_run: Pass dry_run=true to all requests.
            base_url: Override the API base URL.
        """
        self.api_key = api_key
        self.dry_run = dry_run
        self.debug = debug

        # Resolve base URL: parameter > env var > default
        # Ensure trailing slash so httpx resolves relative paths correctly
        raw_url = base_url or os.environ.get("SPIX_API_URL", DEFAULT_API_URL)
        self.base_url = raw_url.rstrip("/") + "/"

        # Fix 4: Don't set Content-Type as default header; httpx sets it
        # automatically when json= parameter is used.
        headers = {
            "Accept": "application/json",
            "User-Agent": f"spix-cli/{__version__}",
        }
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        # Use explicit per-operation timeouts if no overall timeout specified
        if timeout_ms is not None:
            timeout = httpx.Timeout(timeout_ms / 1000)
        else:
            timeout = DEFAULT_TIMEOUT

        self._client = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=timeout,
            follow_redirects=True,
            http2=True,
        )

    def get(self, path: str, params: dict | None = None) -> ApiResponse:
        """Perform a GET request.

        Args:
            path: API endpoint path (e.g., "/playbooks").
            params: Optional query parameters.

        Returns:
            Parsed ApiResponse.
        """
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        files: dict | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Perform a POST request.

        Args:
            path: API endpoint path.
            json: Request body as dict (mutually exclusive with files).
            params: Optional query parameters.
            files: Optional file upload dict for multipart requests.
            idempotency_key: Optional idempotency key. Auto-generated if not provided.

        Returns:
            Parsed ApiResponse.
        """
        kwargs: dict = {}
        if json is not None:
            kwargs["json"] = json
        if params is not None:
            kwargs["params"] = params
        if files is not None:
            kwargs["files"] = files
        return self._request("POST", path, idempotency_key=idempotency_key, **kwargs)

    def patch(
        self,
        path: str,
        json: dict | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Perform a PATCH request.

        Args:
            path: API endpoint path.
            json: Request body as dict.
            idempotency_key: Optional idempotency key. Auto-generated if not provided.

        Returns:
            Parsed ApiResponse.
        """
        return self._request("PATCH", path, json=json, idempotency_key=idempotency_key)

    def put(
        self,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Perform a PUT request.

        Args:
            path: API endpoint path.
            json: Request body as dict.
            params: Optional query parameters.
            idempotency_key: Optional idempotency key. Auto-generated if not provided.

        Returns:
            Parsed ApiResponse.
        """
        return self._request("PUT", path, json=json, params=params, idempotency_key=idempotency_key)

    def delete(
        self,
        path: str,
        json: dict | None = None,
        params: dict | None = None,
        idempotency_key: str | None = None,
    ) -> ApiResponse:
        """Perform a DELETE request.

        Args:
            path: API endpoint path.
            json: Optional request body as dict.
            params: Optional query parameters.
            idempotency_key: Optional idempotency key. Auto-generated if not provided.

        Returns:
            Parsed ApiResponse.
        """
        return self._request("DELETE", path, json=json, params=params, idempotency_key=idempotency_key)

    def _request(
        self,
        method: str,
        path: str,
        idempotency_key: str | None = None,
        **kwargs,
    ) -> ApiResponse:
        """Execute an HTTP request and return parsed response.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE).
            path: API endpoint path.
            idempotency_key: Optional idempotency key for write operations.
            **kwargs: Additional arguments passed to httpx.request().

        Returns:
            Parsed ApiResponse. On connection/timeout errors, returns
            ApiResponse.connection_error() or ApiResponse.timeout_error().
        """
        # Strip leading slash — httpx treats "/foo" as absolute from host root,
        # bypassing the base_url path prefix (e.g., /v1). "foo" is relative.
        if path.startswith("/"):
            path = path[1:]

        # Ensure trailing slash — Django returns 301 for missing slashes,
        # and httpx downgrades POST→GET on 301 redirect, breaking all writes.
        if path and not path.endswith("/") and "?" not in path:
            path = path + "/"

        # Inject dry-run query parameter
        if self.dry_run:
            params = kwargs.get("params") or {}
            params["dry_run"] = "true"
            kwargs["params"] = params

        # Inject idempotency key for write operations
        headers: dict[str, str] = {}
        if method in ("POST", "PATCH", "PUT"):
            key = idempotency_key or str(uuid.uuid4())
            headers["Idempotency-Key"] = key

        # Debug logging
        if self.debug:
            body = kwargs.get("json")
            logger.debug("→ %s %s", method, path)
            if kwargs.get("params"):
                logger.debug("  Params: %s", kwargs["params"])
            if body:
                logger.debug("  Body: %s", orjson.dumps(body).decode())

        try:
            response = self._client.request(method, path, headers=headers, **kwargs)
        except httpx.TimeoutException as e:
            if self.debug:
                logger.debug("← Timeout: %s", e)
            return ApiResponse.timeout_error()
        except httpx.TransportError as e:
            if self.debug:
                logger.debug("← Connection error: %s", e)
            return ApiResponse.connection_error()

        if self.debug:
            logger.debug("← %d", response.status_code)
            logger.debug("  Body: %s", response.text[:500])

        return parse_envelope(response)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()

    def __enter__(self) -> SpixClient:
        """Context manager entry."""
        return self

    def __exit__(self, *args) -> None:
        """Context manager exit - ensures client is closed."""
        self.close()
