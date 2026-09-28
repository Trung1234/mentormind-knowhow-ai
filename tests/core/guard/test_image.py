"""Face-model download is verified before any frame is blurred with it."""

from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from mentormind.core.guard import image
from mentormind.core.guard.image import FaceBlurError


def test_face_model_download_is_checksum_verified(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    tampered = httpx.Response(200, content=b"not the model", request=httpx.Request("GET", "u"))
    monkeypatch.setattr(image.httpx, "get", lambda *a, **k: tampered)
    with pytest.raises(FaceBlurError, match="SHA-256"):
        image.ensure_face_model(tmp_path / "m.onnx")
    assert not (tmp_path / "m.onnx").exists()
