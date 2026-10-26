const test = require('node:test');
const assert = require('node:assert/strict');

const { parsePublicationDate, sortOffersByPublicationDesc } = require('../api/offers');

function makeOffer(overrides = {}) {
  return {
    codigo_externo: '',
    nombre: '',
    estado: '',
    fecha_publicacion: '',
    ...overrides,
  };
}

test('parsePublicationDate parses dd/mm/yyyy', () => {
  const time = parsePublicationDate('05/03/2026');
  const date = new Date(time);
  assert.equal(date.getFullYear(), 2026);
  assert.equal(date.getMonth(), 2);
  assert.equal(date.getDate(), 5);
});

test('parsePublicationDate returns null for empty or invalid values', () => {
  assert.equal(parsePublicationDate(''), null);
  assert.equal(parsePublicationDate(undefined), null);
  assert.equal(parsePublicationDate('not-a-date'), null);
  assert.equal(parsePublicationDate('31/02/2026'), null);
});

test('sortOffersByPublicationDesc orders different days newest first', () => {
  const offers = [
    makeOffer({ codigo_externo: 'A', fecha_publicacion: '01/01/2026' }),
    makeOffer({ codigo_externo: 'B', fecha_publicacion: '15/03/2026' }),
    makeOffer({ codigo_externo: 'C', fecha_publicacion: '20/02/2026' }),
  ];

  const sorted = sortOffersByPublicationDesc(offers);

  assert.deepEqual(sorted.map((o) => o.codigo_externo), ['B', 'C', 'A']);
});

test('sortOffersByPublicationDesc breaks ties on same day by row position (lower row = newer)', () => {
  const offers = [
    makeOffer({ codigo_externo: 'FIRST_ROW', fecha_publicacion: '10/05/2026' }),
    makeOffer({ codigo_externo: 'LAST_ROW', fecha_publicacion: '10/05/2026' }),
  ];

  const sorted = sortOffersByPublicationDesc(offers);

  assert.deepEqual(sorted.map((o) => o.codigo_externo), ['LAST_ROW', 'FIRST_ROW']);
});

test('sortOffersByPublicationDesc pushes empty or invalid dates to the end', () => {
  const offers = [
    makeOffer({ codigo_externo: 'EMPTY', fecha_publicacion: '' }),
    makeOffer({ codigo_externo: 'VALID', fecha_publicacion: '01/01/2026' }),
    makeOffer({ codigo_externo: 'INVALID', fecha_publicacion: 'no-date' }),
  ];

  const sorted = sortOffersByPublicationDesc(offers);

  assert.equal(sorted[0].codigo_externo, 'VALID');
  assert.deepEqual(
    new Set(sorted.slice(1).map((o) => o.codigo_externo)),
    new Set(['EMPTY', 'INVALID'])
  );
});

test('sorting applies after filtering and keeps the filtered set ordered newest first', () => {
  const offers = [
    makeOffer({ codigo_externo: 'A', estado: 'Publicada', fecha_publicacion: '01/01/2026' }),
    makeOffer({ codigo_externo: 'B', estado: 'Cerrada', fecha_publicacion: '15/03/2026' }),
    makeOffer({ codigo_externo: 'C', estado: 'Publicada', fecha_publicacion: '20/02/2026' }),
  ];

  const filtered = offers.filter((offer) => offer.estado === 'Publicada');
  const sorted = sortOffersByPublicationDesc(filtered);

  assert.deepEqual(sorted.map((o) => o.codigo_externo), ['C', 'A']);
});

test('pagination over an already sorted set keeps the sequence across pages', () => {
  const offers = Array.from({ length: 150 }, (_, i) => {
    const day = String((i % 28) + 1).padStart(2, '0');
    return makeOffer({ codigo_externo: `offer-${i}`, fecha_publicacion: `${day}/01/2026` });
  });

  const sorted = sortOffersByPublicationDesc(offers);
  const pageSize = 100;

  const page1 = sorted.slice(0, pageSize);
  const page2 = sorted.slice(pageSize, pageSize * 2);

  assert.equal(page1.length, 100);
  assert.equal(page2.length, 50);
  assert.deepEqual([...page1, ...page2], sorted);
});
