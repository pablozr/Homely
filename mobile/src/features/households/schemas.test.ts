import assert from 'node:assert/strict';
import test from 'node:test';

import { householdFormSchema } from './schemas';

test('trims a valid household form', () => {
  const parsed = householdFormSchema.safeParse({
    name: '  Casa da Praia  ',
    timezone: '  America/Sao_Paulo  ',
  });

  assert.equal(parsed.success, true);
  if (parsed.success) {
    assert.deepEqual(parsed.data, {
      name: 'Casa da Praia',
      timezone: 'America/Sao_Paulo',
    });
  }
});

test('rejects an empty name or timezone', () => {
  assert.equal(householdFormSchema.safeParse({ name: '   ', timezone: 'UTC' }).success, false);
  assert.equal(householdFormSchema.safeParse({ name: 'Casa', timezone: '   ' }).success, false);
});

test('rejects a timezone outside the Brazil catalog', () => {
  assert.equal(householdFormSchema.safeParse({ name: 'Casa', timezone: 'UTC' }).success, false);
  assert.equal(
    householdFormSchema.safeParse({ name: 'Casa', timezone: 'America/New_York' }).success,
    false,
  );
});

test('rejects a name longer than 255 characters', () => {
  assert.equal(
    householdFormSchema.safeParse({ name: 'a'.repeat(256), timezone: 'America/Sao_Paulo' }).success,
    false,
  );
  assert.equal(
    householdFormSchema.safeParse({ name: 'a'.repeat(255), timezone: 'America/Sao_Paulo' }).success,
    true,
  );
});
