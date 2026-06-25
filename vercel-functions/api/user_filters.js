const { getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

/**
 * API Endpoint: GET /api/user_filters
 * 
 * Permite a un usuario listar sus filtros de alerta usando su token.
 * 
 * Query params:
 * - token: Token del usuario (requerido)
 * 
 * Respuesta:
 * - user_id
 * - email (solo parcialmente mostrado por privacidad)
 * - filters: array de filtros
 * 
 * Privacidad:
 * - El email solo se muestra parcialmente (ej: u***@dominio.com)
 * - Solo se devuelven filtros activos del usuario
 */

function maskEmail(email) {
  if (!email || !email.includes('@')) return '';
  const [local, domain] = email.split('@');
  if (local.length <= 1) return email;
  return `${local[0]}***@${domain}`;
}

module.exports = async function handler(req, res) {
  if (handleCORS(req, res)) return;
  
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { token } = req.query;

    if (!token) {
      return res.status(400).json({ error: 'Token requerido' });
    }

    // Obtener usuarios para encontrar el user_id asociado al token
    let user = null;
    try {
      const users = await getRows('users');
      if (users && users.length > 1) {
        const headers = users[0];
        const tokenIndex = headers.indexOf('unsub_token');
        const userIdIndex = headers.indexOf('user_id');
        const emailIndex = headers.indexOf('email');
        const isActiveIndex = headers.indexOf('is_active');
        
        for (let i = 1; i < users.length; i++) {
          const row = users[i];
          if (row && row[tokenIndex] && row[tokenIndex] === token) {
            user = {
              user_id: row[userIdIndex],
              email: row[emailIndex],
              is_active: row[isActiveIndex] === 'TRUE' || row[isActiveIndex] === true,
            };
            break;
          }
        }
      }
    } catch (error) {
      console.error('Error al obtener usuarios:', error.message);
    }

    if (!user) {
      return res.status(404).json({ error: 'Token no encontrado' });
    }

    if (!user.is_active) {
      return res.status(400).json({ error: 'Usuario inactivo' });
    }

    // Obtener filtros del usuario
    let filters = [];
    try {
      const userFilters = await getRows('user_filters');
      if (userFilters && userFilters.length > 1) {
        const headers = userFilters[0];
        const userIdIndex = headers.indexOf('user_id');
        const filterIdIndex = headers.indexOf('filter_id');
        const filterNameIndex = headers.indexOf('filter_name');
        const keywordIndex = headers.indexOf('keyword');
        const regionIndex = headers.indexOf('region');
        const comunaIndex = headers.indexOf('comuna');
        const organismoIndex = headers.indexOf('organismo');
        const tipoOfertaIndex = headers.indexOf('tipo_oferta');
        const estadoIndex = headers.indexOf('estado');
        const montoMinIndex = headers.indexOf('monto_min');
        const montoMaxIndex = headers.indexOf('monto_max');
        const monedaIndex = headers.indexOf('moneda');
        const utmRangeIndex = headers.indexOf('utm_range');
        const isActiveIndex = headers.indexOf('is_active');
        const createdAtIndex = headers.indexOf('created_at');
        
        for (let i = 1; i < userFilters.length; i++) {
          const row = userFilters[i];
          if (row && row[userIdIndex] && row[userIdIndex] === user.user_id) {
            const isActive = row[isActiveIndex] === 'TRUE' || row[isActiveIndex] === true;
            if (isActive) {
              filters.push({
                filter_id: row[filterIdIndex] || '',
                filter_name: row[filterNameIndex] || '',
                keyword: row[keywordIndex] || '',
                region: row[regionIndex] || '',
                comuna: row[comunaIndex] || '',
                organismo: row[organismoIndex] || '',
                tipo_oferta: row[tipoOfertaIndex] || '',
                estado: row[estadoIndex] || '',
                monto_min: row[montoMinIndex] ? Number(row[montoMinIndex]) : null,
                monto_max: row[montoMaxIndex] ? Number(row[montoMaxIndex]) : null,
                moneda: row[monedaIndex] || '',
                utm_range: row[utmRangeIndex] || '',
                created_at: row[createdAtIndex] || '',
              });
            }
          }
        }
      }
    } catch (error) {
      console.error('Error al obtener filtros:', error.message);
    }

    res.status(200).json({
      user_id: user.user_id,
      email: maskEmail(user.email),
      is_active: user.is_active,
      filters_count: filters.length,
      filters,
    });
  } catch (error) {
    console.error('[USER_FILTERS] Error:', error);
    res.status(500).json({ 
      error: 'Error interno del servidor' 
    });
  }
};
