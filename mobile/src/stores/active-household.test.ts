import assert from 'node:assert/strict';
import test from 'node:test';

import { useActiveHouseholdStore } from './active-household';

function resetActiveHousehold() {
  useActiveHouseholdStore.setState({ activeHouseholdId: null });
}

test('starts without an active household', () => {
  resetActiveHousehold();

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, null);
});

test('setActiveHouseholdId keeps only the identifier', () => {
  resetActiveHousehold();

  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, 'h1');
});

test('clearActiveHousehold drops the active household', () => {
  resetActiveHousehold();
  useActiveHouseholdStore.getState().setActiveHouseholdId('h1');

  useActiveHouseholdStore.getState().clearActiveHousehold();

  assert.equal(useActiveHouseholdStore.getState().activeHouseholdId, null);
});
