import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { runInNewContext } from 'node:vm';
import test from 'node:test';

const source = readFileSync(new URL('../src/api.js', import.meta.url), 'utf8');
const executable = source
  .replace(/import axios from "axios";/, '')
  .replaceAll('import.meta.env', 'buildEnv')
  .replace(/export /g, '');

function resolveBase(buildEnv) {
  const interceptor = { use() {} };
  return runInNewContext(`${executable}\nAPI_BASE_URL`, {
    buildEnv,
    window: { location: { origin: 'https://bid.internal.example' } },
    axios: { create: () => ({ interceptors: { request: interceptor, response: interceptor } }) },
  });
}

test('production defaults to the same HTTPS origin when build configuration is omitted', () => {
  assert.equal(resolveBase({ PROD: true }), 'https://bid.internal.example');
});

test('local development preserves the existing backend address', () => {
  assert.equal(resolveBase({ PROD: false }), 'http://127.0.0.1:8000');
});

test('explicit API configuration wins and trailing slash is normalized', () => {
  assert.equal(resolveBase({ PROD: true, VITE_API_BASE_URL: 'https://api.internal.example/' }), 'https://api.internal.example');
});
