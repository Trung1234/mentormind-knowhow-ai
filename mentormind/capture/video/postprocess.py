"""Clean up raw cut points into 3–20 s pieces (spec 03 FR-04, AC-02, AC-03).

Pieces always touch (the end of one is the start of the next) and together cover the video, so
coverage (AC-03) holds by construction.
"""

from __future__ import annotations

import math

Bounds = list[tuple[float, float]]

MIN_SEGMENT_S = 3.0
MAX_SEGMENT_S = 20.0
SPLIT_TARGET_S = 15.0
_PRECISION = 3


def bounds_from_cuts(cuts: list[float], duration: float) -> Bounds:
    """Turn interior cut times into contiguous ``(start, end)`` pieces covering ``[0, duration]``."""
    inside = sorted({round(c, _PRECISION) for c in cuts if 0 < c < duration})
    points = [0.0, *inside, round(duration, _PRECISION)]
    return list(zip(points, points[1:], strict=False))


def postprocess(bounds: Bounds, duration: float) -> Bounds:
    """Merge pieces shorter than 3 s, then split pieces longer than 20 s into parts of at most 15 s.

    A piece under 3 s joins the previous one (the first joins the next). A video shorter than 3 s
    cannot be fixed and stays one piece. Splitting runs last, so it never creates a short piece
    (a piece above 20 s yields parts of at least 10 s).
    """
    merged = [list(b) for b in bounds]
    while len(merged) > 1:
        short = next((i for i, (s, e) in enumerate(merged) if e - s < MIN_SEGMENT_S), None)
        if short is None:
            break
        if short > 0:
            merged[short - 1][1] = merged[short][1]
        else:
            merged[1][0] = merged[0][0]
        del merged[short]
    out: Bounds = []
    for start, end in merged:
        parts = math.ceil((end - start) / SPLIT_TARGET_S) if end - start > MAX_SEGMENT_S else 1
        edges = [round(start + (end - start) * i / parts, _PRECISION) for i in range(parts)] + [end]
        out.extend(zip(edges, edges[1:], strict=False))
    if out:
        out[-1] = (out[-1][0], round(duration, _PRECISION))
    return out
