import assert from 'node:assert/strict';
import test from 'node:test';

import { buildInviteMessage, buildWhatsAppShareUrl } from './invite-sharing';

const input = {
  fullname: 'Ada',
  householdName: 'Casa da Praia',
  inviteUrl: 'https://homely.app/invite/abc123',
};

test('buildInviteMessage composes the deterministic invite copy', () => {
  assert.equal(
    buildInviteMessage(input),
    'Ada convidou você para entrar em “Casa da Praia” no Homely.\n\nhttps://homely.app/invite/abc123',
  );
});

test('buildInviteMessage keeps the exact invite URL as the only payload', () => {
  const message = buildInviteMessage({
    fullname: 'Bia',
    householdName: 'Apto 42',
    inviteUrl: 'https://homely.app/invite/segredo',
  });

  assert.equal(
    message,
    'Bia convidou você para entrar em “Apto 42” no Homely.\n\nhttps://homely.app/invite/segredo',
  );
});

test('buildWhatsAppShareUrl percent-encodes the full invite message', () => {
  const message = buildInviteMessage(input);

  assert.equal(
    buildWhatsAppShareUrl(message),
    `https://wa.me/?text=${encodeURIComponent(message)}`,
  );
  assert.equal(
    buildWhatsAppShareUrl(message),
    'https://wa.me/?text=Ada%20convidou%20voc%C3%AA%20para%20entrar%20em%20%E2%80%9CCasa%20da%20Praia%E2%80%9D%20no%20Homely.%0A%0Ahttps%3A%2F%2Fhomely.app%2Finvite%2Fabc123',
  );
});
