from datetime import UTC, datetime

from fastapi import APIRouter

from app.core.config import get_settings
from app.models.weather import IntegrationStatus

router = APIRouter(tags=["system"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "fluxsg-api",
        "checked_at": datetime.now(UTC).isoformat(),
    }


@router.get("/api/v1/integrations/lta", response_model=IntegrationStatus)
async def lta_status() -> IntegrationStatus:
    configured = bool(get_settings().lta_account_key)
    return IntegrationStatus(
        source="LTA DataMall",
        configured=configured,
        state="ready" if configured else "awaiting_credentials",
        next_step=(
            "Run the first metadata ingestion"
            if configured
            else "Add LTA_ACCOUNT_KEY to the local environment"
        ),
    )

