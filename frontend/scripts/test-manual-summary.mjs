import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import test from 'node:test';

// Execute the actual App handlers with synthetic APIs, not a copied algorithm.
const source = readFileSync(new URL('../src/App.jsx', import.meta.url), 'utf8');
const handlers = source.slice(source.indexOf('async function loadDashboard(){'), source.indexOf('function beforeUpload(file){'));
function setup() {
  const data = { total_projects: 2, total_risks: 2 };
  const state = { posts: 0, gets: 0, errors: 0, dashboard: null, summary: null };
  const context = vm.createContext({
    trendDays: 7, dashboardLoading: false, dashboardError: '', aiManagementLoading: false,
    aiSummaryCacheRef: { current: {} }, aiSummaryRequestRef: { current: 0 }, aiSummaryPendingRef: { current: false }, dashboardRequestRef: { current: 0 },
    requireObjectResponse: value => value,
    setDashboard: value => { state.dashboard = value; },
    setAiManagementSummary: value => { state.summary = value; },
    message: { error: () => { state.errors++; } },
    apiClient: {
      get: async () => { state.gets++; return { data }; },
      post: async () => { state.posts++; return { data: { success: true, summary: { overall_status: 'synthetic' } } }; },
    },
  });
  for (const [setter, key] of [['setDashboardLoading', 'dashboardLoading'], ['setDashboardError', 'dashboardError'], ['setAiManagementLoading', 'aiManagementLoading']]) {
    context[setter] = value => { context[key] = value; };
  }
  vm.runInContext(handlers, context);
  return { context, state, data };
}
test('initial load, credentials reload and period changes never POST summary', async () => {
  const { context: c, state } = setup();
  await c.loadDashboard();
  await c.loadDashboard();
  c.trendDays = 30;
  await c.loadDashboard();
  assert.equal(state.gets, 3);
  assert.equal(state.posts, 0);
  assert.equal(state.summary, null);
  assert.equal((source.match(/loadAiManagementSummary\(/g) || []).length, 2);
  assert.match(source, /onClick=\{\(\) => loadAiManagementSummary\(dashboard\)\}/);
});
test('manual request generates once and reuses matching cache', async () => {
  const { context: c, state, data } = setup();
  await c.loadDashboard();
  await c.loadAiManagementSummary(data);
  await c.loadAiManagementSummary(data);
  await c.loadDashboard();
  assert.equal(state.posts, 1);
  assert.equal(state.summary.overall_status, 'synthetic');
  c.trendDays = 30;
  await c.loadDashboard();
  assert.equal(state.summary, null);
  assert.equal(state.posts, 1);
});
test('pending request deduplicates clicks and cannot overwrite refreshed statistics', async () => {
  const { context: c, state, data } = setup();
  let resolve;
  c.apiClient.post = () => { state.posts++; return new Promise(r => { resolve = r; }); };
  const pending = c.loadAiManagementSummary(data);
  await c.loadAiManagementSummary(data);
  assert.equal(state.posts, 1);
  c.trendDays = 30;
  await c.loadDashboard();
  resolve({ data: { success: true, summary: { overall_status: 'old' } } });
  await pending;
  assert.equal(state.summary, null);
  assert.equal(c.aiManagementLoading, false);
  assert.equal(Object.keys(c.aiSummaryCacheRef.current).length, 0);
});
test('failed manual request allows explicit retry and leaves statistics intact', async () => {
  const { context: c, state, data } = setup();
  await c.loadDashboard();
  c.apiClient.post = async () => { state.posts++; throw new Error('synthetic failure'); };
  await c.loadAiManagementSummary(data);
  await c.loadAiManagementSummary(data);
  assert.equal(state.posts, 2);
  assert.equal(state.errors, 2);
  assert.equal(state.dashboard, data);
  assert.equal(c.aiSummaryPendingRef.current, false);
});
test('missing, loading or failed statistics disable manual requests', async () => {
  const { context: c, state, data } = setup();
  await c.loadAiManagementSummary(null);
  c.dashboardLoading = true;
  await c.loadAiManagementSummary(data);
  c.dashboardLoading = false;
  c.dashboardError = 'synthetic';
  await c.loadAiManagementSummary(data);
  assert.equal(state.posts, 0);
});

test('older statistics cannot overwrite newer period data or re-enable its button early', async () => {
  const { context: c, state } = setup();
  const pending = [];
  c.apiClient.get = () => new Promise(resolve => pending.push(resolve));
  const oldLoad = c.loadDashboard();
  c.trendDays = 30;
  const newLoad = c.loadDashboard();
  pending[0]({ data: { total_projects: 7 } });
  await oldLoad;
  assert.equal(c.dashboardLoading, true);
  assert.equal(state.dashboard, null);
  pending[1]({ data: { total_projects: 30 } });
  await newLoad;
  assert.equal(state.dashboard.total_projects, 30);
  assert.equal(c.dashboardLoading, false);
  assert.equal(state.posts, 0);
});

test('late statistics success or failure cannot replace a completed newer response', async () => {
  for (const fail of [false, true]) {
    const { context: c, state } = setup();
    const pending = [];
    c.apiClient.get = () => new Promise((resolve, reject) => pending.push({ resolve, reject }));
    const oldLoad = c.loadDashboard();
    c.trendDays = 30;
    const newLoad = c.loadDashboard();
    pending[1].resolve({ data: { total_projects: 30 } });
    await newLoad;
    if (fail) pending[0].reject(new Error('stale synthetic failure'));
    else pending[0].resolve({ data: { total_projects: 7 } });
    await oldLoad;
    assert.equal(state.dashboard.total_projects, 30);
    assert.equal(c.dashboardError, '');
    assert.equal(state.errors, 0);
    assert.equal(state.posts, 0);
  }
});
