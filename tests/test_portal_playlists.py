"""
Tests for playlist management endpoints.
  GET    /api/portal/playlists
  POST   /api/portal/upload
  POST   /api/portal/url
  DELETE /api/portal/playlist/{id}
"""
import io

import pytest
from httpx import AsyncClient

MAC = "AA:BB:CC:DD:EE:FF"
VALID_M3U = b"#EXTM3U\n#EXTINF:-1,Channel 1\nhttp://example.com/stream1\n"


@pytest.mark.asyncio
async def test_get_playlists_empty(auth_client: AsyncClient):
    """No playlists returns an empty list."""
    response = await auth_client.get("/api/portal/playlists", params={"mac": MAC})
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_upload_playlist_file(auth_client: AsyncClient):
    """Upload a valid .m3u file — returns 201 with id and type=file."""
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "My List"},
        files={"file": ("channels.m3u", io.BytesIO(VALID_M3U), "text/plain")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "file"
    assert body["name"] == "My List"
    assert "id" in body


@pytest.mark.asyncio
async def test_upload_playlist_file_invalid_content(auth_client: AsyncClient):
    """File without #EXTM3U header returns 400."""
    bad_content = b"not a playlist"
    response = await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC},
        files={"file": ("bad.m3u", io.BytesIO(bad_content), "text/plain")},
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_save_playlist_url(auth_client: AsyncClient):
    """Save a playlist URL — returns 201 with type=url."""
    response = await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/list.m3u", "name": "URL List"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["type"] == "url"
    assert body["name"] == "URL List"


@pytest.mark.asyncio
async def test_save_playlist_url_invalid(auth_client: AsyncClient):
    """Non-HTTP URL returns 422."""
    response = await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "ftp://example.com/list.m3u"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_playlists_after_upload(auth_client: AsyncClient):
    """Playlists endpoint returns previously uploaded entries."""
    await auth_client.post(
        "/api/portal/upload",
        data={"mac": MAC, "name": "List A"},
        files={"file": ("a.m3u", io.BytesIO(VALID_M3U), "text/plain")},
    )
    response = await auth_client.get("/api/portal/playlists", params={"mac": MAC})
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "List A"


@pytest.mark.asyncio
async def test_delete_playlist(auth_client: AsyncClient):
    """Delete a playlist by id removes it from the list."""
    create = await auth_client.post(
        "/api/portal/url",
        json={"mac": MAC, "url": "http://example.com/l.m3u", "name": "To Delete"},
    )
    playlist_id = create.json()["id"]

    delete = await auth_client.delete(f"/api/portal/playlist/{playlist_id}")
    assert delete.status_code == 200

    remaining = await auth_client.get("/api/portal/playlists", params={"mac": MAC})
    assert remaining.json() == []


@pytest.mark.asyncio
async def test_delete_nonexistent_playlist(auth_client: AsyncClient):
    """Deleting a playlist that doesn't exist returns 404."""
    response = await auth_client.delete("/api/portal/playlist/99999")
    assert response.status_code == 404
