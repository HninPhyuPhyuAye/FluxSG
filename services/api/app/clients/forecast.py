from datetime import UTC, datetime

import httpx
from pydantic import ValidationError

from app.models.forecast import ForecastManifest


class ForecastSourceError(RuntimeError):
    """Raised when the published forecast manifest is unavailable or malformed."""


class ForecastClient:
    def __init__(self, url: str, timeout_seconds: float = 8.0) -> None:
        self.url = url
        self.timeout_seconds = timeout_seconds

    async def fetch(self) -> ForecastManifest:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.get(
                    self.url,
                    headers={"User-Agent": "FluxSG/0.6 forecast delivery"},
                )
                response.raise_for_status()
            manifest = ForecastManifest.model_validate(response.json())
        except (httpx.HTTPError, ValueError, ValidationError) as exc:
            raise ForecastSourceError("The forecast manifest is unavailable or invalid") from exc

        now = datetime.now(UTC)
        if manifest.expires_at <= now:
            checks = {**manifest.checks, "source_fresh": False}
            return manifest.model_copy(
                update={
                    "available": False,
                    "status": "withheld",
                    "reason": "Forecast withheld because the published source observation expired.",
                    "checks": checks,
                }
            )
        return manifest
