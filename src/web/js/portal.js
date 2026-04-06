/**
 * portal.js — Lógica del panel de administración Cine Tv.
 * Gestión de dispositivos, usuarios, códigos de activación y grupos.
 */
import {
  getPlaylists, uploadPlaylist, savePlaylistUrl, deletePlaylist, clearDevice,
  getEpg, uploadEpg, saveEpgUrl, deleteEpg,
  saveXtreamList,
  getDeviceLists, getListGroups, saveListGroups, deleteDeviceList,
  getAdminUsers, giftSubscription, getAdminStats,
  generateCodes, getCodes,
  getDeviceLicense,
} from "./api.js";

// ── Auth guard ────────────────────────────────────────────────────────────────
if (!localStorage.getItem("cinetv_token")) {
  window.location.href = "/";
}

// ── Logout ────────────────────────────────────────────────────────────────────
document.getElementById("logout-btn").addEventListener("click", () => {
  localStorage.removeItem("cinetv_token");
  window.location.href = "/";
});

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = "success") {
  const tc = document.getElementById("toast-container");
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  tc.appendChild(el);
  setTimeout(() => el.remove(), 3500);
}

// ── Overlay ───────────────────────────────────────────────────────────────────
function showOverlay() { document.getElementById("overlay").classList.add("visible"); }
function hideOverlay() { document.getElementById("overlay").classList.remove("visible"); }

// ── Main tabs ─────────────────────────────────────────────────────────────────
document.querySelectorAll(".main-tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".main-tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".main-panel").forEach(p => p.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.panel).classList.add("active");
    if (btn.dataset.panel === "panel-users") loadUsers();
    if (btn.dataset.panel === "panel-codes") loadCodes();
  });
});

// ── Sub-tabs ──────────────────────────────────────────────────────────────────
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    const group = btn.dataset.group;
    document.querySelectorAll(`.tab-btn[data-group="${group}"]`).forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-panel").forEach(p => {
      if (p.id === btn.dataset.tab) p.classList.add("active");
      else if (document.querySelector(`.tab-btn[data-tab="${p.id}"][data-group="${group}"]`)) p.classList.remove("active");
    });
    btn.classList.add("active");
  });
});

// ─────────────────────────────────────────────────────────────────────────────
// PANEL DISPOSITIVOS
// ─────────────────────────────────────────────────────────────────────────────

let currentDeviceId = "";

async function loadStats() {
  try {
    const stats = await getAdminStats();
    document.getElementById("stat-users").textContent = stats.total_users ?? "—";
    document.getElementById("stat-active").textContent = stats.active_subscriptions ?? "—";
    document.getElementById("stat-codes").textContent = stats.available_codes ?? "—";
    document.getElementById("stat-lists").textContent = stats.total_lists ?? "—";
    document.getElementById("stats-bar").classList.remove("hidden");
  } catch (_) {}
}
loadStats();

document.getElementById("load-btn").addEventListener("click", async () => {
  const raw = document.getElementById("device-input").value.trim();
  if (!raw) { toast("Introduce un Device ID o MAC", "error"); return; }
  currentDeviceId = raw;
  showOverlay();
  try {
    await Promise.all([loadLicense(currentDeviceId), loadPlaylists(currentDeviceId), loadEpg(currentDeviceId)]);
    document.getElementById("management").classList.remove("hidden");
  } catch (err) {
    toast(err.message, "error");
  } finally {
    hideOverlay();
  }
});

// ── Licencia ──────────────────────────────────────────────────────────────────
async function loadLicense(deviceId) {
  try {
    const lic = await getDeviceLicense(deviceId);
    const badge = document.getElementById("license-badge");
    const info  = document.getElementById("license-info");
    badge.textContent = lic.status === "active" ? "Activa" : lic.status === "trial" ? "Trial" : "Expirada";
    badge.className = `badge badge-${lic.status === "active" ? "active" : lic.status === "trial" ? "trial" : "expired"}`;
    const exp = lic.expires ? new Date(lic.expires).toLocaleDateString("es-ES") : "—";
    info.textContent = lic.status === "trial"
      ? `Periodo de prueba — ${lic.days_left} día(s) restante(s). Expira: ${exp}`
      : lic.status === "active"
      ? `Suscripción activa — ${lic.days_left} día(s) restante(s). Expira: ${exp}`
      : `Licencia expirada el ${exp}`;
  } catch (_) {
    document.getElementById("license-info").textContent = "No se pudo obtener el estado de licencia.";
  }
}

// ── Regalo de suscripción ─────────────────────────────────────────────────────
document.getElementById("gift-btn").addEventListener("click", () => {
  document.getElementById("gift-device-label").textContent = `Dispositivo: ${currentDeviceId}`;
  document.getElementById("gift-days").value = "365";
  document.getElementById("gift-dialog").classList.add("visible");
});
document.getElementById("gift-cancel-btn").addEventListener("click", () => {
  document.getElementById("gift-dialog").classList.remove("visible");
});
document.getElementById("gift-confirm-btn").addEventListener("click", async () => {
  const days = parseInt(document.getElementById("gift-days").value, 10);
  if (!days || days < 1) { toast("Introduce un número de días válido", "error"); return; }
  showOverlay();
  try {
    await giftSubscription(currentDeviceId, days);
    document.getElementById("gift-dialog").classList.remove("visible");
    toast(`✅ ${days} día(s) regalados correctamente`);
    await loadLicense(currentDeviceId);
    await loadStats();
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── Playlists ─────────────────────────────────────────────────────────────────
async function loadPlaylists(deviceId) {
  const isMac = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(deviceId);
  try {
    if (isMac) {
      const playlists = await getPlaylists(deviceId);
      renderPortalPlaylists(playlists);
    } else {
      const lists = await getDeviceLists(deviceId);
      renderDeviceLists(lists, deviceId);
    }
  } catch (err) {
    document.getElementById("playlist-list").innerHTML =
      `<p class="text-muted">Error cargando listas: ${err.message}</p>`;
  }
}

function renderDeviceLists(lists, deviceId) {
  const container = document.getElementById("playlist-list");
  if (!lists.length) {
    container.innerHTML = '<p class="text-muted">Sin listas configuradas.</p>';
    return;
  }
  container.innerHTML = lists.map(ul => {
    const typeClass = ul.list_type === "xtream" ? "badge-xtream" : ul.list_type === "file" ? "badge-file" : "badge-url";
    const typeLabel = ul.list_type === "xtream" ? "Xtream" : ul.list_type === "file" ? "Archivo" : "URL";
    const groupsInfo = ul.selected_groups ? `<br><small style="color:#6b7280;">${ul.selected_groups.length} grupo(s) filtrados</small>` : "";
    const activeDot = ul.is_active ? ' <span style="color:#16a34a;font-size:.8rem;">● activa</span>' : "";
    return `
      <div class="playlist-item">
        <div class="name">${ul.name || "Sin nombre"}${activeDot}${groupsInfo}</div>
        <span class="badge ${typeClass}">${typeLabel}</span>
        <div class="playlist-item-actions">
          <button class="btn btn-ghost btn-sm groups-btn" data-id="${ul.id}" data-device="${deviceId}">Grupos</button>
          <button class="btn btn-danger btn-sm del-dlist-btn" data-id="${ul.id}" data-device="${deviceId}">✕</button>
        </div>
      </div>`;
  }).join("");

  container.querySelectorAll(".del-dlist-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar esta lista?")) return;
      showOverlay();
      try {
        await deleteDeviceList(btn.dataset.id, btn.dataset.device);
        toast("Lista eliminada");
        await loadPlaylists(btn.dataset.device);
      } catch (err) { toast(err.message, "error"); }
      finally { hideOverlay(); }
    });
  });
  container.querySelectorAll(".groups-btn").forEach(btn => {
    btn.addEventListener("click", () => openGroupsDialog(btn.dataset.id, btn.dataset.device));
  });
}

function renderPortalPlaylists(playlists) {
  const container = document.getElementById("playlist-list");
  if (!playlists.length) {
    container.innerHTML = '<p class="text-muted">Sin listas configuradas.</p>';
    return;
  }
  container.innerHTML = playlists.map(p => `
    <div class="playlist-item">
      <div class="name">${p.name || "Sin nombre"}</div>
      <span class="badge ${p.type === "file" ? "badge-file" : "badge-url"}">${p.type === "file" ? "Archivo" : "URL"}</span>
      <div class="playlist-item-actions">
        <button class="btn btn-danger btn-sm del-pl-btn" data-id="${p.id}">✕</button>
      </div>
    </div>`).join("");
  container.querySelectorAll(".del-pl-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      if (!confirm("¿Eliminar?")) return;
      showOverlay();
      try {
        await deletePlaylist(btn.dataset.id);
        toast("Eliminada");
        await loadPlaylists(currentDeviceId);
      } catch (err) { toast(err.message, "error"); }
      finally { hideOverlay(); }
    });
  });
}

// ── Añadir lista por archivo ──────────────────────────────────────────────────
const dropZone = document.getElementById("upload-drop");
const fileInput = document.getElementById("upload-file-input");
dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault(); dropZone.classList.remove("drag-over");
  if (e.dataTransfer.files[0]) handleFileUpload(e.dataTransfer.files[0]);
});
fileInput.addEventListener("change", () => { if (fileInput.files[0]) handleFileUpload(fileInput.files[0]); });

async function handleFileUpload(file) {
  if (!currentDeviceId) { toast("Carga un dispositivo primero", "error"); return; }
  showOverlay();
  try {
    const name = document.getElementById("upload-name").value.trim();
    await uploadPlaylist(currentDeviceId, file, name);
    toast("Lista subida");
    await loadPlaylists(currentDeviceId);
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
}

// ── Añadir URL ────────────────────────────────────────────────────────────────
document.getElementById("save-url-btn").addEventListener("click", async () => {
  if (!currentDeviceId) { toast("Carga un dispositivo primero", "error"); return; }
  const url  = document.getElementById("playlist-url").value.trim();
  const name = document.getElementById("playlist-url-name").value.trim();
  if (!url) { toast("Introduce una URL", "error"); return; }
  showOverlay();
  try {
    const isMac = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(currentDeviceId);
    if (isMac) {
      await savePlaylistUrl(currentDeviceId, url, name);
    } else {
      const res = await fetch("/api/device/lists/url", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${localStorage.getItem("cinetv_token")}` },
        body: JSON.stringify({ device_id: currentDeviceId, name, url }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Error");
    }
    toast("URL guardada");
    document.getElementById("playlist-url").value = "";
    await loadPlaylists(currentDeviceId);
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── Añadir Xtream ─────────────────────────────────────────────────────────────
document.getElementById("save-xtream-btn").addEventListener("click", async () => {
  if (!currentDeviceId) { toast("Carga un dispositivo primero", "error"); return; }
  const name   = document.getElementById("xtream-name").value.trim();
  const server = document.getElementById("xtream-server").value.trim();
  const user   = document.getElementById("xtream-user").value.trim();
  const pass   = document.getElementById("xtream-pass").value;
  if (!server || !user || !pass) { toast("Rellena servidor, usuario y contraseña", "error"); return; }
  showOverlay();
  try {
    await saveXtreamList(currentDeviceId, name, server, user, pass);
    toast("Xtream guardado");
    ["xtream-name", "xtream-server", "xtream-user", "xtream-pass"].forEach(id => { document.getElementById(id).value = ""; });
    await loadPlaylists(currentDeviceId);
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── EPG ───────────────────────────────────────────────────────────────────────
async function loadEpg(deviceId) {
  const isMac = /^([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2}$/.test(deviceId);
  if (!isMac) {
    document.getElementById("epg-none").textContent = "EPG disponible solo con identificador MAC.";
    return;
  }
  try {
    const epg = await getEpg(deviceId);
    if (epg && epg.type) {
      document.getElementById("epg-none").classList.add("hidden");
      document.getElementById("epg-existing").classList.remove("hidden");
      document.getElementById("epg-type-badge").textContent = epg.type === "file" ? "Archivo" : "URL";
      document.getElementById("epg-type-badge").className = `badge ${epg.type === "file" ? "badge-file" : "badge-url"}`;
      document.getElementById("epg-preview").textContent = (epg.content || "").substring(0, 80) + "…";
    } else {
      document.getElementById("epg-existing").classList.add("hidden");
      document.getElementById("epg-none").classList.remove("hidden");
    }
  } catch (_) {}
}

const epgDrop  = document.getElementById("epg-drop");
const epgInput = document.getElementById("epg-file-input");
epgDrop.addEventListener("click", () => epgInput.click());
epgDrop.addEventListener("dragover", e => { e.preventDefault(); epgDrop.classList.add("drag-over"); });
epgDrop.addEventListener("dragleave", () => epgDrop.classList.remove("drag-over"));
epgDrop.addEventListener("drop", e => { e.preventDefault(); epgDrop.classList.remove("drag-over"); if (e.dataTransfer.files[0]) handleEpgUpload(e.dataTransfer.files[0]); });
epgInput.addEventListener("change", () => { if (epgInput.files[0]) handleEpgUpload(epgInput.files[0]); });

async function handleEpgUpload(file) {
  if (!currentDeviceId) return;
  showOverlay();
  try { await uploadEpg(currentDeviceId, file); toast("EPG subido"); await loadEpg(currentDeviceId); }
  catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
}

document.getElementById("save-epg-url-btn").addEventListener("click", async () => {
  const url = document.getElementById("epg-url").value.trim();
  if (!url) { toast("Introduce una URL de EPG", "error"); return; }
  showOverlay();
  try { await saveEpgUrl(currentDeviceId, url); toast("EPG guardado"); await loadEpg(currentDeviceId); }
  catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

document.getElementById("delete-epg-btn").addEventListener("click", async () => {
  if (!confirm("¿Eliminar EPG?")) return;
  showOverlay();
  try { await deleteEpg(currentDeviceId); toast("EPG eliminado"); await loadEpg(currentDeviceId); }
  catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── Clear device ──────────────────────────────────────────────────────────────
document.getElementById("clear-btn").addEventListener("click", () =>
  document.getElementById("clear-dialog").classList.add("visible")
);
document.getElementById("clear-cancel-btn").addEventListener("click", () =>
  document.getElementById("clear-dialog").classList.remove("visible")
);
document.getElementById("clear-confirm-btn").addEventListener("click", async () => {
  showOverlay();
  try {
    await clearDevice(currentDeviceId);
    document.getElementById("clear-dialog").classList.remove("visible");
    toast("Dispositivo marcado para limpieza");
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── Groups dialog ─────────────────────────────────────────────────────────────
let groupsListId = "";
let groupsDeviceId = "";
let groupsSelected = new Set();

async function openGroupsDialog(listId, deviceId) {
  groupsListId   = listId;
  groupsDeviceId = deviceId;
  groupsSelected = new Set();

  document.getElementById("groups-loading").classList.remove("hidden");
  document.getElementById("groups-list").classList.add("hidden");
  document.getElementById("groups-dialog").classList.add("visible");

  try {
    const data = await getListGroups(listId, deviceId);
    const groups = data.groups || [];
    const listDiv = document.getElementById("groups-list");
    if (!groups.length) {
      listDiv.innerHTML = '<p class="text-muted" style="text-align:center;padding:16px;">No se encontraron grupos.</p>';
    } else {
      listDiv.innerHTML = groups.map(g =>
        `<div class="group-chip" data-group="${g.replace(/"/g,'&quot;')}">${g}</div>`
      ).join("");
      listDiv.querySelectorAll(".group-chip").forEach(chip => {
        chip.addEventListener("click", () => {
          chip.classList.toggle("selected");
          if (chip.classList.contains("selected")) groupsSelected.add(chip.dataset.group);
          else groupsSelected.delete(chip.dataset.group);
        });
      });
    }
    document.getElementById("groups-loading").classList.add("hidden");
    listDiv.classList.remove("hidden");
  } catch (err) {
    document.getElementById("groups-loading").textContent = "Error: " + err.message;
  }
}

document.getElementById("groups-all-btn").addEventListener("click", () => {
  document.querySelectorAll("#groups-list .group-chip").forEach(chip => {
    chip.classList.add("selected");
    groupsSelected.add(chip.dataset.group);
  });
});
document.getElementById("groups-none-btn").addEventListener("click", () => {
  document.querySelectorAll("#groups-list .group-chip").forEach(chip => chip.classList.remove("selected"));
  groupsSelected.clear();
});
document.getElementById("groups-cancel-btn").addEventListener("click", () =>
  document.getElementById("groups-dialog").classList.remove("visible")
);
document.getElementById("groups-save-btn").addEventListener("click", async () => {
  showOverlay();
  try {
    await saveListGroups(groupsListId, groupsDeviceId, [...groupsSelected]);
    document.getElementById("groups-dialog").classList.remove("visible");
    toast(`Grupos guardados (${groupsSelected.size} seleccionados)`);
    await loadPlaylists(currentDeviceId);
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ─────────────────────────────────────────────────────────────────────────────
// PANEL USUARIOS
// ─────────────────────────────────────────────────────────────────────────────

async function loadUsers(page = 1) {
  const tbody = document.getElementById("users-tbody");
  tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:20px;">Cargando…</td></tr>`;
  try {
    const data = await getAdminUsers(page);
    tbody.innerHTML = (data.items || []).map(u => {
      const lic = u.license;
      const badgeClass = lic.status === "active" ? "badge-active" : lic.status === "trial" ? "badge-trial" : "badge-expired";
      const badgeLabel = lic.status === "active" ? "Activa" : lic.status === "trial" ? `Trial (${lic.days_left}d)` : "Expirada";
      const reg = u.created_at ? new Date(u.created_at).toLocaleDateString("es-ES") : "—";
      const exp = lic.expires ? new Date(lic.expires).toLocaleDateString("es-ES") : "—";
      return `
        <tr>
          <td class="device-id-cell monospace" title="${u.device_id}">${u.device_id.substring(0,16)}…</td>
          <td>${reg}</td>
          <td><span class="badge ${badgeClass}">${badgeLabel}</span></td>
          <td>${exp}</td>
          <td><button class="btn btn-primary btn-sm gift-user-btn" data-id="${u.device_id}">🎁 Regalar</button></td>
        </tr>`;
    }).join("") || `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:20px;">Sin usuarios.</td></tr>`;

    tbody.querySelectorAll(".gift-user-btn").forEach(btn => {
      btn.addEventListener("click", () => {
        currentDeviceId = btn.dataset.id;
        document.getElementById("gift-device-label").textContent = `Dispositivo: ${btn.dataset.id}`;
        document.getElementById("gift-days").value = "365";
        document.getElementById("gift-dialog").classList.add("visible");
      });
    });

    renderPagination("users-pagination", data.page, data.pages, loadUsers);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;">Error: ${err.message}</td></tr>`;
  }
}

document.getElementById("refresh-users-btn").addEventListener("click", () => loadUsers());

// ─────────────────────────────────────────────────────────────────────────────
// PANEL CÓDIGOS
// ─────────────────────────────────────────────────────────────────────────────

async function loadCodes(page = 1) {
  const tbody = document.getElementById("codes-tbody");
  tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:20px;">Cargando…</td></tr>`;
  try {
    const filterVal = document.getElementById("codes-filter").value;
    const used = filterVal === "" ? null : filterVal === "true";
    const data = await getCodes(used, page);
    tbody.innerHTML = (data.items || []).map(c => {
      const createdAt = c.created_at ? new Date(c.created_at).toLocaleDateString("es-ES") : "—";
      const usedBy = c.used_by_device
        ? `<span class="monospace" title="${c.used_by_device}" style="font-size:.75rem;">${c.used_by_device.substring(0,14)}…</span>`
        : `<span class="badge" style="background:#dcfce7;color:#14532d;">Disponible</span>`;
      return `
        <tr>
          <td><span class="code-box" title="Clic para copiar" style="cursor:pointer;"
              onclick="navigator.clipboard.writeText('${c.code}');this.style.background='#14532d';">${c.code}</span></td>
          <td>${c.duration_days}d</td>
          <td>${c.note || "—"}</td>
          <td>${createdAt}</td>
          <td>${usedBy}</td>
        </tr>`;
    }).join("") || `<tr><td colspan="5" class="text-muted" style="text-align:center;padding:20px;">Sin códigos.</td></tr>`;

    renderPagination("codes-pagination", data.page, Math.ceil((data.total || 0) / 50) || 1, loadCodes);
  } catch (err) {
    tbody.innerHTML = `<tr><td colspan="5" class="text-muted" style="text-align:center;">Error: ${err.message}</td></tr>`;
  }
}

document.getElementById("refresh-codes-btn").addEventListener("click", () => loadCodes());
document.getElementById("codes-filter").addEventListener("change", () => loadCodes(1));

document.getElementById("generate-codes-btn").addEventListener("click", async () => {
  const quantity = parseInt(document.getElementById("code-quantity").value, 10) || 1;
  const duration = parseInt(document.getElementById("code-duration").value, 10) || 365;
  const note     = document.getElementById("code-note").value.trim();
  showOverlay();
  try {
    const data = await generateCodes(quantity, duration, note || null);
    const resultDiv = document.getElementById("new-codes-result");
    resultDiv.innerHTML = `
      <p class="text-success" style="margin-bottom:8px;">✅ ${data.codes.length} código(s) generado(s):</p>
      <div class="codes-generated">
        ${data.codes.map(c => `<span class="code-box" title="Clic para copiar" style="cursor:pointer;"
          onclick="navigator.clipboard.writeText('${c.code}');this.style.background='#14532d';">${c.code}</span>`).join("")}
      </div>
      <p class="text-muted mt-8" style="font-size:.8rem;">Haz clic en un código para copiarlo.</p>`;
    resultDiv.classList.remove("hidden");
    toast(`${data.codes.length} código(s) generado(s)`);
    await loadCodes();
    await loadStats();
  } catch (err) { toast(err.message, "error"); }
  finally { hideOverlay(); }
});

// ── Paginación ────────────────────────────────────────────────────────────────
function renderPagination(containerId, currentPage, totalPages, callback) {
  const container = document.getElementById(containerId);
  if (totalPages <= 1) { container.innerHTML = ""; return; }
  let html = "";
  for (let i = 1; i <= Math.min(totalPages, 10); i++) {
    html += `<button class="page-btn ${i === currentPage ? "active" : ""}" data-page="${i}">${i}</button>`;
  }
  container.innerHTML = html;
  container.querySelectorAll(".page-btn").forEach(btn => {
    btn.addEventListener("click", () => callback(parseInt(btn.dataset.page, 10)));
  });
}
