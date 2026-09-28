"""spec 01 AC-06 (+ FR-06) — raw media and secrets never enter git."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from mentormind.core.config import REPO_ROOT

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or not (REPO_ROOT / ".git").exists(), reason="needs a git checkout"
)


def is_ignored(path: str) -> bool:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "-q", path], cwd=REPO_ROOT, check=False
    )
    return result.returncode == 0


@pytest.mark.parametrize("path", ["data/raw/x.mp4", "data/factory/line3.mov", "clip.wav"])
def test_ac_06_raw_media_is_ignored(path: str) -> None:
    assert is_ignored(path)


def test_ac_06_samples_are_not_ignored() -> None:
    assert not is_ignored("data/samples/demo.mp4")


def test_secret_files_are_ignored_but_guide_is_tracked() -> None:
    assert is_ignored(".secrets/secrets.env")
    assert is_ignored(".secrets/openrouter.key")
    assert not is_ignored(".secrets/README.md")
    assert not is_ignored(".secrets/secrets.env.example")


def test_env_file_is_ignored() -> None:
    assert is_ignored(".env")
    assert not is_ignored(".env.example")


def test_tracked_example_files_exist() -> None:
    for name in (".env.example", ".secrets/README.md", ".secrets/secrets.env.example"):
        assert Path(REPO_ROOT / name).is_file(), name
