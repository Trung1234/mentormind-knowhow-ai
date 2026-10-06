"""spec 03 FR-05, FR-06, AC-01 — three keyframes and one clip per segment."""

from __future__ import annotations

from pathlib import Path

import cv2
import pytest

from mentormind.capture.video.media import MediaError, export_clip, export_keyframes, keyframe_times
from tests.capture.video.conftest import MakeVideo, needs_ffmpeg


class RecordingRunner:
    """Pretends to be ffmpeg: records the command and creates the output file."""

    def __init__(self, fail: bool = False) -> None:
        self.commands: list[list[str]] = []
        self.fail = fail

    def __call__(self, command: list[str]) -> None:
        self.commands.append(command)
        if self.fail:
            raise MediaError("boom")
        Path(command[-1]).write_bytes(b"data")


def test_keyframe_times_are_start_middle_end_inside_the_segment() -> None:
    assert keyframe_times(10.0, 20.0) == pytest.approx([10.1, 15.0, 19.9])


def test_keyframe_times_stay_inside_a_very_short_segment() -> None:
    times = keyframe_times(5.0, 5.2)
    assert all(5.0 <= t <= 5.2 for t in times) and times == sorted(times)


def test_keyframes_are_three_jpgs_named_after_the_segment(tmp_path: Path) -> None:
    runner = RecordingRunner()
    paths = export_keyframes(Path("v.mp4"), 10.0, 20.0, "VID-aaaaaaaaaaaa-S001", tmp_path, runner=runner)
    assert [p.name for p in paths] == [f"VID-aaaaaaaaaaaa-S001-{i}.jpg" for i in range(3)]
    assert all(p.is_file() for p in paths) and len(runner.commands) == 3
    assert not list(tmp_path.glob("*.part*"))  # no half-written file left behind


def test_existing_outputs_are_reused_unless_forced(tmp_path: Path) -> None:
    runner = RecordingRunner()
    export_keyframes(Path("v.mp4"), 0.0, 10.0, "S", tmp_path, runner=runner)
    export_keyframes(Path("v.mp4"), 0.0, 10.0, "S", tmp_path, runner=runner)
    assert len(runner.commands) == 3
    export_keyframes(Path("v.mp4"), 0.0, 10.0, "S", tmp_path, runner=runner, force=True)
    assert len(runner.commands) == 6


def test_clip_has_no_audio_and_is_reencoded(tmp_path: Path) -> None:
    runner = RecordingRunner()
    clip = export_clip(Path("v.mp4"), 3.0, 9.0, "S", tmp_path, runner=runner)
    command = runner.commands[0]
    assert clip.name == "S.mp4" and "-an" in command and "libx264" in command and "copy" not in command


def test_copy_option_uses_stream_copy(tmp_path: Path) -> None:
    runner = RecordingRunner()
    export_clip(Path("v.mp4"), 3.0, 9.0, "S", tmp_path, runner=runner, copy=True)
    assert "copy" in runner.commands[0] and "libx264" not in runner.commands[0]


def test_failed_export_names_the_segment_and_leaves_no_file(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="S001"):
        export_clip(Path("v.mp4"), 0.0, 5.0, "S001", tmp_path, runner=RecordingRunner(fail=True))
    assert not list(tmp_path.iterdir())


def test_missing_ffmpeg_says_what_to_install(tmp_path: Path) -> None:
    with pytest.raises(MediaError, match="ffmpeg"):
        export_clip(Path("v.mp4"), 0.0, 5.0, "S", tmp_path, ffmpeg="no-such-ffmpeg-binary")


@needs_ffmpeg
def test_ac_01_real_ffmpeg_writes_valid_keyframes_and_clip(make_video: MakeVideo, tmp_path: Path) -> None:
    video = make_video()
    frames = export_keyframes(video, 4.0, 8.0, "S", tmp_path / "kf")
    assert all(cv2.imread(str(p)) is not None for p in frames)
    clip = export_clip(video, 4.0, 8.0, "S", tmp_path / "clips")
    capture = cv2.VideoCapture(str(clip))
    count, fps = capture.get(cv2.CAP_PROP_FRAME_COUNT), capture.get(cv2.CAP_PROP_FPS)
    capture.release()
    assert count / fps == pytest.approx(4.0, abs=0.3)  # re-encode cuts where asked, unlike -c copy
