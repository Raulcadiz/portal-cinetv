# API Contracts

IPTVSur Portal exposes two groups of endpoints:

- **Admin API** (`/api/admin/`, `/api/portal/`) — authenticated with JWT Bearer token
- **Device Sync API** (`/api/sync`) — unauthenticated, called by the Android app

Base URL: `http://<host>:8000`

---

## Authentication

### POST /api/admin/login

Obtain a JWT access token.

**Request body**
```json
{ "username": "admin", "password": "secret" }
```

**Response 200**
```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

**Error responses**
| Status | Meaning |
|--------|---------|
| 401 | Invalid credentials |
| 422 | Missing / malformed body |

All subsequent Admin API calls require:
```
Authorization: Bearer <access_token>
```

---

## Admin — Playlist management

### GET /api/portal/playlists?mac=\<mac\>

List all playlists assigned to a device.

**Query params**
| Param | Type | Required | Description |
|-------|------|----------|-------------|
| mac | string | yes | Device MAC address (format `XX:XX:XX:XX:XX:XX`) |

**Response 200**
```json
[
  {
    "id": 1,
    "name": "Live TV",
    "source_type": "url",
    "url": "http://example.com/live.m3u",
    "mac": "AA:BB:CC:DD:EE:FF"
  }
]
```

---

### POST /api/portal/url

Add a URL-based playlist to a device.

**Request body**
```json
{
  "mac": "AA:BB:CC:DD:EE:FF",
  "url": "http://example.com/list.m3u",
  "name": "My Playlist"
}
```

**Response 201**
```json
{ "id": 1, "name": "My Playlist", "source_type": "url", "url": "http://example.com/list.m3u" }
```

**Validation**
- `mac` must match `^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$`
- `url` must be HTTP or HTTPS

---

### POST /api/portal/upload

Upload an M3U file playlist to a device.

**Request** — multipart/form-data
| Field | Type | Description |
|-------|------|-------------|
| mac | string | Device MAC |
| name | string | Playlist display name |
| file | file | `.m3u` / `.m3u8` file (text/plain or text/x-mpegurl) |

**Response 201**
```json
{ "id": 2, "name": "Uploaded List", "source_type": "file" }
```

**Errors**
| Status | Meaning |
|--------|---------|
| 400 | File content is not a valid M3U |
| 422 | Missing required field |

---

### PUT /api/portal/playlist/\<id\>

Update the URL or name of an existing playlist.

**Path param** — `id`: playlist database ID

**Request body** (all fields optional)
```json
{ "url": "http://example.com/new.m3u", "name": "New Name" }
```

**Response 200** — updated playlist object

**Errors** — 404 if playlist not found

---

### DELETE /api/portal/playlist/\<id\>

Delete a playlist by ID.

**Response 200** — `{ "ok": true }`

**Errors** — 404 if not found

---

## Admin — EPG management

### GET /api/portal/epg?mac=\<mac\>

Get the EPG configuration assigned to a device.

**Response 200** — EPG object or `null`
```json
{
  "id": 1,
  "type": "url",
  "url": "http://example.com/epg.xml",
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

---

### POST /api/portal/epg/url

Set (or replace) an EPG URL for a device.

**Request body**
```json
{ "mac": "AA:BB:CC:DD:EE:FF", "url": "http://example.com/epg.xml" }
```

**Response 200/201** — EPG object

**Validation** — `url` must be HTTP/HTTPS

---

### POST /api/portal/epg/upload

Upload an XMLTV EPG file for a device.

**Request** — multipart/form-data
| Field | Type | Description |
|-------|------|-------------|
| mac | string | Device MAC |
| file | file | XMLTV `.xml` file |

**Response 201** — EPG object with `type: "file"`

---

## Admin — Device management

### DELETE /api/portal/clear

Wipe all playlists and EPG for a device and set a clear flag so the next sync instructs the app to clear its local data.

**Request body**
```json
{ "mac": "AA:BB:CC:DD:EE:FF" }
```

**Response 200** — `{ "ok": true }`

---

## Device Sync

### GET /api/sync?mac=\<mac\>

Called periodically by the Android app. Returns the current configuration diff.

**Query params**
| Param | Type | Required |
|-------|------|----------|
| mac | string | yes |

**Response 200 — action: none**
```json
{ "action": "none", "playlists": [], "epg": null }
```

**Response 200 — action: update**
```json
{
  "action": "update",
  "playlists": [
    {
      "id": 1,
      "name": "Live TV",
      "source_type": "url",
      "url": "http://example.com/live.m3u"
    }
  ],
  "epg": {
    "type": "url",
    "url": "http://example.com/epg.xml"
  }
}
```

**Response 200 — action: clear**
```json
{ "action": "clear", "playlists": [], "epg": null }
```

The `clear` action is returned **once** — the server resets the clear flag after the first successful response. Subsequent syncs return `none` (unless new data is added).

---

## Health check

### GET /health

Returns `200 OK` when the server is running. Used by Docker HEALTHCHECK.

```json
{ "status": "ok" }
```
