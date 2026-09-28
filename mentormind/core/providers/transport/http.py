"""HTTP transport for providers: timeout + retry with exponential backoff (spec 04 FR-07).

Providers depend on the :class:`HttpClient` protocol and receive a client by injection, so tests
hand them a fake and never touch the network (constitution Điều 6).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from typing import Any, Protocol

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


def _retry_after_seconds(response: httpx.Response) -> float | None:
    value = response.headers.get("Retry-After", "").strip()
    return float(value) if value.isdigit() else None


def _decode_object(response: httpx.Response) -> dict[str, Any]:
    try:
        body = response.json()
    except ValueError as exc:
        raise ProviderError(
            f"Non-JSON response from {response.request.url}: {response.text[:300]}",
            status_code=response.status_code,
        ) from exc
    if not isinstance(body, dict):
        raise ProviderError(
            f"Expected a JSON object from {response.request.url}, got {type(body).__name__}",
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

    def _send(
        self,
        method: str,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        last_error: ProviderError | None = None
        for attempt in range(self._retry.max_retries + 1):
            retry_after: float | None = None
            try:
                response = self._client.request(method, url, headers=headers, json=json)
            except httpx.TransportError as exc:  # timeouts, refused connections, DNS...
                last_error = ProviderError(f"{method} {url} failed: {exc!r}")
            else:
                if response.is_success:
                    return _decode_object(response)
                last_error = ProviderError(
                    f"{method} {url} -> HTTP {response.status_code}: {response.text[:500]}",
                    status_code=response.status_code,
                )
                if response.status_code not in self._retry.retriable_statuses:
                    raise last_error
                retry_after = _retry_after_seconds(response)
            if attempt < self._retry.max_retries:
                self._sleep(self._retry.delay_for(attempt, retry_after))
        assert last_error is not None
        raise last_error
