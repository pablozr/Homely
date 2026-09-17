import assert from 'node:assert/strict';
import test from 'node:test';

import {
  BRAZIL_TIMEZONES,
  defaultTimezone,
  filterBrazilTimezones,
  isBrazilTimezone,
  resolveBrazilTimezone,
  timezoneLabel,
} from './timezones';

test('catalog lists the Brazil timezones in a fixed order with human labels', () => {
  assert.deepEqual(
    BRAZIL_TIMEZONES.map((option) => option.id),
    [
      'America/Sao_Paulo',
      'America/Noronha',
      'America/Manaus',
      'America/Cuiaba',
      'America/Rio_Branco',
    ],
  );

  assert.deepEqual(
    BRAZIL_TIMEZONES.map((option) => option.label),
    [
      'São Paulo, Brasil',
      'Fernando de Noronha, Brasil',
      'Manaus, Brasil',
      'Cuiabá, Brasil',
      'Rio Branco, Brasil',
    ],
  );
});

test('timezoneLabel shows the human label instead of the raw IANA id', () => {
  assert.equal(timezoneLabel('America/Noronha'), 'Fernando de Noronha, Brasil');
  assert.equal(timezoneLabel('America/Manaus'), 'Manaus, Brasil');
});

test('isBrazilTimezone only accepts catalog ids', () => {
  for (const option of BRAZIL_TIMEZONES) {
    assert.equal(isBrazilTimezone(option.id), true);
  }

  assert.equal(isBrazilTimezone('UTC'), false);
  assert.equal(isBrazilTimezone('America/New_York'), false);
  assert.equal(isBrazilTimezone('America/Sao_Paulo '), true);
});

test('resolveBrazilTimezone matches the device timezone when it is in the catalog', () => {
  assert.equal(resolveBrazilTimezone('America/Manaus').id, 'America/Manaus');
  assert.equal(resolveBrazilTimezone('America/Rio_Branco').id, 'America/Rio_Branco');
});

test('resolveBrazilTimezone falls back to São Paulo for unknown or missing timezones', () => {
  assert.equal(resolveBrazilTimezone('Europe/London').id, 'America/Sao_Paulo');
  assert.equal(resolveBrazilTimezone('GMT').label, 'São Paulo, Brasil');
  assert.equal(resolveBrazilTimezone(undefined).id, 'America/Sao_Paulo');
  assert.equal(resolveBrazilTimezone(null).id, 'America/Sao_Paulo');
});

test('defaultTimezone always resolves to a Brazil catalog id', () => {
  const resolved = defaultTimezone();

  assert.equal(typeof resolved, 'string');
  assert.equal(isBrazilTimezone(resolved), true);
});

test('filterBrazilTimezones returns every option for an empty query', () => {
  assert.equal(filterBrazilTimezones('').length, BRAZIL_TIMEZONES.length);
  assert.equal(filterBrazilTimezones('   ').length, BRAZIL_TIMEZONES.length);
});

test('filterBrazilTimezones matches cities ignoring case and accents', () => {
  assert.deepEqual(
    filterBrazilTimezones('sao paulo').map((option) => option.id),
    ['America/Sao_Paulo'],
  );
  assert.deepEqual(
    filterBrazilTimezones('CUIABA').map((option) => option.id),
    ['America/Cuiaba'],
  );
  assert.deepEqual(
    filterBrazilTimezones('noronha').map((option) => option.id),
    ['America/Noronha'],
  );
});

test('filterBrazilTimezones matches the country name and the IANA id', () => {
  assert.equal(filterBrazilTimezones('Brasil').length, BRAZIL_TIMEZONES.length);
  assert.deepEqual(
    filterBrazilTimezones('america/manaus').map((option) => option.id),
    ['America/Manaus'],
  );
  assert.deepEqual(
    filterBrazilTimezones('rio branco').map((option) => option.id),
    ['America/Rio_Branco'],
  );
});

test('filterBrazilTimezones returns no options for an unknown query', () => {
  assert.deepEqual(filterBrazilTimezones('toquio'), []);
});
