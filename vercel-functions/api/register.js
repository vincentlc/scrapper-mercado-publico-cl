const { v4: uuidv4 } = require('uuid');
const { appendRow } = require('./utils/google-sheets');
const { handleCORS } = require('./utils/auth');

module.exports = async function handler(req, res) {
  if (handleCORS(req, res)) return;
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }

  try {
    const { email } = req.body;

    if (!email || !email.includes('@')) {
      return res.status(400).json({ error: 'Email inválido' });
    }

    const user_id = `usr_${uuidv4().substring(0, 12)}`;
    const unsub_token = `tok_${uuidv4().substring(0, 12)}`;
    const created_at = new Date().toISOString();

    await appendRow('users', [
      user_id,
      email,
      unsub_token,
      'TRUE',
      created_at,
      '',
      ''
    ]);

    res.status(201).json({
      user_id,
      unsub_token,
      message: 'Usuario registrado exitosamente'
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: error.message });
  }
}