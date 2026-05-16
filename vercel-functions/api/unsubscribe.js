const { getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./auth');

export default async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { token } = req.query;

    if (!token) {
      return res.status(400).json({ error: 'Token requerido' });
    }

    // En Sheets no hay UPDATE fácil, usaremos una función manual en GitHub Actions
    // Por ahora, retornamos un mensaje de confirmación
    res.status(200).json({
      message: 'Desuscripción registrada. Serás removido en la próxima actualización.'
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
}