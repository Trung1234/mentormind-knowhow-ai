"""The expert's words for each step (spec 04 §3), the input of propose-reasons (§5).

Spec 03 (Hoàng) produces them: ``transcript.json`` (``loader``) and ``align_transcript`` (FR-08,
used by ``excerpt.align``). Spec 04 only joins the aligned lines of a step's segments
(``excerpt.excerpt_for``). Anything missing means no excerpt, as before spec 03.
"""

from mentormind.processing.vlm.transcript.excerpt import SPEC03_MODULE, Aligned, align, excerpt_for, lines_for
from mentormind.processing.vlm.transcript.loader import load_transcript, transcript_path

__all__ = ["SPEC03_MODULE", "Aligned", "align", "excerpt_for", "lines_for", "load_transcript", "transcript_path"]
