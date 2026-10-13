from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.models.weather import IntegrationStatus

router = APIRouter(tags=["system"])

SettingsDependency = Annotated[Settings, Depends(get_settings)]


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "fluxsg-api",
        "checked_at": datetime.now(UTC).isoformat(),
    }


@router.get("/api/v1/integrations/lta", response_model=IntegrationStatus)
async def lta_status(settings: SettingsDependency) -> IntegrationStatus:
    configured = bool(settings.lta_account_key)
    return IntegrationStatus(
        source="LTA DataMall",
        configured=configured,
        state="ready" if configured else "awaiting_credentials",
        next_step=(
            "Search stops or request a live arrival board"
            if configured
            else "Add LTA_ACCOUNT_KEY to the local environment"
        ),
    )

