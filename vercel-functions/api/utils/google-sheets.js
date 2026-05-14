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
};

const getRows = async (sheetName, query = '') => {
  const sheets = await getSheets();
  const response = await sheets.spreadsheets.values.get({
    spreadsheetId: process.env.GOOGLE_SHEETS_ID,
    range: `${sheetName}!A:Z`
  });
  return response.data.values || [];
};

module.exports = { getSheets, appendRow, getRows };