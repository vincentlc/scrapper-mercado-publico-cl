const test = require('node:test');
const assert = require('node:assert/strict');

const {
  parseCloseDate,
  parseIsoDateBoundary,
  parseUtmBounds,
  matchesUtmRange,
} = require('../api/offers');

test('parseCloseDate parses dd/mm/yyyy with time', () => {
  // This is the exact value that used to be mis-parsed by the frontend:
  // codigo_externo 2735-175-LE26 showed cierre 11-05-2026 instead of 05-11-2026.
  const time = parseCloseDate('05/11/2026 11:00:00');
  const date = new Date(time);
  assert.equal(date.getFullYear(), 2026);
  assert.equal(date.getMonth(), 10); // November
  assert.equal(date.getDate(), 5);
  assert.equal(date.getHours(), 11);
});

test('parseCloseDate parses dd/mm/yyyy without time', () => {
  const time = parseCloseDate('05/11/2026');
  const date = new Date(time);
  assert.equal(date.getMonth(), 10);
  assert.equal(date.getDate(), 5);
  assert.equal(date.getHours(), 0);
});

test('parseCloseDate returns null for empty or invalid values', () => {
  assert.equal(parseCloseDate(''), null);
  assert.equal(parseCloseDate(undefined), null);
  assert.equal(parseCloseDate('31/02/2026'), null);
});

test('parseIsoDateBoundary parses YYYY-MM-DD as start/end of day', () => {
  const start = new Date(parseIsoDateBoundary('2026-11-05', false));
  const end = new Date(parseIsoDateBoundary('2026-11-05', true));
  assert.equal(start.getHours(), 0);
  assert.equal(start.getMinutes(), 0);
  assert.equal(end.getHours(), 23);
  assert.equal(end.getMinutes(), 59);
});

test('parseIsoDateBoundary returns null for empty or malformed values', () => {
  assert.equal(parseIsoDateBoundary(''), null);
  assert.equal(parseIsoDateBoundary(undefined), null);
  assert.equal(parseIsoDateBoundary('05/11/2026'), null);
});

test('parseUtmBounds reads an explicit "entre X y Y UTM" range', () => {
  assert.deepEqual(
    parseUtmBounds('Licitación Pública Entre 100 y 1000 UTM (LE)'),
    { min: 100, max: 1000 }
  );
});

test('parseUtmBounds reads an explicit "igual o superior a X e inferior a Y UTM" range, with thousands separators', () => {
  assert.deepEqual(
    parseUtmBounds('Licitación Pública igual o superior a 1.000 UTM e inferior a 2.000 UTM (LP)'),
    { min: 1000, max: 2000 }
  );
});

test('parseUtmBounds reads an upper-bound-only range ("menor/inferior a X UTM")', () => {
  assert.deepEqual(
    parseUtmBounds('Licitación Pública Menor a 100 UTM (L1)'),
    { min: 0, max: 100 }
  );
});

test('parseUtmBounds reads a lower-bound-only range ("mayor a X UTM") as open-ended', () => {
  assert.deepEqual(
    parseUtmBounds('Licitación Pública Mayor a 5000 UTM'),
    { min: 5000, max: Infinity }
  );
  // The plain Mercado Público "LP" label has no upper bound in the text at
  // all - Mercado Público itself doesn't subdivide beyond ">1000 UTM".
  assert.deepEqual(
    parseUtmBounds('Licitación Pública Mayor 1000 UTM (LP)'),
    { min: 1000, max: Infinity }
  );
});

test('parseUtmBounds returns null when the string has no UTM figure', () => {
  assert.equal(parseUtmBounds('LR'), null);
  assert.equal(parseUtmBounds(''), null);
});

test('matchesUtmRange matches an explicit range only to its own bucket', () => {
  const tipo = 'Licitación Pública Entre 100 y 1000 UTM (LE)';
  assert.equal(matchesUtmRange(tipo, '100_1000'), true);
  assert.equal(matchesUtmRange(tipo, 'lt100'), false);
  assert.equal(matchesUtmRange(tipo, '1000_2000'), false);
});

test('matchesUtmRange matches an open-ended lower bound to every bucket above it (documented over-inclusion)', () => {
  const tipo = 'Licitación Pública Mayor 1000 UTM (LP)';
  assert.equal(matchesUtmRange(tipo, '1000_2000'), true);
  assert.equal(matchesUtmRange(tipo, '2000_5000'), true);
  assert.equal(matchesUtmRange(tipo, 'gt5000'), true);
  assert.equal(matchesUtmRange(tipo, 'lt100'), false);
  assert.equal(matchesUtmRange(tipo, '100_1000'), false);
});

test('matchesUtmRange excludes offers with no parseable UTM figure', () => {
  assert.equal(matchesUtmRange('LR', 'lt100'), false);
  assert.equal(matchesUtmRange('LR', 'gt5000'), false);
});

test('matchesUtmRange passes everything through when no range is given', () => {
  assert.equal(matchesUtmRange('LR', ''), true);
  assert.equal(matchesUtmRange('LR', undefined), true);
});
