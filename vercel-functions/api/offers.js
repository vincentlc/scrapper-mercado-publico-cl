const { getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

module.exports = async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    // Parámetros de filtro
    const { keyword, estado, region, tipo_oferta } = req.query;

    // Obtener ofertas de Google Sheets
    const rows = await getRows('ofertas');
    const headers = rows[0];
    
    let offers = rows.slice(1).map(row => {
      const obj = {};
      headers.forEach((h, i) => obj[h] = row[i] || '');
      return obj;
    });

    // Aplicar filtros
    if (keyword) {
      offers = offers.filter(o => 
        o.nombre?.toLowerCase().includes(keyword.toLowerCase()) ||
        o.descripcion?.toLowerCase().includes(keyword.toLowerCase())
      );
    }
    if (estado) {
      offers = offers.filter(o => o.estado === estado);
    }
    if (region) {
      offers = offers.filter(o => o.region === region);
    }
    if (tipo_oferta) {
      offers = offers.filter(o => o.tipo_oferta === tipo_oferta);
    }

    res.status(200).json({
      count: offers.length,
      offers: offers.slice(0, 100) // Paginación: primeros 100
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
}