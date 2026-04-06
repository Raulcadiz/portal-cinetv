"""
Tests for EPG management endpoints.
  GET    /api/portal/epg
  POST   /api/portal/epg/upload
  POST   /api/portal/epg/url
  DELETE /api/portal/epg
"""
import gzip
import io

import pytest
from httpx import AsyncClient

MAC = "AA:BB:CC:DD:EE:FF"
VALID_XMLTV = b'<?xml version="1.0"?><tv generator-info-name="test"></tv>'
VALID_XMLTV_GZ = gzip.compress(VALID_XMLTV)


@pytest.mark.asyncio
async def test_get_epg_none(auth_client: AsyncClient):
    """No EPG configured returns null."""
    response = await auth_client.get("/api/portal/epg", params={"mac": MAC})
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_save_epg_url(auth_client: AsyncClient):
    """Save EPG URL — returns 200 with type=url."""
    response = await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "url"
    assert "example.com" in body["content"]


@pytest.mark.asyncio
async def test_get_epg_after_save(auth_client: AsyncClient):
    """EPG endpoint reflects the saved URL."""
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )
    response = await auth_client.get("/api/portal/epg", params={"mac": MAC})
    assert response.status_code == 200
    body = response.json()
    assert body is not None
    assert body["type"] == "url"


@pytest.mark.asyncio
async def test_upload_epg_file(auth_client: AsyncClient):
    """Upload a valid XMLTV file — returns 200 with type=file."""
    response = await auth_client.post(
        "/api/portal/epg/upload",
        data={"mac": MAC},
        files={"file": ("epg.xml", io.BytesIO(VALID_XMLTV), "application/xml")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["type"] == "file"


@pytest.mark.asyncio
async def test_upload_epg_gzip(auth_client: AsyncClient):
    """Upload a gzipped XMLTV file is accepted."""
    response = await auth_client.post(
        "/api/portal/epg/upload",
        data={"mac": MAC},
        files={"file": ("epg.xml.gz", io.BytesIO(VALID_XMLTV_GZ), "application/gzip")},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_delete_epg(auth_client: AsyncClient):
    """Delete EPG — subsequent GET returns null."""
    await auth_client.post(
        "/api/portal/epg/url",
        json={"mac": MAC, "url": "http://example.com/epg.xml"},
    )
    delete = await auth_client.request(
        "DELETE", "/api/portal/epg", json={"mac": MAC}
    )
    assert delete.status_code == 200

    response = await auth_client.get("/api/portal/epg", params={"mac": MAC})
    assert response.json() is None
