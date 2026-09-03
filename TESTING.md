# 开发与回归测试

## 环境准备

要求：Python 3.11+、Node.js 20+；DOC/DOCX 版式预览需要 Microsoft Word 或 WPS Office。默认顺序是 Microsoft Word 主用、WPS 备用；非标准安装位置可在 `.env` 中用 `MICROSOFT_WORD_PATH` 或 `WPS_OFFICE_PATH` 指向对应可执行文件。不要把真实 Key 写入命令、截图或提交记录。

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item ..\.env.example .env
```

只在本机 `.env` 中填写 `DEEPSEEK_API_KEY`。随后安装前端依赖：

本地默认配置保持 `sqlite:///./bid.db`、`uploads`、`reports` 以及两个 5173 开发来源。部署或隔离测试可在进程环境或 `.env` 中覆盖：

```dotenv
DATABASE_URL=sqlite:///./bid.db
UPLOAD_DIR=uploads
REPORT_DIR=reports
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
UPLOAD_MAX_BYTES=52428800
DEEPSEEK_MODEL=
DEEPSEEK_TIMEOUT_SECONDS=60
AUTH_MODE=disabled
APP_ACCESS_TOKEN=
```

相对路径以启动后端时的当前目录为基准；生产环境建议使用明确的持久化路径。`CORS_ORIGINS` 使用英文逗号分隔，不要加入末尾斜杠，也不要在生产环境使用通配符。

`UPLOAD_MAX_BYTES` 按真实上传字节数限制单文件，默认 50 MiB；超过上限返回 `413 / UPLOAD_TOO_LARGE`，且不会进入解析、OCR、Office 转换或 AI。`DEEPSEEK_MODEL` 留空时保留各调用链现有默认模型，填写后统一覆盖；`DEEPSEEK_TIMEOUT_SECONDS` 默认 60 秒。生产反向代理的请求体上限应不高于应用上限。

```powershell
cd ..\frontend
npm ci
```

## 启动

后端命令必须在 `backend` 目录执行，以保持当前 SQLite 和 uploads 相对路径一致：

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

生产式启动不使用 reload。先检查数据库和持久化目录，再启动：

```powershell
cd backend
.\.venv\Scripts\python.exe scripts\start_production.py --check
.\.venv\Scripts\python.exe scripts\start_production.py
```

生产入口读取 `APP_HOST`、`APP_PORT`、`APP_WORKERS` 和 `APP_LOG_LEVEL`；SQLite及当前Office自动化架构默认保持单worker。详细说明见 `docs/DEPLOYMENT.md`。

本地开发保持 `AUTH_MODE=disabled`。部署启用共享密钥时设置 `AUTH_MODE=shared_token` 和至少32位的随机 `APP_ACCESS_TOKEN`；不要把真实值写入命令历史或截图。前端通过顶部“设置访问凭据”在当前页面内存启用，刷新后需重新输入；隔离全链路回归完成前不得在业务环境启用。

类生产验证必须使用隔离数据库、上传目录、报告目录和未占用端口；依次请求 `/`、`/api/health`、`/api/health/ready`、`/api/files`，最后正常停止进程。不得为了测试覆盖当前 `.env` 或连接用户 `bid.db`。

共享鉴权回归可用 `backend/scripts/prepare_auth_regression.py <全新临时目录>` 创建纯合成SQLite、PDF及预生成Word预览夹具。脚本拒绝覆盖已有目录，不包含密钥；密钥只在启动进程环境中设置。回归结束必须正常停止前后端，不得把临时夹具当作业务数据。

隔离启动不能用空字符串覆盖AI配置，因为配置模块会继续读取本机 `.env`。必须同时设置非空测试Key和不可达的本机测试端点，例如 `DEEPSEEK_API_KEY=auth-regression-disabled`、`DEEPSEEK_BASE_URL=http://127.0.0.1:9`，确保Dashboard自动摘要不会调用真实模型。

创建运行数据快照时在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe scripts\backup_runtime.py <全新的备份目录>
.\.venv\Scripts\python.exe scripts\restore_runtime.py <备份目录> <不存在的恢复目录>
```

脚本仅支持持久化SQLite。备份目标和恢复目标只要已存在就拒绝覆盖；恢复前校验清单路径、文件集合、逐文件SHA-256和SQLite完整性，全部复制校验成功后才原子生成目标目录。恢复结果保持 `database/bid.db`、`uploads/`、`reports/` 结构；部署人员应在隔离目录核验后再通过环境变量切换，禁止对运行中的真实目录原位恢复。

新终端启动前端：

```powershell
cd frontend
npm run dev -- --host 127.0.0.1
```

## 每批最低验证

```powershell
cd frontend
npm run lint
npm run build
```

```powershell
cd backend
.\.venv\Scripts\python.exe -m compileall -q app
.\.venv\Scripts\python.exe -m pytest
```

V1候选版本发布前，在仓库根目录执行统一自动入口：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\verify_release.ps1
```

该入口包含联网依赖审计；完整人工门禁见 `docs/V1_RELEASE_CHECKLIST.md`。自动入口通过不等于正式发布。

若尚无 pytest 用例，至少启动 FastAPI 并验证：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/
Invoke-RestMethod http://127.0.0.1:8000/api/health
Invoke-RestMethod http://127.0.0.1:8000/api/health/ready
Invoke-RestMethod http://127.0.0.1:8000/api/files
Invoke-RestMethod 'http://127.0.0.1:8000/api/dashboard?days=7'
```

当前已建立 pytest 用例，正常开发应优先运行 `python -m pytest`。测试夹具会在 pytest 临时目录创建独立 `bid.db` 和 `uploads/`，不得改成复用 `backend/bid.db`。

Windows 公共 Temp 曾出现 pytest 目录权限拒绝，因此 `backend/pytest.ini` 已将临时根固定为已忽略的 `backend/.pytest-tmp/`，并关闭非必要的 pytest 缓存写入。

## V1 核心回归清单

- [ ] Dashboard 可加载；周期切换、图表和空数据状态正确。
- [ ] 点击 Dashboard 预警项目可进入对应项目，并展开风险检查器。
- [ ] 项目中心搜索、风险筛选、选择项目、加入/取消对比正常。
- [ ] PDF 使用响应式页面预览；DOCX/DOC 显示由 Microsoft Word（主）或 WPS Office（备用）转换的“Word 版式预览”，页数与转换 PDF 一致，每页下方显示当前页码和总页数。
- [ ] 新上传 DOCX/DOC 的分析和风险定位使用转换后的真实页；点击风险可切换到对应页，并高亮能在原文中命中的风险词。
- [ ] 电子 PDF 不调用 OCR；扫描页仅在显式启用百度 OCR 后识别，并保留原 PDF 页码。
- [ ] 未配置百度凭据时扫描 PDF 返回明确提示且不残留上传文件；超过 OCR 页数上限时不产生云调用。
- [ ] 使用授权脱敏扫描样本核对百度额度消耗、OCR 正文、风险页码和风险跳页；不把样本或响应正文提交 Git。
- [ ] 重新分析扫描 PDF 后点击风险，核对含位置 OCR 高亮框；在左右侧栏折叠和不同 PDF 宽度下保持对齐。
- [ ] PDF 随左/右侧栏收起展开自动调整，无横向溢出或遮挡。
- [ ] 点击风险可跳转正确页码，并高亮来自原文的关键词。
- [ ] 风险详情、数量、等级、扣分与项目卡片/Dashboard 一致。
- [ ] 两项目对比可生成共同风险、独有风险、推荐结果和 AI 摘要。
- [ ] 风险报告和项目对比报告可下载、打开，内容对应当前项目。
- [ ] 同一 Dashboard 数据重复请求可命中 AI 缓存；数据变化后不误用旧缓存。
- [ ] 缺少 Key、AI 超时/非法 JSON、损坏文件和空历史数据有明确提示，不破坏已有数据。
- [ ] 损坏 PDF、损坏 DOCX 和不支持扩展名分别返回明确422/415，且上传目录、预览文件和数据库无残留。
- [ ] 扩展名与声明 MIME 不一致、伪造 PDF/DOCX/DOC 文件头分别返回明确415；空 MIME或`application/octet-stream`仍需通过真实签名与结构解析，失败不调用Office/OCR/AI且无残留。
- [ ] 含 `../`、反斜杠或绝对路径的上传文件名只能保存为上传根目录内的安全文件名；异常历史数据库路径不得生成公开地址、触发Word转换或删除目录外文件。
- [ ] 正常请求响应包含安全的 `X-Request-ID`；访问日志是单行JSON，不包含查询参数、上传文件名、正文、API Key、Bearer令牌或完整异常，数字资源ID应被占位符替换。
- [ ] 上传与AI高成本接口超过配置窗口后返回 `429 / RATE_LIMITED`、`Retry-After` 和请求ID；健康、历史读取及静态预览不受限。默认忽略伪造转发头，只有可信直接代理可提供限流身份。
- [ ] 共享模式下无凭据访问业务API、`/uploads/*`和就绪探针返回401，根接口及存活探针可访问，文档入口关闭；正确凭据可访问全部受保护入口且响应继续携带请求ID。
- [ ] 凭据仅在前端内存中存在；刷新后需重新输入，不能出现在源码、构建产物、URL、localStorage、日志或错误响应中。PDF、Word转换预览和两类报告下载都必须携带同一Authorization Header。

## 发布前安全扫描

联网环境中先安装独立审计工具，再扫描当前 Python 环境和前端生产锁文件：

```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements-audit.txt
.\.venv\Scripts\python.exe -m pip_audit --local --progress-spinner off --cache-dir .pytest-pip-audit-cache
.\.venv\Scripts\python.exe scripts\scan_secrets.py

cd ..\frontend
npm audit --omit=dev --audit-level=low
```

秘密扫描只覆盖受控源码、测试、部署模板和文档，明确不读取本地 `.env`、数据库、上传件、报告、真实回归样本、`node_modules` 和构建产物。命中时只显示相对路径、行号和规则名，不输出匹配内容。任何扫描失败都必须先分级、修复或记录有证据的例外，不能带入发布批次。

## 真实标书测试纪律

仅使用已授权样本。测试记录用脱敏编号，不提交 PDF/DOCX 原件、个人信息、数据库和生成报告。发现回归失败时，保存最小脱敏证据和复现步骤，先修复再推进下一任务。

样本台账、预期模板和结果模板位于 `docs/regression/`；真实原件只能放在已忽略的 `regression_samples/`。授权状态不是“已确认”时禁止执行。

## 最近一次 V1 UI 回归

2026-08-29 已完成 P0-06，浏览器和接口证据记录在 `docs/V1_UI_REGRESSION.md`。完整 AI 对比和当前 Dashboard 指纹缓存命中因会产生真实模型调用而未执行；这两项不伪造通过，将分别在 P1-03/P1-05 使用可控替身验证。
