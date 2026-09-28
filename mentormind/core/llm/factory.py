"""``get_llm_provider`` — the only way business code obtains an LLM (spec 06 §2).

Switching self-host <-> cloud is config only (constitution art. 5).
"""

from __future__ import annotations

from pydantic import SecretStr

from mentormind.core.config import Settings, get_settings, lookup_secret
from mentormind.core.guard import GuardPolicy
from mentormind.core.llm.base import LLMProvider
from mentormind.core.llm.registry import LLM_REGISTRY
from mentormind.core.providers.models import ProviderConfig
from mentormind.core.providers.transport import HttpClient


def llm_config_from_settings(settings: Settings) -> ProviderConfig:
    """Translate ``KNOWHOW_LLM_*`` settings (+ the provider's own secret) into a config."""
    # ``KNOWHOW_LLM_API_KEY=`` (blank line in .env) arrives as SecretStr(""): treat as unset.
    api_key = settings.llm_api_key
    if api_key is not None and not api_key.get_secret_value().strip():
        api_key = None
    provider_cls = LLM_REGISTRY.get(settings.llm_provider)
    key_env = provider_cls.api_key_env(settings.llm_provider) if provider_cls else None
    if api_key is None and key_env:
        found = lookup_secret(key_env, secrets_file=settings.secrets_file)
        api_key = SecretStr(found) if found else None
    base_url = settings.llm_base_url or None
    url_env = provider_cls.base_url_env(settings.llm_provider) if provider_cls else None
    if base_url is None and url_env:
        base_url = lookup_secret(url_env, secrets_file=settings.secrets_file)
    return ProviderConfig(
        provider=settings.llm_provider,
        model=settings.llm_model or None,
        base_url=base_url,
        api_key=api_key,
        timeout_s=settings.llm_timeout_s,
        max_retries=settings.llm_max_retries,
        json_mode=settings.llm_json_mode,
        max_tokens=settings.llm_max_tokens,
        extra_body=settings.llm_extra_body,
    )


def get_llm_provider(
    settings: Settings | None = None, *, http: HttpClient | None = None
) -> LLMProvider:
    """Build the LLM provider selected by ``KNOWHOW_LLM_PROVIDER``.

    Raises:
        ProviderConfigError: unknown provider name, missing key, base URL or model.
    """
    settings = settings or get_settings()
    provider = LLM_REGISTRY.create(llm_config_from_settings(settings), http)
    provider.guard_policy = GuardPolicy(
        mask_text=settings.guard_mask_text,
        audit_dir=settings.guard_audit_dir,
        extra_patterns=settings.guard_extra_patterns,
    )
    return provider
