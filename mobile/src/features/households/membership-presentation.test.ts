import assert from 'node:assert/strict';
import test from 'node:test';

import { membershipRoleLabel } from './membership-presentation';

test('membershipRoleLabel maps the raw roles to the canonical friendly copy', () => {
  assert.equal(membershipRoleLabel('OWNER'), 'Responsável');
  assert.equal(membershipRoleLabel('MEMBER'), 'Morador');
});

test('membershipRoleLabel falls back to Morador for unknown roles', () => {
  assert.equal(membershipRoleLabel('GUEST'), 'Morador');
  assert.equal(membershipRoleLabel(''), 'Morador');
});
