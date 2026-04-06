"""
Edge-case tests — sync, upload, and EPG boundary conditions.
"""
import io

import pytest
from httpx import AsyncClient

MAC = "AA:BB:CC:DD:EE:FF"
MAC2 = "11:22:33:44:55:66"

VALID_M3U = b"#EXTM3U\n#EXTINF:-1,Channel 1\nhttp://example.com/stream.m3u8\n"
EMPTY_M3U = b"#EXTM3U\n"
INVALID_M3U = b"This is not an M3U file at all"


# ── Sync edge cases ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_sync_missing_mac(client: AsyncClient):
    """Sync without mac param returns 422."""
    response = await client.get("/api/sync")
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_sync_different_devices_isolated(
    auth_client: AsyncClient, client: AsyncClient
):
    """Playlist added for MAC1 must not appear in sync for MAC2."""
    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/mac1.m3u", "name": "MAC1 list"},
    )

    sync_mac2 = await client.get("/api/sync", params={"mac": MAC2})
    assert sync_mac2.json()["action"] == "none"


@pytest.mark.asyncio
async def test_sync_multiple_playlists(auth_client: AsyncClient, client: AsyncClient):
    """Device with multiple playlists receives all of them in one sync response."""
    for i in range(3):
        await auth_client.post(
            "/api/portal/url",
            json={"mac": MAC, "url": f"http://example.com/list{i}.m3u", "name": f"List {i}"},
        )

    sync = await client.get("/api/sync", params={"mac": MAC})
    body = sync.json()
    assert body["action"] == "update"
    assert len(body["playlists"]) == 3


# ── Upload edge cases ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_empty_m3u(auth_client: AsyncClient):
    """Uploading an M3U with only the header (no entries) should succeed (empty playlist)."""
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "Empty"},
        files={"file": ("empty.m3u", io.BytesIO(EMPTY_M3U), "text/plain")},
    )
    # Accepted even if empty — the app will show an empty list
    assert response.status_code in (200, 201)


@pytest.mark.asyncio
async def test_upload_invalid_content_type(auth_client: AsyncClient):
    """Uploading a binary file (not M3U) returns 400 or 422."""
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "Bad"},
        files={"file": ("bad.exe", io.BytesIO(b"\x00\x01\x02\x03"), "application/octet-stream")},
    )
    assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_upload_missing_mac(auth_client: AsyncClient):
    """Upload without mac field returns 422."""
    response = await auth_client.post(
        "/api/portal/upload",
        data={"name": "No MAC"},
        files={"file": ("test.m3u", io.BytesIO(VALID_M3U), "text/plain")},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_missing_file(auth_client: AsyncClient):
    """Upload without a file returns 422."""
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "No File"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_upload_unauthenticated(client: AsyncClient):
    """Upload without auth token returns 401."""
    response = await client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "Unauth"},
        files={"file": ("test.m3u", io.BytesIO(VALID_M3U), "text/plain")},
    )
    assert response.status_code == 401


# ── EPG edge cases ────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_epg_url_overrides_previous(auth_client: AsyncClient, client: AsyncClient):
    """Setting a new EPG URL replaces the old one; only the latest is synced."""
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg_old.xml"},
    )
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg_new.xml"},
    )

    sync = await client.get("/api/sync", params={"mac": MAC})
    epg = sync.json()["epg"]
    assert epg["url"] == "http://example.com/epg_new.xml"


@pytest.mark.asyncio
async def test_epg_missing_mac(auth_client: AsyncClient):
    """Adding EPG URL without mac returns 422."""
    response = await auth_client.post(
        "/api/portal/epg/url",
        json={"url": "http://example.com/epg.xml"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_epg_invalid_url_scheme(auth_client: AsyncClient):
    """Adding EPG URL with an invalid scheme (ftp://) returns 422."""
    response = await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "ftp://example.com/epg.xml"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_epg_unauthenticated(client: AsyncClient):
    """Setting EPG URL without auth returns 401."""
    response = await client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )
    assert response.status_code == 401


# ── URL playlist edge cases ───────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_add_url_playlist_invalid_mac(auth_client: AsyncClient):
    """Adding a URL playlist with a bad MAC format returns 422."""
    response = await auth_client.post(
        "/api/portal/url",
        json={"mac": "not-valid", "url": "http://example.com/list.m3u", "name": "Bad MAC"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_url_playlist_invalid_url(auth_client: AsyncClient):
    """Adding a URL playlist with a non-HTTP URL returns 422."""
    response = await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "javascript:alert(1)", "name": "XSS"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_nonexistent_playlist(auth_client: AsyncClient):
    """Deleting a playlist that does not exist returns 404."""
    response = await auth_client.delete("/api/portal/playlist/99999")
    assert response.status_code == 404


# ── Idempotency tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_clear_device_with_no_playlists_is_idempotent(
    auth_client: AsyncClient, client: AsyncClient
):
    """Clearing a MAC that has no playlists/EPG still returns 200."""
    response = await auth_client.request(
        "DELETE", "/api/portal/clear", json={"mac": "FF:FF:FF:FF:FF:00"}
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_double_epg_url_upserts_single_record(
    auth_client: AsyncClient, client: AsyncClient
):
    """Two POST /epg/url for the same MAC results in only one EPG record (upsert)."""
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg_v1.xml"},
    )
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg_v2.xml"},
    )

    sync = await client.get("/api/sync", params={"mac": MAC})
    body = sync.json()
    # Only one EPG entry — the latest URL
    assert body["epg"]["url"] == "http://example.com/epg_v2.xml"


# ── Load test ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_upload_large_m3u_responds_within_timeout(auth_client: AsyncClient):
    """Uploading a ~10 MB M3U file should complete in under 10 seconds."""
    import time

    # Generate a large M3U: header + 50 000 channel entries
    lines = ["#EXTM3U"]
    for i in range(50_000):
        lines.append(f"#EXTINF:-1,Channel {i}\nhttp://example.com/stream{i}.m3u8")
    large_m3u = "\n".join(lines).encode()

    start = time.monotonic()
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "Large List"},
        files={"file": ("large.m3u", large_m3u, "text/plain")},
    )
    elapsed = time.monotonic() - start

    assert response.status_code in (200, 201)
    assert elapsed < 10.0, f"Upload took {elapsed:.1f}s — too slow"
