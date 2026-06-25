const { v4: uuidv4 } = require('uuid');
const { appendRow, getRows } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

/**
 * API Endpoint: POST /api/subscribe
 * 
 * Permite a un usuario registrarse para recibir alertas por email.
 * 
 * Requisitos:
 * - Email válido
 * - Nombre del filtro
 * - Al menos un criterio de filtro (keyword, region, etc.)
 * 
 * Respuesta:
 * - user_id
 * - filter_id
 * - unsub_token (para desuscripción)
 * - message
 * 
 * Privacidad:
 * - Nunca expone el email del usuario
 * - Solo devuelve tokens seguros
 */
module.exports = async function handler(req, res) {
  if (handleCORS(req, res)) return;
  
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email, filter_name, ...filterCriteria } = req.body;

    // Validar email
    if (!email || !email.includes('@')) {
      return res.status(400).json({ error: 'Email inválido' });
    }

    // Validar nombre del filtro
    if (!filter_name || filter_name.trim().length < 2) {
      return res.status(400).json({ error: 'El nombre del filtro debe tener al menos 2 caracteres' });
    }

    // Validar que hay al menos un criterio de filtro
    const validCriteria = ['keyword', 'region', 'comuna', 'organismo', 'tipo_oferta', 'estado', 'monto_min', 'monto_max', 'moneda', 'utm_range'];
    const hasValidCriteria = validCriteria.some(key => {
      const value = filterCriteria[key];
      return value !== undefined && value !== null && String(value).trim() !== '';
    });
    
    if (!hasValidCriteria) {
      return res.status(400).json({ 
        error: 'Debes especificar al menos un criterio de filtro (keyword, region, comuna, organismo, tipo_oferta, etc.)' 
      });
    }

    // Verificar si el usuario ya existe
    let existingUser = null;
    try {
      const users = await getRows('users');
      if (users && users.length > 1) {
        const headers = users[0];
        const emailIndex = headers.indexOf('email');
        
        for (let i = 1; i < users.length; i++) {
          const row = users[i];
          if (row && row[emailIndex] && row[emailIndex].toLowerCase() === email.toLowerCase()) {
            existingUser = {
              user_id: row[0],
              email: row[emailIndex],
              unsub_token: row[2],
              is_active: row[3] === 'TRUE' || row[3] === true,
              created_at: row[4],
            };
            break;
          }
        }
      }
    } catch (error) {
      console.warn('No se pudo verificar usuarios existentes:', error.message);
    }

    // Crear o usar usuario existente
    let user_id, unsub_token;
    
    if (existingUser && existingUser.is_active) {
      user_id = existingUser.user_id;
      unsub_token = existingUser.unsub_token;
    } else {
      // Crear nuevo usuario
      user_id = `usr_${uuidv4().substring(0, 12)}`;
      unsub_token = `tok_${uuidv4().substring(0, 12)}`;
      const created_at = new Date().toISOString();

      await appendRow('users', [
        user_id,
        email,
        unsub_token,
        'TRUE',
        created_at,
        '',
        '',
      ]);
    }

    // Crear filtro
    const filter_id = `fil_${uuidv4().substring(0, 12)}`;
    const created_at = new Date().toISOString();
    
    // Construir fila del filtro
    const filterRow = [
      filter_id,
      user_id,
      filter_name.trim(),
      filterCriteria.keyword || '',
      filterCriteria.region || '',
      filterCriteria.comuna || '',
      filterCriteria.organismo || '',
      filterCriteria.tipo_oferta || '',
      filterCriteria.monto_min ? String(filterCriteria.monto_min) : '',
      filterCriteria.monto_max ? String(filterCriteria.monto_max) : '',
      filterCriteria.moneda || '',
      filterCriteria.estado || '',
      filterCriteria.utm_range || '',
      filterCriteria.send_frequency || 'immediate',
      'TRUE',
      created_at,
    ];

    await appendRow('user_filters', filterRow);

    res.status(201).json({
      user_id,
      filter_id,
      unsub_token,
      message: existingUser 
        ? 'Filtro de alerta creado exitosamente (usuario existente)'
        : 'Usuario y filtro de alerta creados exitosamente',
    });
  } catch (error) {
    console.error('[SUBSCRIBE] Error:', error);
    res.status(500).json({ 
      error: 'Error interno del servidor. Por favor, inténtalo de nuevo más tarde.' 
    });
  }
};
