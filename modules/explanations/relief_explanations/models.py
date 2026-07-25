from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ExplanationV1(BaseModel):
    """A consumer-facing explanation of a model output (Section 67). Never
    invents numbers — every supporting point traces back to a field already
    computed by the module being explained (reason_factors, resilience
    components, ranking_reason); this layer only composes and phrases them.
    """

    model_config = ConfigDict(extra="forbid")

    headline: str
    summary: str
    supporting_points: list[str]
    disclosure: str
    confidence: float = Field(ge=0, le=1)
    generated_by: str  # "template" today; "langchain" once Section 63 ships
