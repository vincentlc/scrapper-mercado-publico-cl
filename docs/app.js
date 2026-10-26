// ========== CONFIGURACIÓN ==========
// Detectar API base automáticamente
const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? window.location.origin
  : "https://scrapper-mercado-publico-cl.vercel.app";

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
  "min_days_to_close",
  "max_days_to_close",
];

// Dropdown/date filters auto-apply on change (standard "faceted search" UX:
// a discrete selection is a completed intent, unlike a free-text field).
const AUTO_APPLY_ON_CHANGE_FIELDS = [
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
const PAGE_SIZE = 100;

let currentPage = 1;

// ========== HELPERS ==========

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

  if (clean.length <= maxLength) {
    return escapeHtml(clean);
  }

  const shortText = `${escapeHtml(clean.slice(0, maxLength))}...`;

  return `
    <details class="expandable-text">
      <summary>
        <span>${shortText}</span>
        <span class="more-info">Mas info</span>
      </summary>
      <div class="expandable-body">
        ${escapeHtml(clean)}
      </div>
    </details>
  `;
}

// Parse date in multiple formats to handle Google Sheets exports.
// IMPORTANT: Google Sheets rows are written as DD/MM/YYYY (see
// scripts/update_offers.py:format_date_for_sheet). That format must be
// parsed explicitly first: new Date("05/11/2026") is ambiguous and most
// JS engines read slash-separated dates as MM/DD/YYYY, which silently
// swaps day and month (e.g. "05/11/2026" = 5 Nov becomes 11 May).
function parseDate(dateStr) {
  if (!dateStr) return null;

  const str = String(dateStr).trim();

  // DD/MM/YYYY or DD-MM-YYYY, optionally with a time component.
  const ddmmyyyy = /^(\d{1,2})[/-](\d{1,2})[/-](\d{4})(?:[\sT](\d{1,2}):(\d{2})(?::(\d{2}))?)?$/.exec(str);
  if (ddmmyyyy) {
    const day = parseInt(ddmmyyyy[1], 10);
    const month = parseInt(ddmmyyyy[2], 10) - 1; // JS months are 0-indexed
    const year = parseInt(ddmmyyyy[3], 10);
    const hour = ddmmyyyy[4] ? parseInt(ddmmyyyy[4], 10) : 0;
    const minute = ddmmyyyy[5] ? parseInt(ddmmyyyy[5], 10) : 0;
    const second = ddmmyyyy[6] ? parseInt(ddmmyyyy[6], 10) : 0;
    const date = new Date(year, month, day, hour, minute, second);
    if (!isNaN(date.getTime())) return date;
  }

  // Fall back to native parsing for genuine ISO strings (2026-05-20T15:30:00).
  const date = new Date(str);
  if (!isNaN(date.getTime())) return date;

  return null;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const date = parseDate(dateStr);
  if (!date) return String(dateStr);
  
  return date.toLocaleDateString('es-CL', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit'
  });
}

function formatDateWithTime(dateStr) {
  if (!dateStr) return "";
  const date = parseDate(dateStr);
  if (!date) return String(dateStr);
  
  const datePart = date.toLocaleDateString('es-CL', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
  const timePart = date.toLocaleTimeString('es-CL', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  return `${datePart} ${timePart}`;
}

function formatDaysRemaining(daysValue) {
  // Simply display the value from Google Sheets formula
  // Expected format from sheet: "5d, 3h" or similar
  if (!daysValue) return "";
  return String(daysValue);
}

function isValidOfferLink(link) {
  const value = String(link ?? "").trim();
  return value.startsWith("http://") || value.startsWith("https://");
}

function offerDetailUrl(offer) {
  if (isValidOfferLink(offer.link)) {
    return offer.link;
  }
  const codigo = String(offer.codigo_externo ?? "").trim();
  if (!codigo) return "";
  return `http://www.mercadopublico.cl/Procurement/Modules/RFB/DetailsAcquisition.aspx?idLicitacion=${encodeURIComponent(codigo)}`;
}

function getFiltersFromForm() {
  const out = {};

  for (const field of filterFields) {

    const el = document.getElementById(field);

    if (!el) continue;

    const value = el.value?.trim();

    if (value) {
      out[field] = value;
    }
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

// ========== FILTER OPTIONS ==========

async function loadFilterOptions() {

  try {

    const res = await fetch(`${API_BASE}/api/filters`);

    if (!res.ok) {
      console.error("Error loading filter options");
      return;
    }

    const data = await res.json();

    for (const [field, values] of Object.entries(data)) {

      const el = document.getElementById(field);

      if (!el) continue;

      while (el.options.length > 1) {
        el.remove(1);
      }

      for (const val of values) {

        const option = document.createElement("option");

        option.value = val;
        option.textContent = val;

        el.appendChild(option);
      }
    }

  } catch (err) {

    console.error("Error loading filter options:", err);

  }
}

// ========== RENDER OFFERS ==========

function renderOffers(offers) {
  const tbody = document.getElementById("resultsTable");
  const cards = document.getElementById("resultsCards");
  const count = document.getElementById("resultCount");

  tbody.innerHTML = "";
  cards.innerHTML = "";

  count.textContent = offers?.length ?? 0;

  if (!offers || offers.length === 0) {

    tbody.innerHTML = `
      <tr>
        <td colspan="10" style="text-align:center;padding:24px;color:#999;">
          Sin resultados
        </td>
      </tr>
    `;

    return;
  }

  // Debug: Log first offer data to diagnose dias_para_cierre issue
  console.log("📊 Rendering", offers.length, "offers");
  console.log("First offer data:", offers[0]);
  console.log("First offer dias_para_cierre:", offers[0].dias_para_cierre);
  if (!offers[0].dias_para_cierre) {
    console.warn("⚠️ dias_para_cierre is empty for first offer. Keys:", Object.keys(offers[0]));
  }

  for (const offer of offers) {

    const detailUrl = offerDetailUrl(offer);

    // ===== TABLE =====

    const row = document.createElement("tr");

    const codigoHtml = detailUrl
      ? `<a href="${escapeHtml(detailUrl)}" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline; cursor: pointer;">${escapeHtml(offer.codigo_externo)}</a>`
      : escapeHtml(offer.codigo_externo);

    row.innerHTML = `
      <td data-col="codigo_externo">${codigoHtml}</td>
      <td data-col="nombre">${escapeHtml(offer.nombre)}</td>
      <td data-col="descripcion">${renderExpandableText(offer.descripcion)}</td>
      <td data-col="descripcion_producto">${renderExpandableText(offer.descripcion_producto)}</td>
      <td data-col="organismo" class="hidden">${escapeHtml(offer.organismo)}</td>
      <td data-col="tipo_oferta">${escapeHtml(offer.tipo_oferta_formateado || offer.tipo_oferta)}</td>
      <td data-col="region" class="hidden">${escapeHtml(offer.region)}</td>
      <td data-col="fecha_publicacion" class="hidden">${formatDate(offer.fecha_publicacion)}</td>
      <td data-col="fecha_cierre">${formatDateWithTime(offer.fecha_cierre)}</td>
      <td data-col="dias_para_cierre">${formatDaysRemaining(offer.dias_para_cierre)}</td>
    `;

    tbody.appendChild(row);

    // ===== MOBILE CARDS =====

    const card = document.createElement("div");

    card.className = "offer-card";

    // Hacer el código clickeable
    const codigoDisplay = detailUrl
      ? `<a href="${escapeHtml(detailUrl)}" target="_blank" rel="noopener noreferrer" style="color: #0066cc; text-decoration: underline; cursor: pointer;">${escapeHtml(offer.codigo_externo)}</a>`
      : escapeHtml(offer.codigo_externo);

    card.innerHTML = `
      <h3>${escapeHtml(offer.nombre)}</h3>

      <p>
        <strong>Código:</strong>
        ${codigoDisplay}
      </p>

      <p>
        <strong>Organismo:</strong>
        ${escapeHtml(offer.organismo)}
      </p>

      <p>
        <strong>Región:</strong>
        ${escapeHtml(offer.region)}
      </p>

      <p>
        <strong>Tipo:</strong>
        ${escapeHtml(offer.tipo_oferta_formateado || offer.tipo_oferta)}
      </p>

      <p>
        <strong>Publicación:</strong>
        ${formatDate(offer.fecha_publicacion)}
      </p>

      <p>
        <strong>Cierre:</strong>
        ${formatDateWithTime(offer.fecha_cierre)}
        ${offer.dias_para_cierre !== null && offer.dias_para_cierre !== undefined ? `<span style="color: #d9534f; font-weight: bold;"> (${formatDaysRemaining(offer.dias_para_cierre)})</span>` : ""}
      </p>

      ${
        detailUrl
          ? `
            <a href="${escapeHtml(detailUrl)}" target="_blank" rel="noopener noreferrer">
              Ver en Mercado Público →
            </a>
          `
          : ""
      }
    `;

    cards.appendChild(card);
  }
}

// ========== LOAD OFFERS ==========

async function loadOffers(page = currentPage) {

  try {

    const filters = getFiltersFromForm();

    const params = new URLSearchParams({
      ...filters,
      page,
      page_size: PAGE_SIZE,
    });

    const res = await fetch(
      `${API_BASE}/api/offers?${params.toString()}`,
      {
        mode: "cors",
      }
    );

    if (!res.ok) {
      console.error("Error loading offers:", res.status);
      return;
    }

    const data = await res.json();
    console.log("OFFERS RESPONSE:", data);

    currentPage = page;

    const items = data.items || data.offers || [];
    renderOffers(items);
    renderPagination(data);

  } catch (err) {

    console.error("Error loading offers:", err);

  }
}

function renderPagination({ page, page_size, total } = {}) {
  const info = document.getElementById("paginationInfo");
  const prevButton = document.getElementById("prevPage");
  const nextButton = document.getElementById("nextPage");

  if (!info || !prevButton || !nextButton) return;

  const pageNumber = Number(page) || 1;
  const pageSize = Number(page_size) || PAGE_SIZE;
  const totalCount = Number(total) || 0;

  const start = totalCount === 0 ? 0 : (pageNumber - 1) * pageSize + 1;
  const end = Math.min(pageNumber * pageSize, totalCount);

  info.textContent = `Mostrando ${start} a ${end} de ${totalCount}`;

  prevButton.disabled = pageNumber <= 1;
  nextButton.disabled = end >= totalCount;
}

// ========== SAVED FILTERS ==========

async function loadSavedFilters() {
  return;
  // try {

  //   const res = await fetch(`${API_BASE}/api/saved-filters`);

  //   if (!res.ok) {
  //     console.error("Error loading saved filters");
  //     return;
  //   }

  //   const data = await res.json();

  //   const ul = document.getElementById("savedFilters");

  //   ul.innerHTML = "";

  //   for (const item of data.items || []) {

  //     const li = document.createElement("li");

  //     li.innerHTML = `
  //       <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;">

  //         <button
  //           class="ghost"
  //           onclick='loadFilter(${JSON.stringify(item).replaceAll("'", "&apos;")})'
  //         >
  //           ${escapeHtml(item.name)}
  //         </button>

  //         <button
  //           class="ghost"
  //           onclick="deleteSavedFilter(${item.id})"
  //         >
  //           Borrar
  //         </button>

  //       </div>
  //     `;

  //     ul.appendChild(li);
  //   }

  // } catch (err) {

  //   console.error("Error loading saved filters:", err);

  // }
}

function loadFilter(filter) {

  setFiltersToForm(filter);

  loadOffers(1);
}

// async function deleteSavedFilter(id) {

//   if (!confirm("¿Borrar filtro?")) {
//     return;
//   }

//   try {

//     const res = await fetch(
//       `${API_BASE}/api/saved-filters/${id}`,
//       {
//         method: "DELETE",
//       }
//     );

//     if (res.ok) {
//       loadSavedFilters();
//     }

//   } catch (err) {

//     console.error("Error deleting filter:", err);

//   }
// }

async function saveFilter() {
  alert("Guardado de filtros aún no implementado");

  // const name = document
  //   .getElementById("savedFilterName")
  //   ?.value
  //   ?.trim();

  // if (!name) {
  //   alert("Ingresa un nombre para el filtro");
  //   return;
  // }

  // const filters = getFiltersFromForm();

  // const payload = {
  //   name,
  //   ...filters,
  // };

  // try {

  //   const res = await fetch(
  //     `${API_BASE}/api/saved-filters`,
  //     {
  //       method: "POST",
  //       headers: {
  //         "Content-Type": "application/json",
  //       },
  //       body: JSON.stringify(payload),
  //     }
  //   );

  //   if (res.ok) {

  //     document.getElementById("savedFilterName").value = "";

  //     loadSavedFilters();

  //   } else {

  //     console.error("Error saving filter");

  //   }

  // } catch (err) {

  //   console.error("Error saving filter:", err);

  // }
}

// ========== COLUMN RESIZE HANDLER ==========

function initializeColumnResize() {
  const table = document.querySelector("table");
  if (!table) return;

  const headers = table.querySelectorAll("th");
  const STORAGE_KEY = "column_widths";
  
  // Load saved widths
  const savedWidths = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  headers.forEach((th, idx) => {
    th.classList.add("resizable");
    if (savedWidths[idx]) {
      th.style.width = savedWidths[idx] + "px";
    }
  });

  // Resize handler
  let isResizing = false;
  let startX = 0;
  let currentHeader = null;

  headers.forEach((header, idx) => {
    header.addEventListener("mousedown", (e) => {
      // Only trigger resize on the right edge
      if (e.clientX - header.getBoundingClientRect().right > -10) {
        isResizing = true;
        currentHeader = header;
        startX = e.clientX;
        document.body.style.userSelect = "none";
        e.preventDefault();
      }
    });
  });

  document.addEventListener("mousemove", (e) => {
    if (!isResizing || !currentHeader) return;
    const delta = e.clientX - startX;
    const newWidth = currentHeader.offsetWidth + delta;
    if (newWidth > 50) {
      currentHeader.style.width = newWidth + "px";
      startX = e.clientX;
    }
  });

  document.addEventListener("mouseup", () => {
    if (!isResizing) return;
    isResizing = false;
    document.body.style.userSelect = "";

    // Save widths
    const widths = {};
    headers.forEach((th, idx) => {
      widths[idx] = th.offsetWidth;
    });
    localStorage.setItem(STORAGE_KEY, JSON.stringify(widths));
    currentHeader = null;
  });
}

function initializeColumnToggle() {
  const table = document.querySelector("table");
  const checkboxes = document.querySelectorAll(".checkbox-toggle input[type='checkbox']");
  const STORAGE_KEY = "column_visibility";
  
  console.log("🔧 Initializing column toggle. Found", checkboxes.length, "checkboxes and table:", !!table);
  
  if (!table || checkboxes.length === 0) {
    console.warn("⚠️ Missing table or checkboxes");
    return;
  }
  
  // Load saved visibility preferences
  const savedVisibility = JSON.parse(localStorage.getItem(STORAGE_KEY) || "{}");
  console.log("📦 Saved visibility:", savedVisibility);
  
  checkboxes.forEach((checkbox) => {
    const colName = checkbox.getAttribute("data-col");
    
    // If we have a saved preference, use it; otherwise use the checkbox's current state
    const shouldShow = savedVisibility[colName] !== undefined 
      ? savedVisibility[colName] 
      : checkbox.checked;
    
    console.log(`✓ Column ${colName}: shouldShow=${shouldShow}, checkbox.checked=${checkbox.checked}`);
    
    // Update checkbox to match the desired state
    checkbox.checked = shouldShow;
    
    // Apply initial hide/show
    if (!shouldShow) {
      hideColumn(colName, table);
    }
    
    // Add change listener
    checkbox.addEventListener("change", (e) => {
      console.log(`🔄 Toggle ${colName}: now checked=${checkbox.checked}`);
      if (checkbox.checked) {
        showColumn(colName, table);
      } else {
        hideColumn(colName, table);
      }
      
      // Save preference
      savedVisibility[colName] = checkbox.checked;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(savedVisibility));
    });
  });
}

function hideColumn(colName, table) {
  // Hide all cells with this data-col attribute
  const cells = table.querySelectorAll(`th[data-col="${colName}"], td[data-col="${colName}"]`);
  console.log(`🚫 hideColumn("${colName}"): Found ${cells.length} cells`);
  cells.forEach((cell, idx) => {
    cell.classList.add("hidden");
    if (idx < 3) console.log(`   [${idx}] Added hidden class to:`, cell.tagName, cell.textContent?.substring(0, 30));
  });
}

function showColumn(colName, table) {
  // Show all cells with this data-col attribute
  const cells = table.querySelectorAll(`th[data-col="${colName}"], td[data-col="${colName}"]`);
  console.log(`✅ showColumn("${colName}"): Found ${cells.length} cells`);
  cells.forEach((cell, idx) => {
    cell.classList.remove("hidden");
    if (idx < 3) console.log(`   [${idx}] Removed hidden class from:`, cell.tagName, cell.textContent?.substring(0, 30));
  });
}

// ========== INIT ==========

document.addEventListener("DOMContentLoaded", () => {

  loadFilterOptions();

  loadOffers();

  loadSavedFilters();
  
  initializeColumnResize();
  initializeColumnToggle();

  document
    .getElementById("applyFilters")
    ?.addEventListener("click", () => {
      loadOffers(1);
    });

  // Auto-apply as soon as the user picks a value: these are discrete,
  // single-step choices (dropdown or date picker), so there is no
  // "still typing" state to debounce like with free-text fields.
  for (const field of AUTO_APPLY_ON_CHANGE_FIELDS) {
    document
      .getElementById(field)
      ?.addEventListener("change", () => {
        loadOffers(1);
      });
  }

  // Keyword is free text: apply once the user presses Enter after typing
  // a non-trivial search term, instead of on every keystroke or blur.
  document
    .getElementById("keyword")
    ?.addEventListener("keydown", (e) => {
      if (e.key !== "Enter") return;
      if (e.target.value.trim().length > 5) {
        loadOffers(1);
      }
    });

  document
    .getElementById("clearFilters")
    ?.addEventListener("click", () => {

      for (const field of filterFields) {

        const el = document.getElementById(field);

        if (el) {
          el.value = "";
        }
      }

      loadOffers(1);
    });

  document
    .getElementById("prevPage")
    ?.addEventListener("click", () => {
      if (currentPage > 1) {
        loadOffers(currentPage - 1);
      }
    });

  document
    .getElementById("nextPage")
    ?.addEventListener("click", () => {
      loadOffers(currentPage + 1);
    });

  // document
  //   .getElementById("saveFilter")
  //   ?.addEventListener("click", saveFilter);
});