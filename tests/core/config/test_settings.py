"""spec 01 FR-03 — settings come from KNOWHOW_* variables and .env files."""

from __future__ import annotations

import pytest

from mentormind.core.config import Settings


def test_fr_03_settings_read_prefixed_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KNOWHOW_VLM_PROVIDER", "openrouter")
    monkeypatch.setenv("KNOWHOW_VLM_MAX_FRAMES", "12")
    settings = Settings(_env_file=None)
    assert settings.vlm_provider == "openrouter"
    assert settings.vlm_max_frames == 12


def test_settings_defaults_target_the_self_hosted_vlm(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("KNOWHOW_VLM_PROVIDER", "KNOWHOW_VLM_FPS", "KNOWHOW_VLM_MAX_FRAMES"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=None)
    assert settings.vlm_provider == "local_openai"
    assert settings.vlm_fps == 4
    assert settings.vlm_max_frames == 48


def test_env_example_parses_into_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    from mentormind.core.config import REPO_ROOT

    for name in ("KNOWHOW_VLM_PROVIDER", "KNOWHOW_VLM_BASE_URL", "KNOWHOW_VLM_EXTRA_BODY"):
        monkeypatch.delenv(name, raising=False)
    settings = Settings(_env_file=REPO_ROOT / ".env.example")
    assert settings.vlm_provider == "local_openai"
    assert settings.vector_backend == "pgvector"
    assert not settings.vlm_base_url  # blank -> provider default
    assert settings.vlm_extra_body == {"presence_penalty": 1.5}
    assert not settings.vlm_model
