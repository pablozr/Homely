import assert from 'node:assert/strict';
import test, { type TestContext } from 'node:test';

import { ApiError, getErrorMessage, request } from './client';
import { API_URL } from './config';

type CapturedRequest = {
  url: string;
  init?: RequestInit;
};

function mockFetch(context: TestContext, body: unknown, status = 200) {
  const calls: CapturedRequest[] = [];

  context.mock.method(globalThis, 'fetch', async (...args: Parameters<typeof fetch>) => {
    calls.push({ url: String(args[0]), init: args[1] });
    return new Response(JSON.stringify(body), { status });
  });

  return calls;
}

test('rejects non-success responses', async (context) => {
  context.mock.method(globalThis, 'fetch', async () => new Response(null, { status: 503 }));

  await assert.rejects(request('/health'), /API request failed: 503/);
});

test('exposes status and the string detail of a 422 response', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(JSON.stringify({ detail: 'Invalid Idempotency-Key header' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
  );

  await assert.rejects(request('/households', { method: 'POST' }), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 422);
    assert.equal(error.message, 'Invalid Idempotency-Key header');
    return true;
  });
});

test('uses the first message of a FastAPI array detail on 422', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(
        JSON.stringify({
          detail: [
            {
              loc: ['body', 'name'],
              msg: 'String should have at most 255 characters',
              type: 'string_too_long',
            },
            { loc: ['body', 'timezone'], msg: 'Invalid timezone', type: 'value_error' },
          ],
        }),
        { status: 422, headers: { 'Content-Type': 'application/json' } },
      ),
  );

  await assert.rejects(request('/households', { method: 'POST' }), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 422);
    assert.equal(error.message, 'String should have at most 255 characters');
    return true;
  });
});

test('falls back without leaking an unknown error body', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () =>
      new Response(JSON.stringify({ message: 'internal secret' }), {
        status: 422,
        headers: { 'Content-Type': 'application/json' },
      }),
  );

  await assert.rejects(request('/households', { method: 'POST' }), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 422);
    assert.equal(error.message, 'API request failed: 422');
    assert.equal(error.message.includes('internal secret'), false);
    return true;
  });
});

test('falls back when the error body is not JSON', async (context) => {
  context.mock.method(
    globalThis,
    'fetch',
    async () => new Response('<html>gateway</html>', { status: 502 }),
  );

  await assert.rejects(request('/households'), (error: unknown) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 502);
    assert.equal(error.message, 'API request failed: 502');
    return true;
  });
});

test('getErrorMessage prefers a non-empty Error message and falls back otherwise', () => {
  assert.equal(getErrorMessage(new ApiError(422, 'detalhe real'), 'fallback'), 'detalhe real');
  assert.equal(getErrorMessage(new Error('   '), 'fallback'), 'fallback');
  assert.equal(getErrorMessage('boom', 'fallback'), 'fallback');
  assert.equal(getErrorMessage(null, 'fallback'), 'fallback');
});

test('serializes the body, forwards the token and returns the parsed JSON', async (context) => {
  const calls = mockFetch(context, { status: 'ok' });

  const response = await request<{ status: string }>('/thing', {
    method: 'POST',
    body: { name: 'Casa' },
    token: 'access-1',
  });

  assert.equal(calls[0].url, `${API_URL}/thing`);
  assert.equal(calls[0].init?.method, 'POST');

  const headers = calls[0].init?.headers as Record<string, string>;
  assert.equal(headers['Content-Type'], 'application/json');
  assert.equal(headers.Authorization, 'Bearer access-1');
  assert.deepEqual(JSON.parse(String(calls[0].init?.body)), { name: 'Casa' });
  assert.deepEqual(response, { status: 'ok' });
});
