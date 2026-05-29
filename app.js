let statusData = [];
let pendingMedId = null;
let pendingHistoryMedId = null;
let countdownInterval = null;

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  loadConfig();
  fetchStatus();
  setInterval(fetchStatus, 30000);
});

// ── Status & cards ───────────────────────────────────────────────────────────

async function fetchStatus() {
  try {
    const res = await fetch("/api/status");
    statusData = await res.json();
    renderCards(statusData);
    startCountdowns();
  } catch (e) {
    console.error("Error cargando estado:", e);
  }
}

function renderCards(meds) {
  const container = document.getElementById("cards-container");
  container.innerHTML = "";
  meds.forEach((med) => container.appendChild(buildCard(med)));
}

function buildCard(med) {
  const card = document.createElement("div");
  card.className = "med-card";
  card.id = `card-${med.id}`;

  const { badgeClass, badgeText } = getStatusInfo(med);

  const lastStr = med.last_applied
    ? formatDatetime(med.last_applied)
    : "Sin registros";

  const nextStr = med.next_due
    ? formatDatetime(med.next_due)
    : "—";

  card.innerHTML = `
    <div class="card-header">
      <div class="card-icon">${med.icon}</div>
      <div class="card-title">
        <h2>${med.name}</h2>
        <p>${med.description}</p>
      </div>
    </div>
    <div class="card-body">
      <div class="status-row">
        <span class="status-badge ${badgeClass}">${badgeText}</span>
        <span class="interval-tag">cada ${med.interval_hours}hs</span>
      </div>
      <div class="times">
        <div class="time-block">
          <div class="label">Última aplicación</div>
          <div class="value">${lastStr}</div>
        </div>
        <div class="time-block">
          <div class="label">Próxima aplicación</div>
          <div class="value ${med.is_overdue ? "overdue" : ""}">${nextStr}</div>
        </div>
      </div>
      <div class="countdown ${badgeClass}" id="countdown-${med.id}">
        ${getCountdownText(med)}
      </div>
      <div class="card-actions">
        <button class="btn btn-primary" onclick="applyNow('${med.id}', '${med.name}')">
          ✅ Apliqué ahora
        </button>
        <button class="btn btn-ghost" onclick="openApplyWithTime('${med.id}', '${med.name}')">
          🕐 Otra hora
        </button>
        <button class="btn btn-ghost" onclick="openHistory('${med.id}', '${med.name}')">
          📋
        </button>
      </div>
    </div>
  `;
  return card;
}

function getStatusInfo(med) {
  if (!med.last_applied) {
    return { badgeClass: "unknown", badgeText: "⬜ Sin registros" };
  }
  const secs = med.remaining_seconds;
  if (med.is_overdue) {
    return { badgeClass: "overdue", badgeText: "🔴 Vencida" };
  }
  if (secs < 60 * 60) {
    return { badgeClass: "warning", badgeText: "🟡 Por vencer" };
  }
  return { badgeClass: "ok", badgeText: "🟢 Al día" };
}

function getCountdownText(med) {
  if (!med.last_applied) return "Registrá la primera aplicación";
  if (med.is_overdue) {
    return "¡Vencida hace " + formatDuration(-med.remaining_seconds) + "!";
  }
  return "Faltan " + formatDuration(med.remaining_seconds);
}

// ── Countdowns (updated every second) ───────────────────────────────────────

function startCountdowns() {
  if (countdownInterval) clearInterval(countdownInterval);
  countdownInterval = setInterval(tickCountdowns, 1000);
}

function tickCountdowns() {
  statusData.forEach((med) => {
    if (med.remaining_seconds === null) return;
    med.remaining_seconds -= 1;
    med.is_overdue = med.remaining_seconds < 0;

    const el = document.getElementById(`countdown-${med.id}`);
    if (!el) return;

    const { badgeClass } = getStatusInfo(med);
    el.className = `countdown ${badgeClass}`;
    el.textContent = getCountdownText(med);

    // Also update badge
    const badge = document.querySelector(`#card-${med.id} .status-badge`);
    if (badge) {
      const { badgeClass: bc, badgeText: bt } = getStatusInfo(med);
      badge.className = `status-badge ${bc}`;
      badge.textContent = bt;
    }
  });
}

// ── Apply ────────────────────────────────────────────────────────────────────

async function applyNow(medId, medName) {
  await doApply(medId, null);
}

function openApplyWithTime(medId, medName) {
  pendingMedId = medId;
  document.getElementById("modal-title").textContent = `Registrar: ${medName}`;
  const now = toLocalISOString(new Date());
  document.getElementById("modal-datetime").value = now;
  document.getElementById("modal-overlay").classList.remove("hidden");
}

function closeModal() {
  document.getElementById("modal-overlay").classList.add("hidden");
  pendingMedId = null;
}

async function confirmApply() {
  const val = document.getElementById("modal-datetime").value;
  if (!val) return;
  await doApply(pendingMedId, val);
  closeModal();
}

async function doApply(medId, appliedAt) {
  const body = { med_id: medId };
  if (appliedAt) body.applied_at = appliedAt;
  try {
    await fetch("/api/apply", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    await fetchStatus();
  } catch (e) {
    alert("Error al registrar la aplicación.");
  }
}

// ── History ──────────────────────────────────────────────────────────────────

async function openHistory(medId, medName) {
  pendingHistoryMedId = medId;
  document.getElementById("history-title").textContent = `Historial: ${medName}`;
  await loadHistory(medId);
  document.getElementById("history-overlay").classList.remove("hidden");
}

function closeHistory() {
  document.getElementById("history-overlay").classList.add("hidden");
}

async function loadHistory(medId) {
  const res = await fetch(`/api/history/${medId}`);
  const rows = await res.json();
  const list = document.getElementById("history-list");
  if (rows.length === 0) {
    list.innerHTML = '<p style="color:#aaa;text-align:center;padding:20px">Sin registros</p>';
    return;
  }
  list.innerHTML = rows
    .map(
      (r) => `
    <div class="history-item">
      <span>${formatDatetime(r.applied_at)}</span>
      <button class="history-delete" onclick="deleteRecord(${r.id})" title="Eliminar">✕</button>
    </div>`
    )
    .join("");
}

async function deleteRecord(id) {
  await fetch(`/api/delete/${id}`, { method: "DELETE" });
  await loadHistory(pendingHistoryMedId);
  await fetchStatus();
}

// ── Config ───────────────────────────────────────────────────────────────────

async function loadConfig() {
  const res = await fetch("/api/config");
  const cfg = await res.json();
  document.getElementById("cfg-phone").value = cfg.whatsapp_phone || "";
  if (cfg.has_apikey) {
    document.getElementById("cfg-apikey").placeholder = "••••••  (ya guardada)";
  }
}

async function saveConfig() {
  const phone = document.getElementById("cfg-phone").value.trim();
  const apikey = document.getElementById("cfg-apikey").value.trim();
  const body = { whatsapp_phone: phone };
  if (apikey) body.callmebot_apikey = apikey;

  const res = await fetch("/api/config", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json();
  showConfigStatus(data.success ? "✅ Configuración guardada." : "❌ Error al guardar.");
  if (data.success) loadConfig();
}

async function testWhatsapp() {
  showConfigStatus("Enviando mensaje de prueba...");
  const res = await fetch("/api/test-whatsapp", { method: "POST" });
  const data = await res.json();
  showConfigStatus(
    data.success
      ? "✅ ¡Mensaje enviado! Revisá tu WhatsApp."
      : "❌ No se pudo enviar. Verificá el número y la API key."
  );
}

function showConfigStatus(msg) {
  const el = document.getElementById("config-status");
  el.textContent = msg;
  setTimeout(() => (el.textContent = ""), 5000);
}

function toggleConfig() {
  const form = document.getElementById("config-form");
  form.classList.toggle("hidden");
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function formatDatetime(isoStr) {
  const d = new Date(isoStr);
  if (isNaN(d)) return "—";
  return d.toLocaleString("es-AR", {
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds) {
  const s = Math.abs(Math.round(seconds));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h > 0) return `${h}h ${pad(m)}m`;
  if (m > 0) return `${m}m ${pad(ss)}s`;
  return `${ss}s`;
}

function pad(n) {
  return String(n).padStart(2, "0");
}

function toLocalISOString(date) {
  const offset = date.getTimezoneOffset();
  const local = new Date(date.getTime() - offset * 60000);
  return local.toISOString().slice(0, 16);
}
