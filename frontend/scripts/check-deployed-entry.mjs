import { pathToFileURL } from 'node:url';
import { requireProjectFiles } from '../src/responseValidation.js';

// GET allowlist only: never load the application or its automatic AI requests.
export async function checkDeployedEntry(base, expectedAsset, fetcher = fetch) {
  const origin = new URL(base);
  if (origin.protocol !== 'https:' || origin.username || origin.password ||
      origin.pathname !== '/' || origin.search || origin.hash) {
    throw new Error('INVALID_HTTPS_ORIGIN');
  }
  if (!/^\/assets\/[\w-]+\.js$/.test(expectedAsset)) {
    throw new Error('INVALID_EXPECTED_ASSET');
  }
  async function get(path, type, limit) {
    const response = await fetcher(new URL(path, origin), {
      method: 'GET', redirect: 'error', signal: AbortSignal.timeout(30000),
    });
    if (response.status !== 200) throw new Error('HTTP_STATUS_FAILED');
    if (!type.test(response.headers.get('content-type') || '')) {
      throw new Error('CONTENT_TYPE_FAILED');
    }
    // Read with a cap, without logging bodies or project names.
    const reader = response.body.getReader();
    const chunks = [];
    let length = 0;
    try {
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        length += value.byteLength;
        if (length > limit) throw new Error('RESPONSE_TOO_LARGE');
        chunks.push(value);
      }
    } finally {
      await reader.cancel();
    }
    return Buffer.concat(chunks).toString('utf8');
  }
  const html = await get('/', /^text\/html\b/i, 1024 * 1024);
  const scripts = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)];
  if (!scripts.some((match) => match[1] === expectedAsset)) {
    throw new Error('ENTRY_ASSET_MISMATCH');
  }
  const script = await get(expectedAsset, /^(?:text|application)\/javascript\b/i, 10 * 1024 * 1024);
  if (!script.trim() || /^\s*</.test(script)) throw new Error('INVALID_SCRIPT_BODY');
  const body = await get('/api/files', /^application\/json\b/i, 10 * 1024 * 1024);
  const files = requireProjectFiles(JSON.parse(body));
  return { ok: true, entryAsset: expectedAsset, projectCount: files.length };
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(JSON.stringify(await checkDeployedEntry(process.argv[2], process.argv[3])));
  } catch {
    // Network errors and server payloads can contain sensitive values.
    console.error('DEPLOYED_ENTRY_CHECK_FAILED: check connectivity, expected asset and API contract. No response body logged.');
    process.exitCode = 1;
  }
}
