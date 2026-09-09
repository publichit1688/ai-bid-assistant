# AI标书助手 1.5.2-rc.1 腾讯云候选门禁方案

日期：2026-09-09

状态：已执行并通过。候选通过临时 COS 单对象中转至腾讯云隔离目录，组合门禁全部通过；临时对象及空桶已删除，候选目录保留，正式 `v1.5.1` 与数据目录未改动。

## 目标与边界

- 只验证已签署候选提交 `e4cf9dd10bad4ef257fd92206dcdce582b2edc74`。
- 不修改云端正式检出目录 `C:\AI-Bid-Assistant`，不移动或创建标签，不推送 GitHub。
- 不创建生产配置、数据目录或服务，不启动应用，不调用 DeepSeek、百度 OCR 或 WPS。
- 全部测试在新的隔离目录执行；失败立即停止，不进入正式版本提升或部署。

## 推荐交付方式

使用本地 Git bundle 传输完整、可校验的仓库历史。bundle 可包含签署文档提交，但云端必须显式检出候选代码提交 `e4cf9dd`，不能测试当前 `main`。

选择 Git bundle 的原因：

- 不需要把候选推送到 GitHub，也不创建候选标签。
- 云端可以先执行 SHA-256 与 `git bundle verify`，再在独立目录检出精确提交。
- 不覆盖云端正式目录和现有 `.venv`，失败后可删除整个隔离目录，不影响 `v1.5.1`。

候选包不得包含 `.env`、数据库、上传文件、报告、真实标书、`node_modules`、`dist` 或本机虚拟环境。创建前必须先运行仓库秘密扫描并确认工作区干净。

## 本地制包与校验

在仓库根目录执行，输出路径使用新的临时目录：

```powershell
.\backend\.venv\Scripts\python.exe backend\scripts\scan_secrets.py
git status --short
git rev-parse 'e4cf9dd^{commit}'
git bundle create <临时目录>\ai-bid-assistant-1.5.2-rc.1.bundle main
git bundle verify <临时目录>\ai-bid-assistant-1.5.2-rc.1.bundle
Get-FileHash -Algorithm SHA256 <临时目录>\ai-bid-assistant-1.5.2-rc.1.bundle
```

必须记录 bundle 的字节数和 SHA-256，不把临时下载地址、签名参数或任何凭据写入仓库。

## 云端隔离检出

候选包到达云服务器后，先核对固定 SHA-256，再执行：

```powershell
$candidateRoot = 'C:\AI-Bid-Gate\1.5.2-rc.1'
git bundle verify '<候选包绝对路径>'
git clone --branch main --no-checkout '<候选包绝对路径>' $candidateRoot
git -C $candidateRoot checkout --detach e4cf9dd10bad4ef257fd92206dcdce582b2edc74
git -C $candidateRoot status --short
git -C $candidateRoot rev-parse HEAD
Get-Content -LiteralPath "$candidateRoot\VERSION"
```

继续门禁的前置条件：HEAD 精确等于 `e4cf9dd10bad4ef257fd92206dcdce582b2edc74`、工作区为空、版本为 `1.5.2-rc.1`。任何一项不符均停止。

## 云端候选门禁

候选目录使用自己的 `.venv` 和前端依赖，不复用或修改正式目录依赖。环境变量须显式使用非空测试 Key 与不可达本机模型地址，避免读取服务器上可能存在的真实配置。

门禁顺序：

1. 安装后端和前端依赖。
2. 运行 Python 编译与秘密扫描。
3. 优先运行 `backend/tests/test_backup_runtime.py::test_backup_refuses_overwrite_and_symlinks`，确认 System 账户下不再跳过且通过。
4. 运行完整后端 pytest；预期至少保持候选基线 `177 passed`，符号链接用例不得跳过。
5. 运行前端 `npm run lint` 和 `npm run build`。
6. 联网依赖审计作为独立门禁运行；网络失败必须记录为未完成，不能当作通过。
7. 复核 `C:\AI-Bid-Assistant` 的 HEAD、版本和工作区未发生变化。

候选门禁不启动 Uvicorn/Vite，不创建 `C:\AI-Bid-Data`，也不执行真实文件分析。

## 传输授权边界

当前签署已授权执行腾讯云候选门禁，但没有授权推送或部署。实际传输仍需选择并授权一种通道：

- 推荐：临时 COS 对象中转，使用固定 SHA-256，门禁完成后删除对象和空桶；如果需要临时公有读，必须再次明确授权且只公开单个 bundle 对象。
- 备选：腾讯云自动化助手的文件分发能力；仅在控制台确认可用且不会把凭据写入命令日志时使用。

在传输通道获明确授权前，只保留本方案，不上传候选包、不操作云服务器。

## 通过条件与后续决策

只有以下条件全部满足，才可报告云端候选门禁通过：

- bundle 哈希、Git 校验和候选提交身份一致；
- System 账户符号链接回归通过且没有残留目标；
- 完整后端回归、前端 lint/build 和秘密扫描通过；
- 正式 `v1.5.1` 检出、生产数据和服务保持未修改；
- 临时传输对象及候选目录的保留或清理状态有明确记录。

门禁通过仍不等于正式发布；提升 `1.5.2`、创建标签、推送和部署均需另行授权。

## 执行结果

- 候选身份：`e4cf9dd10bad4ef257fd92206dcdce582b2edc74`，版本 `1.5.2-rc.1`，bundle SHA-256 与 Git 校验通过。
- 后端：System 账户符号链接聚焦回归 `1 passed`；完整回归 `178 passed`。
- 安全与前端：秘密扫描通过；隔离虚拟环境 pip 升至 `26.2` 后 Python 审计为0；前端 lint/build 与 npm 生产依赖审计通过。
- 最终不变量：自动化助手执行 `inv-s8fe6wg7vv` 返回 ExitCode 0，清理3个门禁缓存目录并确认候选工作区干净；正式 HEAD 仍为 `b542d010d2679c0265fcd4cd50cd420fcd39954e`、版本仍为 `1.5.1`，`C:\AI-Bid-Data` 仍不存在。
- 资源边界：临时 COS 对象及空桶已删除；未创建标签、未推送、未提升正式版本、未启动服务或部署。
