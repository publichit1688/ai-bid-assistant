# V1候选版本 Git 基线审计

审计日期：2026-09-03
候选版本：`1.0.0-rc.1`
审计性质：先完成只读盘点；用户于2026-09-03明确授权创建本地候选提交，不授权推送、恢复或标签操作。

## 当前仓库事实

- 当前分支为 `main`，HEAD与 `origin/main` 同为 `82f3383`。
- 历史只有2个提交；HEAD只跟踪 `.gitignore`、`LICENSE`、`README.md` 和 `backend/main.py`。
- 工作区快照有127个未跟踪、但未被忽略的文件；另有 `.gitignore` 修改和 `backend/main.py` 删除。
- 旧 `backend/main.py` 只有171字节、10行和1个路由；当前 `backend/app/main.py` 约2905字符并装配7组路由。现有测试、生产启动脚本及文档均以 `app.main:app` 为入口，因此删除旧入口是迁移结果，不应恢复。
- Git全历史只有9个对象，高置信度令牌/私钥格式扫描为0命中。
- 未跟踪文件中唯一超过1 MiB的是 `frontend/public/pdf.worker.min.mjs`（1,369,805字节）；它是前端PDF预览运行依赖，应保留而不是视为用户上传件。

## 建议纳入候选基线

- 根治理与发布文件：`AGENTS.md`、`VERSION`、`.env.example`、`CHANGELOG.md`、`SECURITY.md`、`TASKS.md`、`TESTING.md`及状态/路线图入口。
- 后端：`backend/app/`、`backend/scripts/`、`backend/tests/`、`pytest.ini`和两份依赖清单。
- 前端：`package.json`、`package-lock.json`、Vite/ESLint配置、`index.html`、`src/`实际引用代码和样式、`public/pdf.worker.min.mjs`及当前引用的favicon。
- 部署：Nginx、systemd、Windows启动/服务模板。
- 文档：`docs/`中的架构契约、部署说明、授权回归脱敏证据、冻结回归、发布清单和发布说明草案。
- Git变更：保留 `.gitignore` 的数据/密钥/缓存边界，并记录删除旧 `backend/main.py`。

## 不得纳入候选基线

- `.env`、`backend/.env`及任何真实API Key。
- `backend/bid.db*`、`backend/uploads/`、`backend/reports/`。
- `regression_samples/`中的授权原件、转换PDF、完整模型响应和本地结果。
- `frontend/node_modules/`、`frontend/dist/`、pytest临时目录、审计缓存、日志和生成报告。
- `docs/regression/*.local.json`与 `*.local.csv`。

上述路径均已通过 `git check-ignore -v` 验证受忽略规则保护；当前未跟踪候选列表未发现用户数据库、上传件、报告、真实样本或 `.env`。

## 发布前清理项（已完成）

以下5个未跟踪模板文件没有被当前应用引用，已在P4-01第四小批处理：

- `frontend/README.md`：已改写为AI标书助手实际启动与验证说明。
- `frontend/public/icons.svg`：已删除。
- `frontend/src/assets/hero.png`：已删除。
- `frontend/src/assets/react.svg`：已删除。
- `frontend/src/assets/vite.svg`：已删除。

`frontend/index.html` 已切换为 `zh-CN`、AI标书助手标题、描述和主题色；favicon已替换为项目自有SVG。品牌契约测试锁定上述状态，PDF worker保留。

## 建议提交方案

由于当前Git历史没有保存中间开发阶段，而现工作区已经作为一个整体完成138项后端测试、前端构建、安全扫描和隔离浏览器回归，用户已授权在模板清理完成后创建一个原子候选基线提交：

```text
chore(release): establish AI Bid Assistant v1.0.0-rc.1 baseline
```

该提交应同时包含新前后端、测试、部署文档、`.gitignore`和旧入口删除，保证检出任一提交都不会处于“只有前端”或“只有后端”的不可运行状态。提交前必须再次核对 `git status --short`、秘密扫描及统一发布检查结果。本次授权仅允许 `git add` 和一次本地 `git commit`；不执行 `git push` 或创建 `v1.0.0` 标签。

## 回滚依据

- 代码回滚点：候选基线提交的父提交 `82f3383`，但该父提交只有最小示例后端，不能作为业务可用版本。
- 数据回滚：只使用经清单和哈希验证、恢复到全新目录的快照；不得用Git操作覆盖数据库、上传件或报告。
- 正式V1发布后，应把最终提交ID、版本文件、依赖锁、备份清单哈希和部署配置项名称登记到发布记录中。
