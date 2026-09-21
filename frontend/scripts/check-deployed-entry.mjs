import { pathToFileURL } from 'node:url';
import { requireProjectFiles } from '../src/responseValidation.js';

const safeCodes = new Set([
  'INVALID_HTTPS_ORIGIN', 'INVALID_EXPECTED_ASSET', 'HTTP_STATUS_FAILED',
  'CONTENT_TYPE_FAILED', 'RESPONSE_TOO_LARGE', 'ENTRY_ASSET_MISMATCH',
  'INVALID_SCRIPT_BODY',
]);
class EntryCheckError extends Error {}

export function formatEntryFailure(error) {
  return `DEPLOYED_ENTRY_CHECK_FAILED: ${error instanceof EntryCheckError ? error.message : 'UNKNOWN:CHECK_FAILED'}. No response body logged.`;
}

// GET allowlist only: never load the application or its automatic AI requests.
export async function checkDeployedEntry(base, expectedAsset, fetcher = fetch) {
  let stage = 'INPUT';
  let phase = 'VALIDATION';
  try {
  const origin = new URL(base);
  if (origin.protocol !== 'https:' || origin.username || origin.password ||
      origin.pathname !== '/' || origin.search || origin.hash) {
    throw new Error('INVALID_HTTPS_ORIGIN');
  }
  if (!/^\/assets\/[\w-]+\.js$/.test(expectedAsset)) {
    throw new Error('INVALID_EXPECTED_ASSET');
  }
  async function get(path, type, limit) {
    phase = 'REQUEST';
    const response = await fetcher(new URL(path, origin), {
      method: 'GET', redirect: 'error', signal: AbortSignal.timeout(30000),
    });
    phase = 'VALIDATION';
    if (response.status !== 200) throw new Error('HTTP_STATUS_FAILED');
    if (!type.test(response.headers.get('content-type') || '')) {
      throw new Error('CONTENT_TYPE_FAILED');
    }
    // Read with a cap, without logging bodies or project names.
    const reader = response.body.getReader();
    phase = 'BODY';
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
      // Cleanup must not replace the original timeout/size/read failure.
      await reader.cancel().catch(() => {});
    }
    return Buffer.concat(chunks).toString('utf8');
  }
  stage = 'HOME';
  const html = await get('/', /^text\/html\b/i, 1024 * 1024);
  phase = 'VALIDATION';
  const scripts = [...html.matchAll(/<script\b[^>]*\bsrc=["']([^"']+)["'][^>]*>/gi)];
  if (!scripts.some((match) => match[1] === expectedAsset)) {
    throw new Error('ENTRY_ASSET_MISMATCH');
  }
  stage = 'ASSET';
  const script = await get(expectedAsset, /^(?:text|application)\/javascript\b/i, 10 * 1024 * 1024);
  phase = 'VALIDATION';
  if (!script.trim() || /^\s*</.test(script)) throw new Error('INVALID_SCRIPT_BODY');
  stage = 'FILES';
  const body = await get('/api/files', /^application\/json\b/i, 10 * 1024 * 1024);
  phase = 'VALIDATION';
  const files = requireProjectFiles(JSON.parse(body));
  return { ok: true, entryAsset: expectedAsset, projectCount: files.length };
  } catch (error) {
    // Only fixed enums survive; never retain raw URL, payload, stack or cause.
    const code = safeCodes.has(error?.message) ? error.message
      : error?.name === 'TimeoutError' ? 'TIMEOUT'
      : error?.name === 'AbortError' ? 'ABORTED'
      : `${phase}_FAILED`;
    throw new EntryCheckError(`${stage}:${code}`);
  }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  try {
    console.log(JSON.stringify(await checkDeployedEntry(process.argv[2], process.argv[3])));
  } catch (error) {
    // Network errors and server payloads can contain sensitive values.
    console.error(formatEntryFailure(error));
    process.exitCode = 1;
  }
}
