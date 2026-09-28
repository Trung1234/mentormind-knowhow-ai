"""spec 04 AC-03, AC-13 — confidential data never reaches a cloud provider, not even its files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from pydantic import SecretStr

from mentormind.core.config import Settings
from mentormind.core.guard import ConfidentialDataError
from mentormind.processing.vlm import providers as vlm_providers
from mentormind.processing.vlm.providers import get_vlm_provider
from mentormind.processing.vlm.providers.backends.fake import FakeVLM
from mentormind.processing.vlm.providers.models import ImageInput
from tests.processing.vlm.fakes import RecordingHttp


def with_provider(settings: Settings, **update: Any) -> Settings:
    return settings.model_copy(update=update)


def test_ac_03_confidential_video_cloud_provider_raises_before_reading_files(
    frames: list[Path], monkeypatch: pytest.MonkeyPatch
) -> None:
    opened: list[Path] = []
    real_read = vlm_providers.base.read_image

    def spy(path: Path) -> ImageInput:
        opened.append(path)
        return real_read(path)

    monkeypatch.setattr(vlm_providers.base, "read_image", spy)
    cloud = FakeVLM(is_cloud=True, name="openrouter")
    with pytest.raises(ConfidentialDataError):
        cloud.generate(frames, "mô tả", classification="factory_confidential")
    assert opened == []
    assert cloud.calls == []


def test_ac_03_cloud_http_provider_sends_nothing(
    settings: Settings, http: RecordingHttp, frames: list[Path]
) -> None:
    settings = with_provider(settings, vlm_provider="openrouter", vlm_api_key=SecretStr("sk"))
    vlm = get_vlm_provider(settings, http=http)
    assert vlm.is_cloud
    with pytest.raises(ConfidentialDataError):
        vlm.generate(frames, "mô tả", classification="factory_confidential")
    assert http.posts == []


def test_ac_03_self_hosted_provider_accepts_confidential(
    settings: Settings, http: RecordingHttp, frames: list[Path]
) -> None:
    vlm = get_vlm_provider(settings, http=http)
    assert vlm.name == "local_openai" and not vlm.is_cloud
    vlm.generate(frames, "mô tả", classification="factory_confidential")
    assert len(http.posts) == 1


def test_ac_13_local_provider_aimed_at_public_host_counts_as_cloud(
    settings: Settings, http: RecordingHttp, frames: list[Path]
) -> None:
    settings = with_provider(settings, vlm_base_url="https://vlm.example.com/v1")
    vlm = get_vlm_provider(settings, http=http)
    assert vlm.is_cloud
    with pytest.raises(ConfidentialDataError):
        vlm.generate(frames, "mô tả", classification="factory_confidential")
