import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { systemApi } from './api';

test('returns the health response', async (context: TestContext) => {
  const fetchMock = context.mock.method(
    globalThis,
    'fetch',
    async () => new Response(JSON.stringify({ status: 'ok' }), { status: 200 }),
  );

  assert.deepEqual(await systemApi.health(), { status: 'ok' });
  assert.equal(fetchMock.mock.callCount(), 1);
});
