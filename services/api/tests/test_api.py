import httpx
import pytest

from app.main import app


@pytest.mark.asyncio
async def test_health() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["service"] == "fluxsg-api"


@pytest.mark.asyncio
async def test_lta_is_safe_when_key_is_missing() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/integrations/lta")

    assert response.status_code == 200
    assert response.json() == {
        "source": "LTA DataMall",
        "configured": False,
        "state": "awaiting_credentials",
        "next_step": "Add LTA_ACCOUNT_KEY to the local environment",
    }


