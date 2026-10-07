"""HTTP transport for providers: timeout + retry with exponential backoff (spec 04 FR-07).

Providers depend on the :class:`HttpClient` protocol and receive a client by injection, so tests
hand them a fake and never touch the network (constitution art. 6).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import urlsplit, urlunsplit

import httpx

from mentormind.core.providers.errors import ProviderError
from mentormind.core.providers.transport.retry import RetryPolicy

DEFAULT_TIMEOUT_S = 90.0


class HttpClient(Protocol):
    """The HTTP surface the provider layer needs."""

    def post_json(
        self, url: str, payload: Mapping[str, Any], *, headers: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        """POST ``payload`` as JSON and return the decoded JSON object."""
        ...

    def get_json(self, url: str, *, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
        """GET ``url`` and return the decoded JSON object."""
        ...


def redact_url(url: str | httpx.URL) -> str:
    """``url`` without ``user:password@``: a base URL may carry basic-auth (e.g. an ngrok tunnel)."""
    parts = urlsplit(str(url))
    if "@" not in parts.netloc:
        return str(url)
    return urlunsplit(parts._replace(netloc=parts.netloc.rpartition("@")[2]))


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After", "").strip()
    return float(value) if value.isdigit() else None


def _decode_object(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderError(
            f"Non-JSON response from {redact_url(response.request.url)}: {response.text[:300]}",
            status_code=response.status_code,
        ) from exc
    if not isinstance(body, dict):
        raise ProviderError(
            f"Expected a JSON object from {redact_url(response.request.url)}, got {type(body).__name__}",
            status_code=response.status_code,
        )
    return body


class HttpxClient:
    """:class:`HttpClient` over ``httpx`` with per-call timeout and bounded retries."""

    def __init__(
        self,
        *,
        timeout_s: float = DEFAULT_TIMEOUT_S,
        retry: RetryPolicy | None = None,
        sleep: Callable[[float], None] = time.sleep,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._client = httpx.Client(timeout=timeout_s, transport=transport)
        self._retry = retry or RetryPolicy()
        self._sleep = sleep

    def post_json(
        self, url: str, payload: Mapping[str, Any], *, headers: Mapping[str, str] | None = None
    ) -> dict[str, Any]:
        return self._send("POST", url, headers=headers, json=dict(payload))

    def get_json(self, url: str, *, headers: Mapping[str, str] | None = None) -> dict[str, Any]:
        return self._send("GET", url, headers=headers)

    def post_file(
        self,
        url: str,
        path: Path,
        *,
        field: str = "file",
        data: Mapping[str, str | Sequence[str]] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, Any]:
        """POST ``path`` as multipart ``field`` plus form ``data``; the file is streamed, reopened per try.

        Raises:
            ProviderError: the file cannot be read, or the request failed after the retries.
        """
        return self._send("POST", url, headers=headers, upload=(field, path), data=data)

    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        json: dict[str, Any] | None = None,
        upload: tuple[str, Path] | None = None,
        data: Mapping[str, str | Sequence[str]] | None = None,
    ) -> dict[str, Any]:
        shown = redact_url(url)
        last_error: ProviderError | None = None
        for attempt in range(self._retry.max_retries + 1):
            retry_after: float | None = None
            try:
                response = self._request(method, url, headers=headers, json=json, upload=upload, data=data)
            except httpx.TransportError as exc:  # timeouts, refused connections, DNS...
                last_error = ProviderError(f"{method} {shown} failed: {exc!r}")
            else:
                if response.is_success:
                    return _decode_object(response)
                last_error = ProviderError(
                    f"{method} {shown} -> HTTP {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                )
                if response.status_code not in self._retry.retriable_statuses:
                    raise last_error
                retry_after = _retry_after_seconds(response)
            if attempt < self._retry.max_retries:
                self._sleep(self._retry.delay_for(attempt, retry_after))
        assert last_error is not None
        raise last_error

    def _request(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        json: dict[str, Any] | None,
        upload: tuple[str, Path] | None,
        data: Mapping[str, str | Sequence[str]] | None,
    ) -> httpx.Response:
        if upload is None:
            return self._client.request(method, url, headers=headers, json=json)
        field, path = upload
        form = {key: value if isinstance(value, str) else list(value) for key, value in (data or {}).items()}
        try:
            handle = path.open("rb")
        except OSError as exc:
            raise ProviderError(f"Không đọc được {path.name}: {exc}") from exc
        with handle:
            return self._client.request(method, url, headers=headers, data=form, files={field: (path.name, handle)})
