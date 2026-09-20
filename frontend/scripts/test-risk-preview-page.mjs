import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { resolveRiskPreviewPage } from '../src/riskPreviewPage.js';

const source = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');
test('risk list and navigation share the rendered page resolver', () => {
  assert.ok(/第 \{resolveRiskPreviewPage\(item, index, wordPreviewRiskPages, numPages\)\} 页/.test(source));
  assert.ok(/const targetPage = resolveRiskPreviewPage\(item, index, wordPreviewRiskPages, numPages\);/.test(source));
});
test('Word rendered mapping overrides original page without mutating the risk', () => {
  const risk = Object.freeze({ page: 1 });
  assert.equal(resolveRiskPreviewPage(risk, 0, { 0: 2 }, 2), 2);
  assert.equal(resolveRiskPreviewPage(risk, 1, { 0: 2 }, 2), 1);
  assert.equal(risk.page, 1);
});
test('PDF and missing mappings keep valid original pages', () => {
  assert.equal(resolveRiskPreviewPage({ page: '2' }, 0, {}, 3), 2);
  assert.equal(resolveRiskPreviewPage({ page: 2 }, 0, null, 0), 2);
});
test('invalid pages fall back safely and navigation stays within rendered bounds', () => {
  for (const value of [0, -1, 1.5, 'bad', Infinity, null]) {
    assert.equal(resolveRiskPreviewPage({ page: 2 }, 0, { 0: value }, 3), 2);
    assert.equal(resolveRiskPreviewPage({ page: value }, 0, {}, 3), 1);
  }
  assert.equal(resolveRiskPreviewPage({ page: 1 }, 0, { 0: 9 }, 2), 2);
  assert.equal(resolveRiskPreviewPage({}, 0), 1);
});
