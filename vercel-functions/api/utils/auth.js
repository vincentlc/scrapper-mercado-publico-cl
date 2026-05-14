// Validaciones simples para requests
const validateEmail = (email) => {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
};

const validateUserId = (userId) => {
  return userId && userId.startsWith('usr_') && userId.length > 4;
};

const validateFilterJson = (filterJson) => {
  return typeof filterJson === 'object' && filterJson !== null;
};

const validateToken = (token) => {
  return token && token.startsWith('tok_') && token.length > 4;
};

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type'
};

const handleCORS = (req, res) => {
  if (req.method === 'OPTIONS') {
    res.status(200).json({ ok: true });
    return true;
  }
  // Agregar headers CORS
  Object.keys(corsHeaders).forEach(key => {
    res.setHeader(key, corsHeaders[key]);
  });
  return false;
};

module.exports = {
  validateEmail,
  validateUserId,
  validateFilterJson,
  validateToken,
  handleCORS
};
