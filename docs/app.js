// ========== CONFIGURACIÓN ==========
const API_BASE = "https://scrapper-mercado-publico-cl.vercel.app";

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
        <td colspan="8" style="text-align:center;padding:24px;color:#999;">
          Sin resultados
        </td>
      </tr>
    `;

    return;
  }

  for (const offer of offers) {

    // ===== TABLE =====

    const row = document.createElement("tr");

    row.innerHTML = `
      <td>${escapeHtml(offer.codigo_externo)}</td>
      <td>${escapeHtml(offer.nombre)}</td>
      <td>${renderExpandableText(offer.descripcion)}</td>
      <td>${renderExpandableText(offer.descripcion_producto)}</td>
      <td>${escapeHtml(offer.organismo)}</td>
      <td>${escapeHtml(offer.tipo_oferta)}</td>
      <td>${escapeHtml(offer.region)}</td>
      <td>${escapeHtml(offer.fecha_publicacion)}</td>
    `;

    tbody.appendChild(row);

    // ===== MOBILE CARDS =====

    const card = document.createElement("div");

    card.className = "offer-card";

    card.innerHTML = `
      <h3>${escapeHtml(offer.nombre)}</h3>

      <p>
        <strong>Código:</strong>
        ${escapeHtml(offer.codigo_externo)}
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
        ${escapeHtml(offer.tipo_oferta)}
      </p>

      <p>
        <strong>Publicación:</strong>
        ${escapeHtml(offer.fecha_publicacion)}
      </p>

      <p>
        <strong>Cierre:</strong>
        ${escapeHtml(offer.fecha_cierre)}
      </p>

      ${
        offer.link
          ? `
            <a href="${offer.link}" target="_blank">
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

async function loadOffers(page = 1) {

  try {

    const filters = getFiltersFromForm();

    const params = new URLSearchParams({
      ...filters,
      page,
      page_size: 100,
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


    renderOffers(data.offers || []);

  } catch (err) {

    console.error("Error loading offers:", err);

  }
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

  loadOffers();
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

// ========== INIT ==========

document.addEventListener("DOMContentLoaded", () => {

  loadFilterOptions();

  loadOffers();

  loadSavedFilters();

  document
    .getElementById("applyFilters")
    ?.addEventListener("click", () => {
      loadOffers();
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

      loadOffers();
    });

  // document
  //   .getElementById("saveFilter")
  //   ?.addEventListener("click", saveFilter);
});