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
    el.value = filters[field] ?? "";
  }
}

async function loadFilterOptions() {
  const res = await fetch("/api/filters/options");
  const data = await res.json();
  for (const key of ["tipo_oferta", "organismo", "region", "comuna"]) {
    const select = document.getElementById(key);
    if (!select) continue;
    const defaultLabel = select.options[0]?.textContent || "Todas";
    select.innerHTML = "";
    const defaultOpt = document.createElement("option");
    defaultOpt.value = "";
    defaultOpt.textContent = defaultLabel;
    select.appendChild(defaultOpt);
    for (const val of data[key] || []) {
      const opt = document.createElement("option");
      opt.value = val;
      opt.textContent = val;
      select.appendChild(opt);
    }
  }
}

function renderOffers(items) {
  const tbody = document.getElementById("resultsTable");
  const cards = document.getElementById("resultsCards");
  tbody.innerHTML = "";
  cards.innerHTML = "";
  for (const row of items) {
    const descripcion = renderExpandableText(row.descripcion);
    const descripcionProducto = renderExpandableText(row.descripcion_producto);
    const pubDate = row.fecha_publicacion ?? "";
    const closeDate = row.fecha_cierre ?? "";
    const rowType = row.tipo_oferta ?? "";
    const tr = document.createElement("tr");
    const safeCode = row.link
      ? `<a href="${escapeHtml(row.link)}" target="_blank" rel="noopener noreferrer">${escapeHtml(row.codigo_externo ?? "")}</a>`
      : escapeHtml(row.codigo_externo ?? "");
    tr.innerHTML = `
      <td>${safeCode}</td>
      <td>${escapeHtml(row.nombre ?? "")}</td>
      <td class="description-cell">${descripcion}</td>
      <td class="description-cell">${descripcionProducto}</td>
      <td>${escapeHtml(row.organismo ?? "")}</td>
      <td>${escapeHtml(rowType)}</td>
      <td>${escapeHtml(row.region ?? "")}</td>
      <td>${escapeHtml(pubDate)}</td>
    `;
    tbody.appendChild(tr);

    const card = document.createElement("article");
    card.className = "offer-card";
    card.innerHTML = `
      <h3>${safeCode}</h3>
      <p><strong>Nombre:</strong> ${escapeHtml(row.nombre ?? "")}</p>
      <p><strong>Tipo:</strong> ${escapeHtml(rowType)}</p>
      <p><strong>Organismo:</strong> ${escapeHtml(row.organismo ?? "")}</p>
      <p><strong>Region:</strong> ${escapeHtml(row.region ?? "")}</p>
      <p><strong>Publicacion:</strong> ${escapeHtml(pubDate)}</p>
      <p><strong>Cierre:</strong> ${escapeHtml(closeDate)}</p>
      <p><strong>Descripcion:</strong> ${descripcion}</p>
      <p><strong>Descripcion producto:</strong> ${descripcionProducto}</p>
    `;
    cards.appendChild(card);
  }
}

async function loadOffers() {
  const params = new URLSearchParams(getFiltersFromForm());
  params.set("page", "1");
  params.set("page_size", "100");
  const res = await fetch(`/api/offers?${params.toString()}`);
  const data = await res.json();
  document.getElementById("resultCount").textContent = String(data.total ?? 0);
  renderOffers(data.items ?? []);
}

async function loadSavedFilters() {
  const res = await fetch("/api/saved-filters");
  const data = await res.json();
  const list = document.getElementById("savedFilters");
  list.innerHTML = "";
  for (const item of data.items || []) {
    const li = document.createElement("li");
    const runBtn = document.createElement("button");
    runBtn.textContent = `Usar: ${item.name}`;
    runBtn.className = "ghost";
    runBtn.onclick = () => {
      setFiltersToForm(item);
      loadOffers();
    };
    const delBtn = document.createElement("button");
    delBtn.textContent = "Borrar";
    delBtn.onclick = async () => {
      await fetch(`/api/saved-filters/${item.id}`, { method: "DELETE" });
      loadSavedFilters();
    };
    li.appendChild(runBtn);
    li.appendChild(delBtn);
    list.appendChild(li);
  }
}

async function saveCurrentFilter() {
  const name = document.getElementById("savedFilterName").value.trim();
  if (!name) {
    alert("Ingresa un nombre para el filtro.");
    return;
  }
  const payload = { name, ...getFiltersFromForm() };
  const res = await fetch("/api/saved-filters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    alert(err.detail || "No se pudo guardar el filtro.");
    return;
  }
  document.getElementById("savedFilterName").value = "";
  loadSavedFilters();
}

async function triggerUpdateOffers() {
  const status = document.getElementById("updateStatus");
  status.textContent = "Actualizando...";
  const btn = document.getElementById("updateOffers");
  btn.disabled = true;
  try {
    const res = await fetch("/api/update-offers", { method: "POST" });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || "Fallo al actualizar.");
    }
    status.textContent = `OK: ${data.rows} filas, +${data.inserted} nuevas, ${data.updated} actualizadas`;
    await loadFilterOptions();
    await loadOffers();
  } catch (err) {
    status.textContent = `Error: ${err.message}`;
  } finally {
    btn.disabled = false;
  }
}

function clearFilters() {
  setFiltersToForm({});
  loadOffers();
}

document.getElementById("applyFilters").addEventListener("click", loadOffers);
document.getElementById("saveFilter").addEventListener("click", saveCurrentFilter);
document.getElementById("clearFilters").addEventListener("click", clearFilters);
document.getElementById("updateOffers").addEventListener("click", triggerUpdateOffers);

loadFilterOptions().then(() => loadOffers());
loadSavedFilters();
