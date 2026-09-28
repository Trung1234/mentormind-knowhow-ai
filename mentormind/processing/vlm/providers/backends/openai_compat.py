"""OpenAI-compatible VLM provider: self-hosted vLLM and every cloud vendor in one class.

Frames are sent as base64 ``image_url`` parts of ONE user message, text first ("the following
images are consecutive frames..."), which every OpenAI-compatible endpoint accepts — including
the self-hosted Qwen3-VL-8B server in ``3rdparty/vlm_server`` (spec 04 §2, FR-08).
"""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from typing import Any, Self

from mentormind.core.config import JsonMode
from mentormind.core.providers.errors import ProviderConfigError, ProviderError
from mentormind.core.providers.models import ProviderConfig, TokenUsage
from mentormind.core.providers.openai_compat import (
    GENERIC_OPENAI_COMPATIBLE,
    OPENAI_COMPAT_ENDPOINTS,
    is_private_url,
)
from mentormind.core.providers.transport import HttpClient, HttpxClient, RetryPolicy
from mentormind.processing.vlm.providers.base import VLMProvider
from mentormind.processing.vlm.providers.catalog import default_vlm_model
from mentormind.processing.vlm.providers.models import ImageInput
from mentormind.processing.vlm.providers.registry import register_vlm

SECRETS_GUIDE = ".secrets/README.md"


@register_vlm(*OPENAI_COMPAT_ENDPOINTS, GENERIC_OPENAI_COMPATIBLE)
class OpenAICompatVLM(VLMProvider):
    def __init__(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        is_cloud: bool,
        api_key: str | None,
        json_mode: JsonMode,
        max_tokens: int | None,
        http: HttpClient,
        extra_body: Mapping[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.model = model
        self.is_cloud = is_cloud
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._json_mode = json_mode
        self._max_tokens = max_tokens
        self._http = http
        self._extra_body = dict(extra_body or {})

    @classmethod
    def api_key_env(cls, name: str) -> str | None:
        endpoint = OPENAI_COMPAT_ENDPOINTS.get(name)
        return endpoint.api_key_env if endpoint else None

    @classmethod
    def from_config(cls, config: ProviderConfig, http: HttpClient | None = None) -> Self:
        name = config.provider
        endpoint = OPENAI_COMPAT_ENDPOINTS.get(name)
        base_url = config.base_url or (endpoint.base_url if endpoint else None)
        if not base_url:
            raise ProviderConfigError(
                f"Provider '{name}' cần địa chỉ server: đặt KNOWHOW_VLM_BASE_URL "
                "(vd. http://gpu-box:8100/v1)."
            )
        model = config.model or default_vlm_model(name)
        if not model:
            raise ProviderConfigError(f"Provider '{name}' cần tên model: đặt KNOWHOW_VLM_MODEL.")
        api_key = config.api_key.get_secret_value() if config.api_key else None
        if endpoint and endpoint.is_cloud and not api_key:
            raise ProviderConfigError(
                f"Thiếu API key cho provider '{name}': thêm {endpoint.api_key_env}=... vào "
                f".secrets/secrets.env (hướng dẫn: {SECRETS_GUIDE})."
            )
        # A vendor row that is cloud stays cloud; anything else is judged by where the URL
        # actually points, so a "local" provider aimed at a public host is still guarded.
        is_cloud = bool(endpoint and endpoint.is_cloud) or not is_private_url(base_url)
        json_mode = config.json_mode
        if json_mode == "auto":
            json_mode = endpoint.json_mode if endpoint else "off"
        return cls(
            name=name,
            base_url=base_url,
            model=model,
            is_cloud=is_cloud,
            api_key=api_key,
            json_mode=json_mode,
            max_tokens=config.max_tokens,
            extra_body=config.extra_body,
            http=http
            or HttpxClient(
                timeout_s=config.timeout_s, retry=RetryPolicy(max_retries=config.max_retries)
            ),
        )

    def _complete(
        self,
        images: Sequence[ImageInput],
        prompt: str,
        *,
        json_schema: Mapping[str, Any] | None,
        system: str | None,
        temperature: float | None,
        max_tokens: int | None,
    ) -> tuple[str, TokenUsage | None]:
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content += [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image.mime_type};base64,"
                    + base64.b64encode(image.data).decode("ascii")
                },
            }
            for image in images
        ]
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": content})
        # Configured extras first, so the call's own fields always win over them.
        payload: dict[str, Any] = {**self._extra_body, "model": self.model, "messages": messages}
        if temperature is not None:
            payload["temperature"] = temperature
        if (max_tokens or self._max_tokens) is not None:
            payload["max_tokens"] = max_tokens or self._max_tokens
        response_format = self._response_format(json_schema)
        if response_format is not None:
            payload["response_format"] = response_format

        body = self._http.post_json(
            f"{self._base_url}/chat/completions", payload, headers=self._headers()
        )
        return _message_text(body), _usage(body)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"} if self._api_key else {}

    def _response_format(self, json_schema: Mapping[str, Any] | None) -> dict[str, Any] | None:
        if json_schema is None or self._json_mode == "off":
            return None
        if self._json_mode == "json_object":
            return {"type": "json_object"}
        return {
            "type": "json_schema",
            "json_schema": {"name": "knowhow_output", "schema": dict(json_schema)},
        }


def _message_text(body: Mapping[str, Any]) -> str:
    try:
        content = body["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError(f"Unexpected chat response shape: {str(body)[:500]}") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):  # some vendors return content parts
        return "".join(str(part.get("text", "")) for part in content if isinstance(part, dict))
    raise ProviderError(f"Unexpected message content type: {type(content).__name__}")


def _usage(body: Mapping[str, Any]) -> TokenUsage | None:
    usage = body.get("usage")
    if not isinstance(usage, dict):
        return None
    return TokenUsage(
        prompt_tokens=int(usage.get("prompt_tokens") or 0),
        completion_tokens=int(usage.get("completion_tokens") or 0),
    )
