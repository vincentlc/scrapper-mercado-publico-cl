const { getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

module.exports = async function handler(req, res) {

  if (handleCORS(req, res)) return;

  if (req.method !== 'GET') {
    return res.status(405).json({
      error: 'Method not allowed'
    });
  }

  try {

    const rows = await getRows('ofertas');

    if (!rows || rows.length === 0) {
      return res.status(200).json({
        tipo_oferta: [],
        organismo: [],
        region: [],
        comuna: []
      });
    }

    const headers = rows[0];

    const offers = rows.slice(1).map(row => {
      const obj = {};

      headers.forEach((h, i) => {
        obj[h] = row[i] || '';
      });

      return obj;
    });

    const unique = (field) => {
      return [...new Set(
        offers
          .map(o => o[field])
          .filter(v => v && v.trim() !== '')
      )].sort();
    };

    return res.status(200).json({
      tipo_oferta: unique('tipo_oferta'),
      organismo: unique('organismo'),
      region: unique('region'),
      comuna: unique('comuna'),
    });

  } catch (error) {

    console.error(error);

    return res.status(500).json({
      error: error.message
    });
  }
};