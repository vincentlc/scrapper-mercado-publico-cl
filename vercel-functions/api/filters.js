const { v4: uuidv4 } = require('uuid');
const { appendRow, getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./auth');

export default async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method === 'POST') {
    // Crear nuevo filtro
    try {
      const { user_id, filter_name, filter_json } = req.body;

      const filter_id = `flt_${uuidv4().substring(0, 12)}`;
      const created_at = new Date().toISOString();

      await appendRow('user_filters', [
        filter_id,
        user_id,
        filter_name,
        JSON.stringify(filter_json),
        'TRUE',
        created_at,
        created_at,
        ''
      ]);

      res.status(201).json({ filter_id, message: 'Filtro creado' });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  } else if (req.method === 'GET') {
    // Obtener filtros del usuario
    try {
      const { user_id } = req.query;
      const rows = await getRows('user_filters');
      const headers = rows[0];

      const filters = rows
        .slice(1)
        .filter(row => row[1] === user_id) // user_id está en índice 1
        .map(row => {
          const obj = {};
          headers.forEach((h, i) => obj[h] = row[i] || '');
          return obj;
        });

      res.status(200).json({ filters });
    } catch (error) {
      res.status(500).json({ error: error.message });
    }
  } else {
    res.status(405).json({ error: 'Method not allowed' });
  }
}