"""bge-m3 dense embedder (spec 02 FR-07): text -> unit vector of 1024 floats.

Runs on this machine (constitution art. 2: factory-confidential text must never leave it). The
model (~2.2 GB) downloads from Hugging Face on first use; ``torch``/``transformers`` come with
the ``ingest`` extra and are imported only then, so everything else works without them.
"""

from __future__ import annotations

import importlib
import math
from collections.abc import Callable, Sequence

from mentormind.knowledge_base.store.vector_store import VectorStoreError

#: Texts in -> raw (unnormalised) CLS vectors out. The only part that touches torch.
Forward = Callable[[list[str]], list[list[float]]]

DEFAULT_MODEL = "BAAI/bge-m3"
DEFAULT_DIM = 1024
# Chunks are at most 800 bge-m3 tokens (spec 02 FR-04); the model itself accepts up to 8192.
_MAX_LENGTH = 1024


class BgeM3Embedder:
    """Implements ``Embedder``. The model loads on the first non-empty ``embed`` call."""

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        *,
        dim: int = DEFAULT_DIM,
        batch_size: int = 16,
        forward: Forward | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError(f"batch_size phải >= 1, nhận {batch_size}.")
        self._model_name = model_name
        self._dim = dim
        self._batch_size = batch_size
        self._forward = forward

    @property
    def dim(self) -> int:
        return self._dim

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed ``texts`` in order, ``batch_size`` at a time.

        Raises:
            VectorStoreError: ``torch``/``transformers`` are missing or the model's dimension is not ``dim``.
        """
        items = list(texts)
        if not items:
            return []
        if self._forward is None:
            self._forward = _load_forward(self._model_name)
        out: list[list[float]] = []
        for start in range(0, len(items), self._batch_size):
            for vector in self._forward(items[start : start + self._batch_size]):
                if len(vector) != self._dim:
                    raise VectorStoreError(
                        f"Model {self._model_name} sinh vector {len(vector)} chiều, store cần {self._dim}."
                    )
                out.append(_normalise(vector))
        return out


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    return [v / norm for v in vector] if norm else vector


def _load_forward(model_name: str) -> Forward:
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
    except ImportError as exc:
        raise VectorStoreError("Thiếu torch/transformers: cài extra `ingest` (uv sync --extra ingest).") from exc
    tokenizer = transformers.AutoTokenizer.from_pretrained(model_name)
    model = transformers.AutoModel.from_pretrained(model_name).eval()

    def forward(texts: list[str]) -> list[list[float]]:
        batch = tokenizer(texts, padding=True, truncation=True, max_length=_MAX_LENGTH, return_tensors="pt")
        with torch.no_grad():
            hidden = model(**batch).last_hidden_state
        return [[float(x) for x in row] for row in hidden[:, 0].tolist()]  # bge-m3 dense = the [CLS] vector

    return forward
