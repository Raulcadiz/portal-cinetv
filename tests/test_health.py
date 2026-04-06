"""Basic smoke test — verifies the app starts and the health endpoint responds."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health(client: AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_sync_no_data(client: AsyncClient) -> None:
    """Sync with unknown device_id returns action=none (no data in DB)."""
    response = await client.get("/api/sync", params={"device_id": "test-device-uuid"})
    assert response.status_code == 200
    assert response.json()["action"] == "none"
