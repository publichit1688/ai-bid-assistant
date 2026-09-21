import assert from 'node:assert/strict';
import test from 'node:test';
import { applyPreviewTextHighlight } from '../src/previewTextHighlight.js';
import { readFileSync } from 'node:fs';

function layer(text) {
    const names = new Set();
    const span = { textContent: text, classList: {
        add: (...values) => values.forEach((v) => names.add(v)),
        remove: (...values) => values.forEach((v) => names.delete(v)),
    }};
    return { names, querySelectorAll: () => [span] };
}
const risk = { page: 1, level: '中', highlight_words: ['RISK'] };
test('replacement text layer receives mapped Word highlight after resize', () => {
    const before = layer('WORD RISK');
    const after = layer('WORD RISK');
    applyPreviewTextHighlight(before, risk, 2, 2);
    applyPreviewTextHighlight(after, risk, 2, 2);
    assert.ok(before.names.has('highlight-middle'));
    assert.ok(after.names.has('highlight-middle'));
    applyPreviewTextHighlight(after, risk, 1, 2);
    assert.equal(after.names.size, 0);
});
test('risk changes and invalid keywords clear stale highlight without touching other layers', () => {
    const current = layer('RISK');
    const other = layer('RISK');
    applyPreviewTextHighlight(current, risk, 1);
    applyPreviewTextHighlight(current, { ...risk, level: '高' }, 1);
    assert.deepEqual([...current.names], ['highlight-high']);
    assert.equal(other.names.size, 0);
    applyPreviewTextHighlight(current, { ...risk, highlight_words: [null, {}, ''] }, 1);
    assert.equal(current.names.size, 0);
});
test('preview reapplies highlight on text-layer render and active selection changes', () => {
    const source = readFileSync(new URL('../src/components/DocumentPreview.jsx', import.meta.url), 'utf8');
    assert.match(source, /onRenderTextLayerSuccess=\{refreshTextHighlight\}/);
    assert.match(source, /useEffect\(refreshTextHighlight,\[refreshTextHighlight\]\)/);
});
