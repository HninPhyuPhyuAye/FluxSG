from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.config import Settings, get_settings
from app.models.pipeline import PipelineRun, PipelineStatus
from app.pipelines.snapshot import PostgresIngestionLedger

router = APIRouter(prefix="/api/v1/pipeline", tags=["pipeline"])
SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/status", response_model=PipelineStatus)
async def pipeline_status(
    settings: SettingsDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PipelineStatus:
    if not settings.database_url:
        return PipelineStatus(configured=False, state="not_configured", latest_runs=[])
    try:
        rows = await PostgresIngestionLedger(settings.database_url).latest(limit)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The ingestion ledger is temporarily unavailable",
        ) from exc
    return PipelineStatus(
        configured=True,
        state="ready",
        latest_runs=[PipelineRun.model_validate(row) for row in rows],
    )
