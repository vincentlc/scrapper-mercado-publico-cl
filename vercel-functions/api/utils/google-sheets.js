const { google } = require('googleapis');

const getSheets = async () => {
  const auth = new google.auth.GoogleAuth({
    credentials: JSON.parse(
      Buffer.from(process.env.GOOGLE_SERVICE_ACCOUNT_JSON, 'base64').toString()
    ),
    scopes: ['https://www.googleapis.com/auth/spreadsheets']
  });

  const sheets = google.sheets({ version: 'v4', auth });
  return sheets;
};

const appendRow = async (sheetName, values) => {
  const sheets = await getSheets();
  await sheets.spreadsheets.values.append({
    spreadsheetId: process.env.GOOGLE_SHEETS_ID,
    range: `${sheetName}!A:Z`,
    valueInputOption: 'RAW',
    resource: { values: [values] }
  });
  invalidateRows(sheetName);
};

// Vercel serverless functions reuse the same warm container across nearby
// invocations, so this module-level cache survives between requests hitting
// the same instance. A full sheet read (values.get) is the expensive part
// of every /api/offers and /api/filters call, and the sheet itself only
// changes when the scraper's scheduled workflow runs (see
// .github/workflows/update-offers.yml) - not on every page view - so a
// short TTL trades a few seconds of staleness for far fewer Sheets API
// reads, which matters now that the frontend auto-applies filters.
const CACHE_TTL_MS = Number(process.env.SHEETS_CACHE_TTL_MS) || 30000;
const rowsCache = new Map(); // sheetName -> { data, expiresAt }

const invalidateRows = (sheetName) => {
  rowsCache.delete(sheetName);
};

const getRows = async (sheetName, query = '') => {
  const cached = rowsCache.get(sheetName);
  if (cached && cached.expiresAt > Date.now()) {
    return cached.data;
  }

  const sheets = await getSheets();
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId: process.env.GOOGLE_SHEETS_ID,
    range: `${sheetName}!A:Z`
  });
  const data = response.data.values || [];

  rowsCache.set(sheetName, { data, expiresAt: Date.now() + CACHE_TTL_MS });

  return data;
};

module.exports = { getSheets, appendRow, getRows, invalidateRows };
