import assert from 'node:assert/strict';
import test from 'node:test';
import { checkDeployedEntry } from './check-deployed-entry.mjs';

const origin = 'https://example.test';
const asset = '/assets/index-test.js';
function fixture(overrides = {}) {
  const calls = [];
  const responses = {
    '/': ['<script type="module" src="/assets/index-test.js"></script>', 'text/html'],
    [asset]: ['console.log("synthetic")', 'text/javascript'],
    '/api/files': ['[{"id":1}]', 'application/json'],
    ...overrides,
  };
  const fetcher = async (url, options) => {
    assert.equal(options.method, 'GET');
    assert.equal(options.redirect, 'error');
    assert.equal(url.origin, origin);
    calls.push(url.pathname);
    const [body, type, status = 200] = responses[url.pathname];
    return new Response(body, { status, headers: { 'content-type': type } });
  };
  return { calls, fetcher };
}
test('only requests root, pinned script and history; reports count without data', async () => {
  const f = fixture();
  assert.deepEqual(await checkDeployedEntry(origin, asset, f.fetcher), {
    ok: true, entryAsset: asset, projectCount: 1,
  });
  assert.deepEqual(f.calls, ['/', asset, '/api/files']);
});
test('rejects stale HTML before requesting any asset or API', async () => {
  const f = fixture({ '/': ['<script src="/assets/old.js"></script>', 'text/html'] });
  await assert.rejects(checkDeployedEntry(origin, asset, f.fetcher), /ENTRY_ASSET_MISMATCH/);
  assert.deepEqual(f.calls, ['/']);
});
test('rejects HTML fallbacks, invalid rows and HTTP failures', async () => {
  for (const value of [['<html>private</html>', 'text/html'], ['[null]', 'application/json'],
    ['{}', 'application/json'], ['not-json', 'application/json'], ['[]', 'application/json', 401]]) {
    await assert.rejects(checkDeployedEntry(origin, asset, fixture({ '/api/files': value }).fetcher));
  }
});
test('rejects invalid or HTML script bodies and oversized response', async () => {
  for (const body of ['', '<html>fallback</html>', 'x'.repeat(10 * 1024 * 1024 + 1)]) {
    await assert.rejects(checkDeployedEntry(origin, asset, fixture({ [asset]: [body, 'text/javascript'] }).fetcher));
  }
});
test('rejects credentials, alternate routes and non-HTTPS before network', async () => {
  for (const base of ['http://example.test', 'https://user:secret@example.test', `${origin}/api`, `${origin}/?token=secret`]) {
    const f = fixture();
    await assert.rejects(checkDeployedEntry(base, asset, f.fetcher));
    assert.equal(f.calls.length, 0);
  }
  await assert.rejects(checkDeployedEntry(origin, 'https://other.test/a.js'));
});
