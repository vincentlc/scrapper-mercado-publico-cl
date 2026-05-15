// ========== CONFIGURACIÓN ==========
// URL base de la API (Vercel serverless)
const API_BASE = 'https://scrapper-mercado-publico-cl.vercel.app';

const filterFields = [
  "keyword",
  "tipo_oferta",
  "utm_range",
  "organismo",
  "region",
  "comuna",
  "start_date",
  "end_date",
  "start_close_date",
  "end_close_date",
];

const DESCRIPTION_PREVIEW_LENGTH = 180;

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function renderExpandableText(text, maxLength = DESCRIPTION_PREVIEW_LENGTH) {
  const clean = String(text ?? "").trim();
  if (!clean) return "";
  if (clean.length <= maxLength) return escapeHtml(clean);
  const shortText = `${escapeHtml(clean.slice(0, maxLength))}...`;
  return `
    <details class="expandable-text">
      <summary><span>${shortText}</span> <span class="more-info">Mas info</span></summary>
      <div class="expandable-body">${escapeHtml(clean)}</div>
    </details>
  `;
}

function getFiltersFromForm() {
  const out = {};
  for (const field of filterFields) {
    const el = document.getElementById(field);
    if (!el) continue;
    const value = el.value?.trim();
    if (value) out[field] = value;
  }
  return out;
}

function setFiltersToForm(filters) {
  for (const field of filterFields) {
    const el = document.getElementById(field);
    if (!el) continue;
    el.value = filters[field] || "";
  }
}

async function loadFilterOptions() {
  const res = await fetch(`${API_BASE}/api/filters/options`);
  if (!res.ok) return;
  const data = await res.json();
  for (const [field, values] of Object.entries(data)) {
    const el = document.getElementById(field);
    if (!el) continue;
    for (const val of values) {
      const option = document.createElement("option");
      option.value = val;
      option.textContent = val;
      el.appendChild(option);
    }
  }
}

function renderOffers(offers) {
  const tbody = document.getElementById("resultsTable");
  const cards = document.getElementById("resultsCards");
  const count = document.getElementById("resultCount");

  tbody.innerHTML = "";
  cards.innerHTML = "";
  count.textContent = offers?.length ?? 0;

  if (!offers || offers.length === 0) {
    tbody.innerHTML =
      '<tr><td colspan="8" style="text-align: center; padding: 24px; color: #999;">Sin resultados</td></tr>';
    return;
  }

  for (const offer of offers) {
    // Tabla
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${escapeHtml(offer.codigo_externo)}</td>
      <td>${escapeHtml(offer.nombre)}</td>
      <td>${renderExpandableText(offer.descripcion)}</td>
      <td>${renderExpandableText(offer.descripcion_producto)}</td>
      <td>${escapeHtml(offer.organismo)}</td>
      <td>${escapeHtml(offer.tipo_oferta)}</td>
      <td>${escapeHtml(offer.region)}</td>
      <td>${offer.fecha_publicacion}</td>
    `;
    tbody.appendChild(row);

    // Card (mobile-friendly)
    const card = document.createElement("div");
    card.className = "offer-card";
    card.innerHTML = `
      <h3>${escapeHtml(offer.nombre)}</h3>
      <p><strong>Código:</strong> ${escapeHtml(offer.codigo_externo)}</p>
      <p><strong>Organismo:</strong> ${escapeHtml(offer.organismo)}</p>
      <p><strong>Región:</strong> ${escapeHtml(offer.region)}</p>
      <p><strong>Tipo:</strong> ${escapeHtml(offer.tipo_oferta)}</p>
      <p><strong>Publicación:</strong> ${offer.fecha_publicacion}</p>
      <p><strong>Cierre:</strong> ${offer.fecha_cierre}</p>
      ${offer.link ? `<a href="${offer.link}" target="_blank">Ver en Mercado Público →</a>` : ""}
    `;
    cards.appendChild(card);
  }
}

async function loadOffers() {
  const filters = getFiltersFromForm();
  const params = new URLSearchParams(filters);
  const res = await fetch(`${API_BASE}/api/offers?${params.toString()}`, {
    mode: "cors",
  });
  if (!res.ok) {
    console.error("Error loading offers:", res);
    return;
  }
  const data = await res.json();
  renderOffers(data.offers);
}

async function loadSavedFilters() {
  const res = await fetch(`${API_BASE}/api/saved-filters`);
  if (!res.ok) {
    console.error("Error loading saved filters:", res);
    return;
  }
  const filters = await res.json();
  const ul = document.getElementById("savedFilters");
  ul.innerHTML = "";
  for (const item of filters.filters || []) {
    const li = document.createElement("li");
    li.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center;">
        <a href="javascript:loadFilter('${escapeHtml(
          JSON.stringify(item.filter_json)
        )}');">${escapeHtml(item.filter_name)}</a>
        <button class="ghost" onclick="deleteSavedFilter(${item.id})">Borrar</button>
      </div>
    `;
    ul.appendChild(li);
  }
}

function loadFilter(filterJson) {
  setFiltersToForm(JSON.parse(filterJson));
  loadOffers();
}

async function deleteSavedFilter(id) {
  if (!confirm("¿Borrar filtro?")) return;
  const res = await fetch(`${API_BASE}/api/saved-filters/${id}`, {
    method: "DELETE",
  });
  if (res.ok) {
    loadSavedFilters();
  }
}

async function saveFilter() {
  const name = document.getElementById("savedFilterName").value?.trim();
  if (!name) {
    alert("Ingresa un nombre para el filtro");
    return;
  }
  const filters = getFiltersFromForm();
  const res = await fetch(`${API_BASE}/api/saved-filters`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, filter_json: filters }),
  });
  if (res.ok) {
    document.getElementById("savedFilterName").value = "";
    loadSavedFilters();
  }
}

async function updateOffers() {
  const btn = document.getElementById("updateOffers");
  const status = document.getElementById("updateStatus");
  btn.disabled = true;
  status.textContent = "Actualizando...";
  try {
    const res = await fetch(`${API_BASE}/api/update-offers`, { method: "POST" });
    if (res.ok) {
      status.textContent = "✅ Actualizado";
      setTimeout(() => {
        status.textContent = "";
      }, 3000);
      loadOffers();
    } else {
      status.textContent = "❌ Error";
    }
  } finally {
    btn.disabled = false;
  }
}

// ========== INIT ==========
document.addEventListener("DOMContentLoaded", () => {
  loadFilterOptions();
  loadOffers();
  loadSavedFilters();

  document.getElementById("applyFilters").addEventListener("click", loadOffers);
  document.getElementById("clearFilters").addEventListener("click", () => {
    for (const field of filterFields) {
      const el = document.getElementById(field);
      if (el) el.value = "";
    }
    loadOffers();
  });
  document
    .getElementById("saveFilter")
    .addEventListener("click", saveFilter);
  document
    .getElementById("updateOffers")
    .addEventListener("click", updateOffers);
});
