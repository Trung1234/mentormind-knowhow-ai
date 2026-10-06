"""Spec 03b D11b — guard against drifting from the stopgap segmenter spec 04 ships.

Spec 04 owns ``processing/vlm/sweep/windows.py`` (a fixed-window cutter used until spec 03 landed).
This module is written independently and must keep agreeing with it on ids and window bounds; the
test only *reads* that module. If it fails, tell the owner of whichever side changed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mentormind.capture.video.postprocess import bounds_from_cuts, postprocess
from mentormind.capture.video.probe import video_id_for
from mentormind.capture.video.segmenters import FixedWindowSegmenter
from mentormind.processing.vlm.sweep import windows as spec04


def test_video_id_matches_spec_04(tmp_path: Path) -> None:
    f = tmp_path / "a.mp4"
    f.write_bytes(b"some video bytes" * 1000)
    assert video_id_for(f) == spec04.video_id_for(f)


@pytest.mark.parametrize("duration", [8.0, 10.0, 22.0, 23.0, 35.0, 61.5, 193.793])
def test_fixed_window_bounds_match_spec_04(duration: float) -> None:
    ours = postprocess(bounds_from_cuts(FixedWindowSegmenter(10.0).cuts(Path("x"), duration), duration), duration)
    theirs = [(round(s, 3), round(e, 3)) for s, e in spec04.window_bounds(duration, 10.0)]
    assert ours == theirs
