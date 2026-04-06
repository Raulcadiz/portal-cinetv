"""
Integration tests — full admin-to-device flows.

Covers:
  - Playlist sync lifecycle (upload → sync → delete → sync)
  - EPG + clear lifecycle
  - Full 7-step E2E scenario
  - Multi-device isolation
  - Re-authentication after token expiry (simulated via fresh client)
"""
import io

import pytest
from httpx import AsyncClient

MAC = "AA:BB:CC:DD:EE:FF"
VALID_M3U = b"#EXTM3U\n#EXTINF:-1,Test Channel\nhttp://example.com/live.m3u8\n"
VALID_XMLTV = b'<?xml version="1.0"?><tv generator-info-name="test"></tv>'


@pytest.mark.asyncio
async def test_full_playlist_sync_flow(auth_client: AsyncClient, client: AsyncClient):
    """
    Admin uploads a playlist → device syncs → playlist appears in sync response
    → admin deletes it → device syncs → action=none.
    """
    # 1. Upload file playlist
    upload = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "Integration Test"},
        files={"file": ("test.m3u", io.BytesIO(VALID_M3U), "text/plain")},
    )
    assert upload.status_code == 201
    playlist_id = upload.json()["id"]

    # 2. Device syncs — should see the playlist
    sync1 = await client.get("/api/sync", params={"mac": MAC})
    assert sync1.status_code == 200
    body1 = sync1.json()
    assert body1["action"] == "update"
    assert any(p["name"] == "Integration Test" for p in body1["playlists"])

    # 3. Admin deletes playlist
    delete = await auth_client.delete(f"/api/portal/playlist/{playlist_id}")
    assert delete.status_code == 200

    # 4. Device syncs again — no data left
    sync2 = await client.get("/api/sync", params={"mac": MAC})
    assert sync2.json()["action"] == "none"


@pytest.mark.asyncio
async def test_full_epg_and_clear_flow(auth_client: AsyncClient, client: AsyncClient):
    """
    Admin saves EPG URL + playlist → device syncs → admin clears device
    → device syncs (action=clear) → device syncs again (action=none).
    """
    # 1. Add playlist and EPG
    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/list.m3u", "name": "Flow Test"},
    )
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )

    # 2. Verify sync shows both
    sync1 = await client.get("/api/sync", params={"mac": MAC})
    body1 = sync1.json()
    assert body1["action"] == "update"
    assert len(body1["playlists"]) == 1
    assert body1["epg"]["type"] == "url"

    # 3. Admin clears device
    clear = await auth_client.request("DELETE", "/api/portal/clear", json={"mac": MAC})
    assert clear.status_code == 200

    # 4. Device sync — action=clear
    sync2 = await client.get("/api/sync", params={"mac": MAC})
    assert sync2.json()["action"] == "clear"

    # 5. Confirm playlists and EPG were also removed server-side
    playlists = await auth_client.get("/api/portal/playlists", params={"mac": MAC})
    assert playlists.json() == []

    epg = await auth_client.get("/api/portal/epg", params={"mac": MAC})
    assert epg.json() is None

    # 6. Second sync — nothing left
    sync3 = await client.get("/api/sync", params={"mac": MAC})
    assert sync3.json()["action"] == "none"


@pytest.mark.asyncio
async def test_full_7_step_e2e_flow(auth_client: AsyncClient, client: AsyncClient):
    """
    Complete 7-step E2E scenario:
      1. Admin adds URL playlist for device
      2. Admin uploads a file playlist for same device
      3. Admin adds EPG URL
      4. Device syncs — sees both playlists + EPG
      5. Admin updates one playlist URL
      6. Device syncs — sees updated playlist URL
      7. Admin clears device → device syncs (clear) → syncs again (none)
    """
    MAC_E2E = "E2:E2:E2:E2:E2:E2"

    # Step 1: Admin adds URL playlist
    r1 = await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC_E2E, "url": "http://example.com/live.m3u", "name": "Live TV"},
    )
    assert r1.status_code in (200, 201)
    url_playlist_id = r1.json()["id"]

    # Step 2: Admin uploads file playlist
    file_content = b"#EXTM3U\n#EXTINF:-1,Movie 1\nhttp://example.com/movie1.mp4\n"
    r2 = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC_E2E, "name": "Movies"},
        files={"file": ("movies.m3u", io.BytesIO(file_content), "text/plain")},
    )
    assert r2.status_code in (200, 201)

    # Step 3: Admin adds EPG URL
    r3 = await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC_E2E, "url": "http://example.com/epg.xml"},
    )
    assert r3.status_code in (200, 201)

    # Step 4: Device syncs — should see both playlists + EPG
    sync1 = await client.get("/api/sync", params={"mac": MAC_E2E})
    body1 = sync1.json()
    assert body1["action"] == "update"
    assert len(body1["playlists"]) == 2
    assert body1["epg"]["url"] == "http://example.com/epg.xml"

    playlist_names = {p["name"] for p in body1["playlists"]}
    assert "Live TV" in playlist_names
    assert "Movies" in playlist_names

    # Step 5: Admin updates the URL playlist
    r5 = await auth_client.put(
        f"/api/portal/playlist/{url_playlist_id}",
        json={"url": "http://example.com/live_v2.m3u", "name": "Live TV v2"},
    )
    assert r5.status_code in (200, 201)

    # Step 6: Device syncs again — sees updated playlist
    sync2 = await client.get("/api/sync", params={"mac": MAC_E2E})
    body2 = sync2.json()
    assert body2["action"] == "update"
    updated_names = {p["name"] for p in body2["playlists"]}
    assert "Live TV v2" in updated_names

    # Step 7: Admin clears device
    r7 = await auth_client.request("DELETE", "/api/portal/clear", json={"mac": MAC_E2E})
    assert r7.status_code == 200

    sync3 = await client.get("/api/sync", params={"mac": MAC_E2E})
    assert sync3.json()["action"] == "clear"

    sync4 = await client.get("/api/sync", params={"mac": MAC_E2E})
    assert sync4.json()["action"] == "none"


@pytest.mark.asyncio
async def test_multi_device_isolation(auth_client: AsyncClient, client: AsyncClient):
    """Playlists and EPG are scoped per device MAC; no cross-device leakage."""
    MAC_A = "AA:AA:AA:AA:AA:AA"
    MAC_B = "BB:BB:BB:BB:BB:BB"

    await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC_A, "url": "http://example.com/a.m3u", "name": "Device A"},
    )
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC_A, "url": "http://example.com/epg_a.xml"},
    )

    sync_b = await client.get("/api/sync", params={"mac": MAC_B})
    assert sync_b.json()["action"] == "none"

    sync_a = await client.get("/api/sync", params={"mac": MAC_A})
    body_a = sync_a.json()
    assert body_a["action"] == "update"
    assert len(body_a["playlists"]) == 1
    assert body_a["epg"] is not None
