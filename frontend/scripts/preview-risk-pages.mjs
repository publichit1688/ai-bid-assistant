// Synthetic-only UI: no backend, database, AI or outbound proxy.
import { readFileSync } from 'node:fs';
import { createServer } from 'vite';

const files = ['docx', 'pdf'].map((ext, i) => ({
  id: i + 1, filename: `auth-${ext}.${ext}`, project_name: `Synthetic ${ext}`,
  filepath: `/fixture/${ext}.pdf`, score: 92, score_level: '低风险',
  risk_count: 1, middle_count: 1, high_count: 0, low_count: 0, total_deduction: 8,
  analysis: {}, risk: [{ page: ext === 'docx' ? 1 : 2, level: '中风险', deduction: 8,
    description: 'Synthetic page mapping', original_text: ext === 'docx' ? 'AUTH WORD RISK PAGE 2' : 'AUTH REGRESSION PDF RISK PAGE 2',
    highlight_words: [ext === 'docx' ? 'AUTH WORD RISK PAGE 2' : 'AUTH REGRESSION PDF RISK PAGE 2'] }],
}));
const pdfs = {
  '/fixture/docx.pdf': readFileSync(new URL('../../backend/.browser-layout-20260914/uploads/auth-word-sample.docx.preview.pdf', import.meta.url)),
  '/fixture/pdf.pdf': readFileSync(new URL('../../backend/.browser-layout-20260914/uploads/auth-sample.pdf', import.meta.url)),
};
const server = await createServer({
  define: { 'import.meta.env.VITE_API_BASE_URL': JSON.stringify('http://127.0.0.1:5176') },
  server: { host: '127.0.0.1', port: 5176, strictPort: true },
  plugins: [{ name: 'synthetic-risk-pages', configureServer(vite) {
    vite.middlewares.use((req, res, next) => {
      const path = new URL(req.url, 'http://127.0.0.1').pathname;
      if (!path.startsWith('/api/') && !path.startsWith('/fixture/')) return next();
      const send = (status, data) => { res.writeHead(status, { 'Content-Type': 'application/json' }); res.end(JSON.stringify(data)); };
      if (req.method !== 'GET') { req.resume(); return send(405, { detail: 'Read-only fixture' }); }
      if (pdfs[path]) { res.writeHead(200, { 'Content-Type': 'application/pdf' }); return res.end(pdfs[path]); }
      if (path === '/api/files') return send(200, files);
      if (path === '/api/dashboard') return send(200, { total_projects: 2, total_risks: 2, average_score: 92 });
      if (path === '/api/files/1/preview') return send(200, { pagination: 'rendered', source_format: 'docx', renderer: 'synthetic', num_pages: 2, risk_page_map: { 0: 2 }, filepath: '/fixture/docx.pdf' });
      const file = files.find(item => path === `/api/files/${item.id}`);
      return file ? send(200, file) : send(404, { detail: 'Not allowed' });
    });
  } }],
});
await server.listen();
console.log('SYNTHETIC_ONLY http://127.0.0.1:5176');
for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, async () => { await server.close(); process.exit(0); });
