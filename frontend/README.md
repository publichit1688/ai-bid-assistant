# AI标书助手前端

本目录是AI标书助手的React/Vite前端，使用Ant Design、ECharts和react-pdf。V1以招标文件分析、风险定位、项目管理、项目对比和报告导出为核心，不在Dashboard继续扩展新模块。

## 本地启动

先按仓库根目录 `TESTING.md` 启动FastAPI后端，再执行：

```powershell
npm ci
npm run dev -- --host 127.0.0.1
```

默认后端地址为 `http://127.0.0.1:8000`。隔离或部署验证可通过 `VITE_API_BASE_URL` 覆盖；不要把共享访问密钥或任何API Key写入前端环境变量、源码或构建产物。

## 验证

```powershell
npm run lint
npm run build
npm audit --omit=dev --audit-level=low
```

完整候选版本检查从仓库根目录执行 `scripts/verify_release.ps1`。PDF worker位于 `public/pdf.worker.min.mjs`，属于PDF预览运行依赖，不得作为模板资源删除。
