const { getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

function normalizeHeader(header) {
  return String(header || '').trim().toLowerCase();
}

function formatTipoOferta(tipo) {
  const value = String(tipo || '').trim();
  if (!value) return '';
  if (value.toLowerCase().includes('inferior a 100 utm') && !value.toLowerCase().includes('(compra ágil)')) {
    return `${value} (compra ágil)`;
  }
  return value;
}

function parsePublicationDate(value) {
  const str = String(value || '').trim();
  if (!str) return null;

  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})/.exec(str);
  if (!match) return null;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);
  const date = new Date(year, month - 1, day);

  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }

  return date.getTime();
}

// Same source format as parsePublicationDate (DD/MM/YYYY, as written by
// scripts/update_offers.py:format_date_for_sheet) but fecha_cierre also
// carries a time component (DD/MM/YYYY HH:MM:SS).
function parseCloseDate(value) {
  const str = String(value || '').trim();
  if (!str) return null;

  const match = /^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2})(?::(\d{2}))?)?/.exec(str);
  if (!match) return null;

  const day = Number(match[1]);
  const month = Number(match[2]);
  const year = Number(match[3]);
  const hour = match[4] ? Number(match[4]) : 0;
  const minute = match[5] ? Number(match[5]) : 0;
  const second = match[6] ? Number(match[6]) : 0;
  const date = new Date(year, month - 1, day, hour, minute, second);

  if (
    date.getFullYear() !== year ||
    date.getMonth() !== month - 1 ||
    date.getDate() !== day
  ) {
    return null;
  }

  return date.getTime();
}

// start_date/end_date/start_close_date/end_close_date come from the
// frontend's <input type="date">, always "YYYY-MM-DD" - unambiguous, no
// locale guessing needed.
function parseIsoDateBoundary(value, endOfDay) {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || '').trim());
  if (!match) return null;

  const year = Number(match[1]);
  const month = Number(match[2]) - 1;
  const day = Number(match[3]);

  return endOfDay
    ? new Date(year, month, day, 23, 59, 59, 999).getTime()
    : new Date(year, month, day, 0, 0, 0, 0).getTime();
}

const UTM_BUCKETS = {
  lt100: [0, 100],
  '100_1000': [100, 1000],
  '1000_2000': [1000, 2000],
  '2000_5000': [2000, 5000],
  gt5000: [5000, Infinity],
};

function normalizeForUtmMatch(value) {
  return String(value || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
}

function parseUtmNumber(str) {
  return Number(str.replace(/\./g, '').replace(/,/g, '.'));
}

// Best-effort: extract the UTM bracket a tipo_oferta string describes.
// Mercado Público's own codes (L1/LE/LP) officially distinguish only
// <100 / 100-1000 / >1000 UTM - they don't subdivide further - but many
// organismos write more specific thresholds ("igual o superior a 1.000
// UTM e inferior a 2.000 UTM") that we can parse precisely. When a string
// only states a lower bound ("Mayor a 1000 UTM (LP)"), we can't know how
// far above 1000 UTM it actually is, so it's treated as matching every
// bucket from that lower bound upward. That makes the 2000-5000 and >5000
// buckets over-inclusive for plain "LP" offers - this is the best we can
// do without the offer's actual amount in UTM (monto_estimado is raw CLP
// and frequently 0/unset upstream, and converting it would need the UTM
// value for that month, which isn't tracked anywhere in this project).
function parseUtmBounds(tipoOferta) {
  const text = normalizeForUtmMatch(tipoOferta);
  if (!text.includes('utm')) return null;

  let match = /entre\s*([\d.,]+)\s*y\s*([\d.,]+)\s*utm/.exec(text);
  if (match) {
    return { min: parseUtmNumber(match[1]), max: parseUtmNumber(match[2]) };
  }

  match = /(?:igual o superior a|mayor o igual a)\s*([\d.,]+)\s*utm[^\d]*(?:inferior a|menor a)\s*([\d.,]+)\s*utm/.exec(text);
  if (match) {
    return { min: parseUtmNumber(match[1]), max: parseUtmNumber(match[2]) };
  }

  match = /(?:menor a|inferior a)\s*([\d.,]+)\s*utm/.exec(text);
  if (match) {
    return { min: 0, max: parseUtmNumber(match[1]) };
  }

  match = /(?:mayor a|superior a|mayor o igual a|igual o superior a|mayor)\s*([\d.,]+)\s*utm/.exec(text);
  if (match) {
    return { min: parseUtmNumber(match[1]), max: Infinity };
  }

  return null;
}

function matchesUtmRange(tipoOferta, rangeKey) {
  const bucket = UTM_BUCKETS[rangeKey];
  if (!bucket) return true;

  const bounds = parseUtmBounds(tipoOferta);
  if (!bounds) return false;

  // Half-open interval overlap: [bounds.min, bounds.max) vs [bucket[0], bucket[1])
  return bounds.min < bucket[1] && bucket[0] < bounds.max;
}

function sortOffersByPublicationDesc(offers) {
  return offers
    .map((offer, idx) => ({ offer, idx, time: parsePublicationDate(offer.fecha_publicacion) }))
    .sort((a, b) => {
      const aValid = a.time !== null;
      const bValid = b.time !== null;
      if (aValid !== bValid) return aValid ? -1 : 1;
      if (aValid && a.time !== b.time) return b.time - a.time;
      return b.idx - a.idx;
    })
    .map((entry) => entry.offer);
}

function rowToOffer(headers, row) {
  const obj = {};
  headers.forEach((header, index) => {
    obj[normalizeHeader(header)] = row[index] || '';
  });

  const dias = obj.dias_que_quedan || obj.dias_para_cierre || '';

  return {
    codigo_externo: obj.codigo_externo || '',
    nombre: obj.nombre || '',
    descripcion: obj.descripcion || '',
    descripcion_producto: obj.descripcion_producto || '',
    organismo: obj.organismo || '',
    estado: obj.estado || '',
    region: obj.region || '',
    comuna: obj.comuna || '',
    tipo_oferta: obj.tipo_oferta || '',
    tipo_oferta_formateado: formatTipoOferta(obj.tipo_oferta),
    moneda: obj.moneda || '',
    monto_estimado: obj.monto_estimado || '',
    fecha_publicacion: obj.fecha_publicacion || '',
    fecha_cierre: obj.fecha_cierre || '',
    link: obj.link || '',
    raw_json: obj.raw_json || '',
    dias_para_cierre: dias,
    dias_que_quedan: dias,
  };
}

async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const {
      keyword,
      estado,
      region,
      tipo_oferta,
      organismo,
      comuna,
      utm_range,
      start_date,
      end_date,
      start_close_date,
      end_close_date,
      min_days_to_close,
      max_days_to_close,
      page = '1',
      page_size = '100',
    } = req.query;

    const rows = await getRows('ofertas');
    if (!rows || rows.length === 0) {
      return res.status(200).json({
        items: [],
        total: 0,
        page: Number(page) || 1,
        page_size: Number(page_size) || 100,
      });
    }

    const headers = rows[0];
    let offers = rows.slice(1).map((row) => rowToOffer(headers, row));

    if (keyword) {
      const q = keyword.toLowerCase();
      offers = offers.filter((offer) =>
        [offer.nombre, offer.descripcion, offer.descripcion_producto, offer.codigo_externo]
          .some((field) => String(field).toLowerCase().includes(q))
      );
    }
    if (estado) {
      offers = offers.filter((offer) => offer.estado === estado);
    }
    if (region) {
      offers = offers.filter((offer) => offer.region === region);
    }
    if (tipo_oferta) {
      offers = offers.filter((offer) => offer.tipo_oferta === tipo_oferta);
    }
    if (organismo) {
      offers = offers.filter((offer) => offer.organismo === organismo);
    }
    if (comuna) {
      offers = offers.filter((offer) => offer.comuna === comuna);
    }
    if (utm_range) {
      offers = offers.filter((offer) => matchesUtmRange(offer.tipo_oferta, utm_range));
    }

    const startDateTs = parseIsoDateBoundary(start_date, false);
    if (startDateTs !== null) {
      offers = offers.filter((offer) => {
        const t = parsePublicationDate(offer.fecha_publicacion);
        return t !== null && t >= startDateTs;
      });
    }
    const endDateTs = parseIsoDateBoundary(end_date, true);
    if (endDateTs !== null) {
      offers = offers.filter((offer) => {
        const t = parsePublicationDate(offer.fecha_publicacion);
        return t !== null && t <= endDateTs;
      });
    }
    const startCloseTs = parseIsoDateBoundary(start_close_date, false);
    if (startCloseTs !== null) {
      offers = offers.filter((offer) => {
        const t = parseCloseDate(offer.fecha_cierre);
        return t !== null && t >= startCloseTs;
      });
    }
    const endCloseTs = parseIsoDateBoundary(end_close_date, true);
    if (endCloseTs !== null) {
      offers = offers.filter((offer) => {
        const t = parseCloseDate(offer.fecha_cierre);
        return t !== null && t <= endCloseTs;
      });
    }

    const minDays = min_days_to_close !== undefined && min_days_to_close !== '' ? Number(min_days_to_close) : null;
    if (minDays !== null && !Number.isNaN(minDays)) {
      offers = offers.filter((offer) => {
        const d = Number(offer.dias_para_cierre);
        return !Number.isNaN(d) && d >= minDays;
      });
    }
    const maxDays = max_days_to_close !== undefined && max_days_to_close !== '' ? Number(max_days_to_close) : null;
    if (maxDays !== null && !Number.isNaN(maxDays)) {
      offers = offers.filter((offer) => {
        const d = Number(offer.dias_para_cierre);
        return !Number.isNaN(d) && d <= maxDays;
      });
    }

    offers = sortOffersByPublicationDesc(offers);

    const pageNumber = Math.max(1, Number(page) || 1);
    const pageSize = Math.min(200, Math.max(1, Number(page_size) || 100));
    const total = offers.length;
    const start = (pageNumber - 1) * pageSize;
    const items = offers.slice(start, start + pageSize);

    return res.status(200).json({
      items,
      total,
      page: pageNumber,
      page_size: pageSize,
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
}

module.exports = handler;
module.exports.parsePublicationDate = parsePublicationDate;
module.exports.parseCloseDate = parseCloseDate;
module.exports.parseIsoDateBoundary = parseIsoDateBoundary;
module.exports.parseUtmBounds = parseUtmBounds;
module.exports.matchesUtmRange = matchesUtmRange;
module.exports.sortOffersByPublicationDesc = sortOffersByPublicationDesc;
