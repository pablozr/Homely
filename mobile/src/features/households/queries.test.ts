import assert from 'node:assert/strict';
import test from 'node:test';

import type { HouseholdSummary } from './types';
import { mergeHousehold, resolveActiveHouseholdId, upsertHouseholdsResponse } from './queries';

function household(id: string, name: string): HouseholdSummary {
  return {
    id,
    name,
    timezone: 'America/Sao_Paulo',
    default_due_time: '20:00:00',
    role: 'OWNER',
    joined_at: '2026-01-01T00:00:00+00:00',
    created_at: '2026-01-01T00:00:00+00:00',
  };
}

test('resolveActiveHouseholdId returns null without households', () => {
  assert.equal(resolveActiveHouseholdId({ households: [], selected_household_id: null }), null);
});

test('resolveActiveHouseholdId activates the only household automatically', () => {
  const only = household('h1', 'Casa');

  assert.equal(resolveActiveHouseholdId({ households: [only], selected_household_id: null }), 'h1');
  assert.equal(
    resolveActiveHouseholdId({ households: [only], selected_household_id: 'other' }),
    'h1',
  );
});

test('resolveActiveHouseholdId prefers the backend selection when there are several', () => {
  const first = household('h1', 'Casa 1');
  const second = household('h2', 'Casa 2');

  assert.equal(
    resolveActiveHouseholdId({
      households: [first, second],
      selected_household_id: 'h2',
    }),
    'h2',
  );
  assert.equal(
    resolveActiveHouseholdId({
      households: [first, second],
      selected_household_id: null,
    }),
    'h1',
  );
  assert.equal(
    resolveActiveHouseholdId({
      households: [first, second],
      selected_household_id: 'missing',
    }),
    'h1',
  );
});

test('mergeHousehold appends new households and sets the selection', () => {
  const first = household('h1', 'Casa 1');
  const second = household('h2', 'Casa 2');

  const merged = mergeHousehold({ households: [first], selected_household_id: 'h1' }, second, 'h2');

  assert.deepEqual(merged.households, [first, second]);
  assert.equal(merged.selected_household_id, 'h2');
});

test('mergeHousehold replaces an existing household without duplicating it', () => {
  const first = household('h1', 'Casa 1');
  const renamed = { ...first, name: 'Casa Renomeada' };

  const merged = mergeHousehold(
    { households: [first], selected_household_id: 'h1' },
    renamed,
    'h1',
  );

  assert.equal(merged.households.length, 1);
  assert.equal(merged.households[0].name, 'Casa Renomeada');
});

test('upsertHouseholdsResponse keeps the response envelope', () => {
  const first = household('h1', 'Casa 1');

  const empty = upsertHouseholdsResponse(undefined, first, 'h1');

  assert.equal(empty.message, '');
  assert.deepEqual(empty.data.households, [first]);

  const updated = upsertHouseholdsResponse(
    { message: 'ok', data: { households: [], selected_household_id: null } },
    first,
    'h1',
  );

  assert.equal(updated.message, 'ok');
  assert.equal(updated.data.selected_household_id, 'h1');
});
