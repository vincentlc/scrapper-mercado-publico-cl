const { getRows, getSheets } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

/**
 * API Endpoint: GET /api/unsubscribe
 * 
 * Permite a un usuario desuscribirse de alertas usando su token.
 * 
 * Query params:
 * - token: Token de desuscripción (requerido)
 * - filter_id: (opcional) Si se proporciona, solo elimina ese filtro específico
 * 
 * Respuesta:
 * - message: Mensaje de confirmación
 * 
 * Privacidad:
 * - Nunca expone el email del usuario
 * - Usa solo tokens seguros
 * 
 * Comportamiento:
 * - Si se proporciona filter_id: elimina solo ese filtro
 * - Si no se proporciona filter_id: marca al usuario como inactivo (desuscripción total)
 */
module.exports = async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method !== 'GET') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { token, filter_id } = req.query;

    if (!token) {
      return res.status(400).json({ error: 'Token requerido' });
    }

    const sheets = await getSheets();
    const spreadsheetId = process.env.GOOGLE_SHEETS_ID;

    if (filter_id) {
      // Eliminar solo un filtro específico
      const userFilters = await getRows('user_filters');
      
      if (userFilters && userFilters.length > 1) {
        const headers = userFilters[0];
        const filterIdIndex = headers.indexOf('filter_id');
        const userIdIndex = headers.indexOf('user_id');
        const isActiveIndex = headers.indexOf('is_active');
        
        // Buscar el filtro
        let targetRow = null;
        let targetRowIndex = null;
        
        for (let i = 1; i < userFilters.length; i++) {
          const row = userFilters[i];
          if (row && row[filterIdIndex] && row[filterIdIndex] === filter_id) {
            // Verificar que el token del usuario coincide
            const userId = row[userIdIndex];
            
            // Obtener el usuario para verificar el token
            const users = await getRows('users');
            if (users && users.length > 1) {
              const userHeaders = users[0];
              const userTokenIndex = userHeaders.indexOf('unsub_token');
              const userIdColIndex = userHeaders.indexOf('user_id');
              
              for (let j = 1; j < users.length; j++) {
                const userRow = users[j];
                if (userRow && userRow[userIdColIndex] && userRow[userIdColIndex] === userId) {
                  if (userRow[userTokenIndex] && userRow[userTokenIndex] === token) {
                    targetRow = row;
                    targetRowIndex = i + 1; // +1 porque la fila 1 es el header
                    break;
                  }
                }
              }
            }
            
            if (targetRow) break;
          }
        }
        
        if (targetRow && targetRowIndex) {
          // Marcar el filtro como inactivo
          const newRow = [...targetRow];
          newRow[isActiveIndex] = 'FALSE';
          
          await sheets.spreadsheets.values.update({
            spreadsheetId,
            range: `user_filters!A${targetRowIndex}:Z${targetRowIndex}`,
            valueInputOption: 'RAW',
            resource: { values: [newRow] },
          });
          
          return res.status(200).json({
            message: 'Filtro eliminado exitosamente',
            filter_id,
          });
        } else {
          return res.status(404).json({ error: 'Filtro no encontrado o token inválido' });
        }
      }
    } else {
      // Desuscripción total: marcar usuario como inactivo
      const users = await getRows('users');
      
      if (users && users.length > 1) {
        const headers = users[0];
        const tokenIndex = headers.indexOf('unsub_token');
        const isActiveIndex = headers.indexOf('is_active');
        
        let targetRow = null;
        let targetRowIndex = null;
        
        for (let i = 1; i < users.length; i++) {
          const row = users[i];
          if (row && row[tokenIndex] && row[tokenIndex] === token) {
            targetRow = row;
            targetRowIndex = i + 1;
            break;
          }
        }
        
        if (targetRow && targetRowIndex) {
          const newRow = [...targetRow];
          newRow[isActiveIndex] = 'FALSE';
          
          await sheets.spreadsheets.values.update({
            spreadsheetId,
            range: `users!A${targetRowIndex}:Z${targetRowIndex}`,
            valueInputOption: 'RAW',
            resource: { values: [newRow] },
          });
          
          return res.status(200).json({
            message: 'Desuscripción exitosa. No recibirás más alertas.',
          });
        } else {
          return res.status(404).json({ error: 'Token no encontrado' });
        }
      }
    }

    return res.status(400).json({ error: 'Acción no válida' });
  } catch (error) {
    console.error('[UNSUBSCRIBE] Error:', error);
    res.status(500).json({ 
      error: 'Error interno del servidor. Por favor, inténtalo de nuevo más tarde.' 
    });
  }
};