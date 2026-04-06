/**
 * api.js — Helpers fetch con autorización JWT automática (Cine Tv Portal).
 */

const BASE = "";  // Same origin

function getToken() {
  return localStorage.getItem("cinetv_token");
}

function authHeaders(extra = {}) {
  const token = getToken();
  return {
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...extra,
  };
}

async function handleResponse(res) {
  if (res.status === 401) {
    localStorage.removeItem("cinetv_token");
    window.location.href = "/";
    throw new Error("Unauthorized");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const msg = data.detail || `HTTP ${res.status}`;
    throw new Error(Array.isArray(msg) ? msg.map(e => e.msg).join(", ") : msg);
  }
  return data;
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function login(username, password) {
  const res = await fetch(`${BASE}/api/admin/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  return handleResponse(res);
}

// ── Playlists (portal legacy — por MAC) ──────────────────────────────────────

export async function getPlaylists(mac) {
  const res = await fetch(`${BASE}/api/portal/playlists?mac=${encodeURIComponent(mac)}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function uploadPlaylist(mac, file, name) {
  const fd = new FormData();
  fd.append("mac", mac);
  fd.append("file", file);
  if (name) fd.append("name", name);
  const res = await fetch(`${BASE}/api/portal/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: fd,
  });
  return handleResponse(res);
}

export async function savePlaylistUrl(mac, url, name) {
  const res = await fetch(`${BASE}/api/portal/url`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ mac, url, name: name || null }),
  });
  return handleResponse(res);
}

export async function saveXtreamList(deviceId, name, server, username, password) {
  const res = await fetch(`${BASE}/api/device/lists/xtream`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ device_id: deviceId, name, server, username, password }),
  });
  return handleResponse(res);
}

export async function deletePlaylist(playlistId) {
  const res = await fetch(`${BASE}/api/portal/playlist/${playlistId}`, {
    method: "DELETE",
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function clearDevice(mac) {
  const res = await fetch(`${BASE}/api/portal/clear`, {
    method: "DELETE",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ mac }),
  });
  return handleResponse(res);
}

// ── EPG ───────────────────────────────────────────────────────────────────────

export async function getEpg(mac) {
  const res = await fetch(`${BASE}/api/portal/epg?mac=${encodeURIComponent(mac)}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function uploadEpg(mac, file) {
  const fd = new FormData();
  fd.append("mac", mac);
  fd.append("file", file);
  const res = await fetch(`${BASE}/api/portal/epg/upload`, {
    method: "POST",
    headers: authHeaders(),
    body: fd,
  });
  return handleResponse(res);
}

export async function saveEpgUrl(mac, url) {
  const res = await fetch(`${BASE}/api/portal/epg/url`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ mac, url }),
  });
  return handleResponse(res);
}

export async function deleteEpg(mac) {
  const res = await fetch(`${BASE}/api/portal/epg`, {
    method: "DELETE",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ mac }),
  });
  return handleResponse(res);
}

// ── Device lists (por device_id) ──────────────────────────────────────────────

export async function getDeviceLists(deviceId) {
  const res = await fetch(`${BASE}/api/device/lists?device_id=${encodeURIComponent(deviceId)}`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function getListGroups(listId, deviceId) {
  const res = await fetch(
    `${BASE}/api/device/lists/${listId}/groups?device_id=${encodeURIComponent(deviceId)}`,
    { headers: authHeaders() }
  );
  return handleResponse(res);
}

export async function saveListGroups(listId, deviceId, groups) {
  const res = await fetch(`${BASE}/api/device/lists/${listId}/groups`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ device_id: deviceId, groups }),
  });
  return handleResponse(res);
}

export async function deleteDeviceList(listId, deviceId) {
  const res = await fetch(
    `${BASE}/api/device/lists/${listId}?device_id=${encodeURIComponent(deviceId)}`,
    { method: "DELETE", headers: authHeaders() }
  );
  return handleResponse(res);
}

// ── Admin — Usuarios ──────────────────────────────────────────────────────────

export async function getAdminUsers(page = 1) {
  const res = await fetch(`${BASE}/api/admin/users?page=${page}&limit=50`, {
    headers: authHeaders(),
  });
  return handleResponse(res);
}

export async function giftSubscription(deviceId, durationDays) {
  const res = await fetch(`${BASE}/api/admin/gift`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ device_id: deviceId, duration_days: durationDays }),
  });
  return handleResponse(res);
}

export async function getAdminStats() {
  const res = await fetch(`${BASE}/api/admin/stats`, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Admin — Códigos ───────────────────────────────────────────────────────────

export async function generateCodes(quantity, durationDays, note) {
  const res = await fetch(`${BASE}/api/admin/codes`, {
    method: "POST",
    headers: authHeaders({ "Content-Type": "application/json" }),
    body: JSON.stringify({ quantity, duration_days: durationDays, note: note || null }),
  });
  return handleResponse(res);
}

export async function getCodes(used = null, page = 1) {
  let url = `${BASE}/api/admin/codes?page=${page}&limit=50`;
  if (used !== null) url += `&used=${used}`;
  const res = await fetch(url, { headers: authHeaders() });
  return handleResponse(res);
}

// ── Device license ────────────────────────────────────────────────────────────

export async function getDeviceLicense(deviceId) {
  const res = await fetch(
    `${BASE}/api/device/license?device_id=${encodeURIComponent(deviceId)}`,
    { headers: authHeaders() }
  );
  return handleResponse(res);
}
