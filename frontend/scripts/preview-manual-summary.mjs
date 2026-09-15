// Isolated UI fixture: no backend, database, credentials or outbound requests.
import { createServer } from 'vite';

const dashboard = {
  total_projects: 2, total_risks: 2, average_score: 86,
  risk_distribution: { high: 1, medium: 1, low: 0 },
  score_distribution: [], period_comparison: {}, attention_projects: [],
  recent_projects: [], trend: [],
};
let requests = 0;
const server = await createServer({
  define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://127.0.0.1:5175') },
  server: { host: '127.0.0.1', port: 5175, strictPort: true },
  plugins: [{
    name: 'isolated-summary-fixture',
    configureServer(vite) {
      vite.middlewares.use((req, res, next) => {
        const path = new URL(req.url, 'http://127.0.0.1').pathname;
        if (!path.startsWith('/api/') && path !== '/fixture-status') return next();
        const send = (status, data) => {
          res.writeHead(status, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify(data));
        };
        if (path === '/fixture-status') return send(200, { summaryRequests: requests });
        if (req.method === 'GET' && path === '/api/files') return send(200, []);
        if (req.method === 'GET' && path === '/api/dashboard') return send(200, dashboard);
        if (req.method === 'POST' && path === '/api/dashboard/ai-summary') {
          requests++;
          const attempt = requests;
          req.resume();
          // First request fails for retry verification; subsequent calls succeed.
          setTimeout(() => send(attempt === 1 ? 502 : 200, attempt === 1
            ? { detail: 'Synthetic retry fixture' }
            : { success: true, summary: {
              overall_status: '合成摘要：仅用于本地验收', risk_change: '合成风险变化',
              key_attention: '合成关注点', management_advice: '合成建议',
            } }), 2000);
          return;
        }
        return send(404, { detail: 'Fixture route not allowed' });
      });
    },
  }],
});
await server.listen();
console.log('SYNTHETIC_ONLY http://127.0.0.1:5175; first summary fails, retry succeeds');
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.once(signal, async () => { await server.close(); process.exit(0); });
}
