# P6 维护候选边界审计

更新时间：2026-09-05

状态：P6-01至P6-07累积成果的代码、数据、版本与回滚边界已完成审计；经项目负责人授权统一提升为 `1.5.1-rc.1`，完整候选门禁通过并建立本地原子候选提交。未推送、打标签或部署。

## 基线身份

- 当前分支：`main`。
- 当前HEAD：`a4295e60cc5dd8a9e4f2a45a8c362db5867e15f6`。
- `v1.5.0` 是annotated tag，标签对象为 `8095a315b8c171b6be3fe6fd01abfc361c705986`，解引用后指向当前HEAD `a4295e60cc5dd8a9e4f2a45a8c362db5867e15f6`。
- 候选基线父提交为正式发布HEAD `a4295e60cc5dd8a9e4f2a45a8c362db5867e15f6`。
- 根版本、FastAPI版本契约和前端包/锁文件已统一为 `1.5.1-rc.1`；既有 `v1.5.0` 标签未修改。
- 最终候选提交为 `814c4bf8be0198d0e48b1d93ee3bb035bfb93700`（短哈希 `814c4bf`），提交说明为 `perf(maintenance): establish v1.5.1-rc.1 candidate`。

## 候选范围

审计完成前共有11个已跟踪修改文件和6个未跟踪源码/文档文件；加上本审计文档和4个版本同步文件，最终候选共22个文件。

### 后端与测试

- `backend/app/api/dashboard.py`：修复多项目Dashboard只聚合最后一条项目的数据一致性问题。
- `backend/scripts/prepare_auth_regression.py`：增强纯合成Dashboard、PDF、Word和工作台隔离夹具。
- `backend/tests/test_core_api.py`：增加Dashboard多项目一致性回归。
- `backend/tests/test_frontend_branding.py`：保护项目列表、懒加载边界和ECharts模块注册。
- `backend/tests/test_frontend_preview_boundary.py`：保护Blob、PDF/Word预览、响应式宽度、风险页映射与高亮边界。
- `backend/tests/test_version.py`：锁定根版本、FastAPI及前端包/锁文件均为 `1.5.1-rc.1`。

### 前端运行代码

- `frontend/src/App.jsx`：原生项目列表、工作台/图表/预览懒加载及原有状态协调。
- `frontend/src/pages/WorkbenchPage.jsx`：智能编标工作台展示与人工操作页面。
- `frontend/src/components/DashboardChart.jsx`：ECharts模块化图表适配器。
- `frontend/src/components/DocumentPreview.jsx`：PDF/Word纯展示与组件内响应式宽度观察。

### 文档

- `CHANGELOG.md`
- `TASKS.md`
- `TESTING.md`
- `docs/ACTIVE_TASK.md`
- `docs/PROJECT_STATE.md`
- `docs/ROADMAP.md`
- `docs/FRONTEND_BUNDLE_AUDIT.md`
- `docs/DOCUMENT_PREVIEW_BOUNDARY_AUDIT.md`
- `docs/P6_MAINTENANCE_CANDIDATE_AUDIT.md`

### 版本文件

- `VERSION`
- `frontend/package.json`
- `frontend/package-lock.json`

## 明确排除

以下路径由Git忽略规则保护，且当前跟踪文件中没有业务数据库、上传件、报告、真实回归样本、依赖或构建产物：

- 根目录与后端真实 `.env`；只允许跟踪不含真实凭据的 `.env.example`。
- `backend/bid.db`、`backend/uploads/`、`backend/reports/`。
- `backend/regression_samples/` 及授权原件。
- `frontend/node_modules/`、`frontend/dist/`。
- pytest、浏览器回归和依赖审计的临时目录。

秘密扫描只报告规则与位置，完整门禁未发现高置信度凭据。候选暂存后再次检查了暂存文件清单、差异格式和秘密扫描，未包含真实凭据或用户数据。

## 完整门禁

`scripts/verify_release.ps1` 已从仓库根目录端到端通过：

- Python `compileall`：通过。
- 后端完整回归：177 passed、1 skipped；跳过项为当前Windows无符号链接权限。
- 秘密扫描：通过。
- Python依赖审计：0个已知漏洞。
- 前端ESLint：通过。
- 前端生产构建：通过。
- 前端生产依赖审计：0个已知漏洞。
- 构建保留585.56 kB Dashboard图表块提醒，不提高阈值。

P6-03、P6-04、P6-05和P6-07均另有隔离浏览器证据，覆盖工作台、Dashboard图表与预警穿透、PDF/Word预览和ECharts模块化。隔离AI使用非真实测试Key和不可达本机地址，未连接真实DeepSeek。

## 原子提交与回滚边界

P6-01至P6-07在数据流和构建边界上互相关联：组件抽离需要入口修改和契约测试，Dashboard聚合修复需要合成夹具及接口测试。因此按授权作为一个维护候选原子提交，不拆成缺少配套测试或文档的零散提交。

签署前只读复核已确认候选身份、22个文件、版本、标签和数据排除边界；项目负责人已签署候选提交 `814c4bf`，验收记录见 `docs/V1_5_1_ACCEPTANCE_SIGNOFF.md`。若候选需要回滚，应在干净边界上使用 `git revert 814c4bf` 生成可审计反向提交，不使用 `git reset --hard`，也不删除数据库、上传文件或报告。正式版本提升、标签、推送和部署均需要另行明确授权。
