import assert from 'node:assert/strict';
import test from 'node:test';

import { api } from './client';

test('returns the health response', async (context) => {
  const fetchMock = context.mock.method(globalThis, 'fetch', async () =>
    new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
  );

  assert.deepEqual(await api.health(), { status: 'ok' });
  assert.equal(fetchMock.mock.callCount(), 1);
});

test('rejects non-success responses', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 503 }));

  await assert.rejects(api.health(), /API request failed: 503/);
});
