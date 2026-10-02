"""What the hybrid retriever of spec 05 hands to the agents of spec 06 (spec 05 §4).

``passages[i]`` is backed by ``citations[i]`` (one-to-one, same order) and labelled by
``passage_classifications[i]``. The label is what lets an agent drop ``factory_confidential``
passages before a cloud LLM sees them (spec 06 §2, constitution art. 2); a passage without a label
is treated as confidential (fail closed).
"""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator

from mentormind.core.schemas.common import Citation, DataClassification


class RetrievedContext(BaseModel):
    query: str
    process_id: str | None
    #: Text put into the prompt; ``passages[i]`` is cited by ``citations[i]``.
    passages: list[str] = Field(default_factory=list)
    #: Sentences such as "Bước X dùng linh kiện Y" from the graph.
    graph_facts: list[str] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    #: Label of each passage; empty = unknown = every passage treated as factory_confidential.
    passage_classifications: list[DataClassification] = Field(default_factory=list)

    @model_validator(mode="after")
    def _aligned(self) -> RetrievedContext:
        if len(self.citations) != len(self.passages):
            raise ValueError("Mỗi passage phải có đúng một citation cùng vị trí (spec 05 AC-06).")
        if self.passage_classifications and len(self.passage_classifications) != len(self.passages):
            raise ValueError("passage_classifications phải dài bằng passages.")
        return self

    def label_of(self, index: int) -> DataClassification:
        if not self.passage_classifications:
            return DataClassification.FACTORY_CONFIDENTIAL
        return self.passage_classifications[index]
