"""
Tests for the device sync endpoint — GET /api/sync
"""
import io

import pytest
from httpx import AsyncClient

MAC = "AA:BB:CC:DD:EE:FF"
VALID_M3U = b"#EXTM3U\n#EXTINF:-1,Channel 1\nhttp://example.com/stream1\n"
VALID_XMLTV = b'<?xml version="1.0"?><tv generator-info-name="test"></tv>'


@pytest.mark.asyncio
async def test_sync_no_data(client: AsyncClient):
    """Device with no playlists/EPG returns action=none."""
    response = await client.get("/api/sync", params={"mac": MAC})
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "none"


@pytest.mark.asyncio
async def test_sync_with_playlist(auth_client: AsyncClient, client: AsyncClient):
    """Device with a playlist returns action=update with playlists payload."""
    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/list.m3u", "name": "Test"},
    )
    response = await client.get("/api/sync", params={"mac": MAC})
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "update"
    assert len(body["playlists"]) == 1
    assert body["playlists"][0]["url"] == "http://example.com/list.m3u"


@pytest.mark.asyncio
async def test_sync_with_epg(auth_client: AsyncClient, client: AsyncClient):
    """Device with EPG returns action=update with epg payload."""
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )
    response = await client.get("/api/sync", params={"mac": MAC})
    assert response.status_code == 200
    body = response.json()
    assert body["action"] == "update"
    assert body["epg"]["type"] == "url"


@pytest.mark.asyncio
async def test_sync_clear_flag(auth_client: AsyncClient, client: AsyncClient):
    """After portal clears a device, sync returns action=clear."""
    # Add a playlist first
    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/list.m3u", "name": "Test"},
    )
    # Trigger clear
    await auth_client.request("DELETE", "/api/portal/clear", json={"mac": MAC})

    response = await client.get("/api/sync", params={"mac": MAC})
    assert response.status_code == 200
    assert response.json()["action"] == "clear"


@pytest.mark.asyncio
async def test_sync_clear_resets_after_acknowledged(
    auth_client: AsyncClient, client: AsyncClient
):
    """Second sync after clear returns action=none (flag was reset on first call)."""
    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/list.m3u", "name": "Test"},
    )
    await auth_client.request("DELETE", "/api/portal/clear", json={"mac": MAC})

    # First sync acknowledges clear
    first = await client.get("/api/sync", params={"mac": MAC})
    assert first.json()["action"] == "clear"

    # Second sync should show no pending data
    second = await client.get("/api/sync", params={"mac": MAC})
    assert second.json()["action"] == "none"


@pytest.mark.asyncio
async def test_sync_invalid_mac(client: AsyncClient):
    """Invalid MAC address returns 422."""
    response = await client.get("/api/sync", params={"mac": "not-a-mac"})
    assert response.status_code == 422
