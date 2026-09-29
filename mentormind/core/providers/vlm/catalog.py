"""Default Qwen3-VL-8B-Instruct model id on each VLM provider.

Vendors spell the same open-weight model differently; ``KNOWHOW_VLM_MODEL`` overrides this.
Check the vendor's model page before relying on an id — ids get renamed and retired.
"""

from __future__ import annotations

DEFAULT_VLM_MODELS: dict[str, str] = {
    # Served name of 3rdparty/vlm_server (its --served-model-name).
    "local_openai": "Qwen/Qwen3-VL-8B-Instruct",
    # Alibaba retires this id on 2026-10-10 (notice of 2026-07-06).
    "qwen_api": "qwen3-vl-8b-instruct",
    "openrouter": "qwen/qwen3-vl-8b-instruct",
    "siliconflow": "Qwen/Qwen3-VL-8B-Instruct",
}


def default_vlm_model(provider: str) -> str | None:
    """Model id to use on ``provider`` when none is configured (None: must be configured)."""
    return DEFAULT_VLM_MODELS.get(provider)
