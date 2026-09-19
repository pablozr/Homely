import assert from 'node:assert/strict';
import test from 'node:test';

import {
  composeDueLocal,
  formatDueAt,
  isValidDateText,
  isValidDueLocal,
  isValidTimeText,
  normalizeDefaultDueTime,
  splitDueLocal,
} from './date-time';

test('accepts valid display dates and rejects impossible ones', () => {
  assert.equal(isValidDateText('20/01/2026'), true);
  assert.equal(isValidDateText('29/02/2024'), true);
  assert.equal(isValidDateText('29/02/2026'), false);
  assert.equal(isValidDateText('31/04/2026'), false);
  assert.equal(isValidDateText('00/01/2026'), false);
  assert.equal(isValidDateText('2026-01-20'), false);
});

test('accepts valid clock times only', () => {
  assert.equal(isValidTimeText('00:00'), true);
  assert.equal(isValidTimeText('23:59'), true);
  assert.equal(isValidTimeText('24:00'), false);
  assert.equal(isValidTimeText('20:60'), false);
  assert.equal(isValidTimeText('8:00'), false);
});

test('composes a civil due_local without going through Date', () => {
  assert.equal(composeDueLocal('20/01/2026', '20:00'), '2026-01-20T20:00');
  assert.equal(composeDueLocal('', ''), null);
  assert.equal(composeDueLocal('', '20:00'), null);
  assert.equal(composeDueLocal('31/02/2026', '20:00'), null);
  assert.equal(composeDueLocal('20/01/2026', '99:99'), null);
  assert.equal(isValidDueLocal('2026-01-20T20:00'), true);
  assert.equal(isValidDueLocal('2026-01-20'), false);
});

test('splits a civil due_local back into display inputs', () => {
  assert.deepEqual(splitDueLocal('2026-01-20T08:05'), { date: '20/01/2026', time: '08:05' });
  assert.deepEqual(splitDueLocal(null), { date: '', time: '' });
  assert.deepEqual(splitDueLocal('not-a-date'), { date: '', time: '' });
});

test('normalizes the household default due time', () => {
  assert.equal(normalizeDefaultDueTime('20:00:00'), '20:00');
  assert.equal(normalizeDefaultDueTime('08:30'), '08:30');
  assert.equal(normalizeDefaultDueTime(''), '20:00');
  assert.equal(normalizeDefaultDueTime('99:99'), '20:00');
});

test('formats due_at in pt-BR within the household timezone', () => {
  const formatted = formatDueAt('2026-01-20T23:00:00+00:00', 'America/Sao_Paulo');

  assert.equal(formatted.includes('20/01/2026'), true);
  assert.equal(formatted.includes('20:00'), true);
  assert.equal(formatDueAt('not-a-date', 'America/Sao_Paulo'), '');
});
