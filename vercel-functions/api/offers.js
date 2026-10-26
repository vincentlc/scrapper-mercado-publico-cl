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
module.exports.sortOffersByPublicationDesc = sortOffersByPublicationDesc;
