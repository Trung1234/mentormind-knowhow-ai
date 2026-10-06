"""Standalone MediaPipe hand detector, run in its OWN process and Python environment.

Why a separate process: ``mediapipe`` 1.0.x aborts natively on macOS and 0.10.x pins ``numpy<2``,
which the rest of the project cannot use (docs/plans/03-spike-notes.md). Here a crash only kills
this process, and the caller falls back to scene cuts.

This file imports nothing from ``mentormind``: the worker environment has only ``mediapipe`` (and
the OpenCV it brings). It prints ONE JSON object on stdout and nothing else:

    {"sample_fps": 5.0, "duration_s": 12.3,
     "wrists": [[[x, y], ...], ...]}      # one entry per sampled frame: wrist positions in 0..1

Run: ``python hand_worker.py <video> [--fps 5]``.
"""

from __future__ import annotations

import argparse
import json
import sys

FRAME_WIDTH = 480  # detection runs on a downscaled frame: hands are large in a station camera view


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("video")
    parser.add_argument("--fps", type=float, default=5.0)
    args = parser.parse_args(argv)

    import cv2
    import mediapipe as mp

    capture = cv2.VideoCapture(args.video)
    if not capture.isOpened():
        print(f"không mở được {args.video}", file=sys.stderr)
        return 2
    source_fps = capture.get(cv2.CAP_PROP_FPS) or 25.0
    step = max(1, round(source_fps / args.fps))
    hands = mp.solutions.hands.Hands(static_image_mode=False, max_num_hands=2, model_complexity=0)
    wrists: list[list[list[float]]] = []
    index = 0
    while True:
        if not capture.grab():
            break
        if index % step == 0:
            ok, frame = capture.retrieve()
            if not ok:
                break
            height = max(1, round(frame.shape[0] * FRAME_WIDTH / frame.shape[1]))
            small = cv2.resize(frame, (FRAME_WIDTH, height))
            found = hands.process(cv2.cvtColor(small, cv2.COLOR_BGR2RGB))
            wrists.append(
                [[round(h.landmark[0].x, 4), round(h.landmark[0].y, 4)] for h in found.multi_hand_landmarks or []]
            )
        index += 1
    capture.release()
    print(json.dumps({"sample_fps": source_fps / step, "duration_s": index / source_fps, "wrists": wrists}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
