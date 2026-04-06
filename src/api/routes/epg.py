"""
Portal routes for managing EPG (Electronic Programme Guide) sources per device.
Only one EPG source per device at a time (upsert semantics).
All endpoints require JWT authentication.
"""
import gzip

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.middlewares.auth import get_current_admin
from src.api.models.admin_user import AdminUser
from src.api.schemas.epg import EpgDeleteRequest, EpgInfo, EpgUrlRequest
from src.api.services import epg_service
from src.api.utils.validators import validate_mac
from src.core.config import settings
from src.core.database import get_db

router = APIRouter()

_XMLTV_MARKER = b"<tv"
_MAC_PATTERN = r"^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$"
_XMLTV_CHECK_BYTES = 200


# ── Upload file ───────────────────────────────────────────────────────────────

@router.post(
    "/upload",
    status_code=201,
    response_model=EpgInfo,
    summary="Upload an XMLTV EPG file for a device",
)
async def upload_epg(
    mac: str = Form(..., description="Device MAC address XX:XX:XX:XX:XX:XX"),
    file: UploadFile = File(..., description="XMLTV file (.xml or .gz)"),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> EpgInfo:
    """
    Validates that the file is a valid XMLTV document and upserts the EPG for *mac*.

    Accepts both uncompressed ``.xml`` and gzip-compressed ``.gz`` files.
    Checks for the ``<tv`` marker in the first 200 bytes (after decompression).
    """
    try:
        mac = validate_mac(mac)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    raw = await file.read(settings.max_xmltv_size_bytes + 1)
    if len(raw) > settings.max_xmltv_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File exceeds maximum allowed size of {settings.max_xmltv_size_mb} MB.",
        )

    # Decompress if gzip to validate header
    check_bytes = raw
    filename = file.filename or ""
    if filename.endswith(".gz"):
        try:
            check_bytes = gzip.decompress(raw)
        except Exception:
            raise HTTPException(status_code=400, detail="Could not decompress gzip file.")

    if _XMLTV_MARKER not in check_bytes[:_XMLTV_CHECK_BYTES].lower():
        raise HTTPException(
            status_code=400,
            detail="Invalid XMLTV file: <tv element not found in first 200 bytes.",
        )

    content = raw.decode("utf-8", errors="replace") if not filename.endswith(".gz") else check_bytes.decode("utf-8", errors="replace")
    epg = await epg_service.upsert_epg(db, mac=mac, epg_type="file", content=content)
    return EpgInfo(id=epg.id, mac=mac, type="file")


# ── Save URL ──────────────────────────────────────────────────────────────────

@router.post(
    "/url",
    status_code=201,
    response_model=EpgInfo,
    summary="Save a remote XMLTV EPG URL for a device",
)
async def save_epg_url(
    body: EpgUrlRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> EpgInfo:
    """Upserts (creates or replaces) the EPG URL for the given MAC."""
    epg = await epg_service.upsert_epg(db, mac=body.mac, epg_type="url", content=body.url)
    return EpgInfo(id=epg.id, mac=body.mac, type="url")


# ── Get EPG ───────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=EpgInfo | None,
    summary="Get EPG source for a device",
)
async def get_epg(
    mac: str = Query(..., pattern=_MAC_PATTERN),
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> EpgInfo | None:
    """Returns the current EPG source for *mac*, or ``null`` if none configured."""
    epg = await epg_service.get_epg(db, mac.upper())
    if epg is None:
        return None
    return EpgInfo.model_validate(epg)


# ── Delete EPG ────────────────────────────────────────────────────────────────

@router.delete(
    "",
    summary="Delete EPG source for a device",
)
async def delete_epg(
    body: EpgDeleteRequest,
    db: AsyncSession = Depends(get_db),
    _admin: AdminUser = Depends(get_current_admin),
) -> dict:
    """Deletes the EPG source for *mac*. Idempotent: 200 even if no EPG existed."""
    await epg_service.delete_epg(db, body.mac)
    return {"deleted": True}
