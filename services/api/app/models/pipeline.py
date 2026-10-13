from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PipelineRun(BaseModel):
    model_config = ConfigDict(frozen=True)

    run_id: UUID
    dataset: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    received_records: int = Field(ge=0)
    valid_records: int = Field(ge=0)
    rejected_records: int = Field(ge=0)
    object_key: str | None


class PipelineStatus(BaseModel):
    model_config = ConfigDict(frozen=True)

    configured: bool
    state: str
    latest_runs: list[PipelineRun]
