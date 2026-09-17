import assert from 'node:assert/strict';
import test from 'node:test';

import { fullnameSchema } from './schemas';

test('trims a valid fullname', () => {
  const parsed = fullnameSchema.safeParse('  Ada Lovelace  ');

  assert.equal(parsed.success, true);
  if (parsed.success) {
    assert.equal(parsed.data, 'Ada Lovelace');
  }
});

test('rejects an empty or whitespace-only fullname', () => {
  assert.equal(fullnameSchema.safeParse('').success, false);
  assert.equal(fullnameSchema.safeParse('   ').success, false);
});

test('rejects a fullname longer than 255 characters', () => {
  assert.equal(fullnameSchema.safeParse('a'.repeat(256)).success, false);
  assert.equal(fullnameSchema.safeParse('a'.repeat(255)).success, true);
});
