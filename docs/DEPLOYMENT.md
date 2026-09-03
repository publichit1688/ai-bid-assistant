# 生产启动与健康检查

当前标准化入口适用于单机或反向代理后的 Python 进程部署。默认只监听 `127.0.0.1:8000`、单 worker，不启用 reload；当前 SQLite 和 Office 自动化架构建议保持 `APP_WORKERS=1`。

## 必要配置

- `DATABASE_URL`：指向持久化 SQLite 文件。
- `UPLOAD_DIR`：持久化上传目录。
- `REPORT_DIR`：持久化报告目录。
- `CORS_ORIGINS`：真实前端 HTTPS 来源，英文逗号分隔。
- `APP_HOST`、`APP_PORT`、`APP_WORKERS`、`APP_LOG_LEVEL`：服务监听参数。
- `DEEPSEEK_API_KEY`：仅通过秘密管理或未提交的 `.env` 提供。
- `AUTH_MODE`：本地默认 `disabled`；生产使用方案A时设为 `shared_token`。
- `APP_ACCESS_TOKEN`：共享模式必须提供至少32位的高熵随机值，只能通过秘密管理或未提交的 `.env` 提供。

数据库、上传和报告必须位于备份范围内。切换路径不会自动迁移旧数据；迁移前必须停写并备份。

## 备份与隔离恢复

在 `backend` 目录使用现有虚拟环境执行：

```powershell
.\.venv\Scripts\python.exe scripts\backup_runtime.py <全新的备份目录>
.\.venv\Scripts\python.exe scripts\restore_runtime.py <备份目录> <不存在的恢复目录>
```

恢复脚本不会覆盖任何已有目录。它先验证清单路径、文件集合、SHA-256与SQLite完整性，再复制到同级临时目录并原子落位。生产恢复必须先停止写入，在隔离目标完成应用启动和抽查后，才可由部署人员修改 `DATABASE_URL`、`UPLOAD_DIR`、`REPORT_DIR` 指向恢复结果；不得直接覆盖当前运行目录。

## 启动前检查

在 `backend` 目录执行：

```powershell
.\.venv\Scripts\python.exe scripts\start_production.py --check
```

检查项包含数据库、上传/报告存储和鉴权配置，只返回名称和通过/失败状态，不输出数据库地址、目录绝对路径或密钥。共享模式缺少密钥、密钥不足32位或模式未知时检查失败，进程不会启动。

## 启动

```powershell
.\.venv\Scripts\python.exe scripts\start_production.py
```

Linux 使用对应虚拟环境中的 `python` 执行同一脚本。DOC/DOCX 真实版式预览仍要求部署主机具备可用的 Microsoft Word、WPS Office 或已配置的兼容渲染器。

## 探针

- `GET /api/health`：存活探针。只证明应用进程能响应。
- `GET /api/health/ready`：就绪探针。验证数据库连接、上传目录可写和报告目录可写；依赖故障返回 HTTP 503。

共享模式仅允许匿名访问 `/` 和 `/api/health`；就绪探针、业务API及 `/uploads/*` 均需 `Authorization: Bearer ...`。`/docs`、`/redoc` 和 `/openapi.json` 在共享模式关闭。监控系统若需要就绪状态，必须从受控网络安全注入凭据且不得记录Header。

## 反向代理

参考模板：`deploy/nginx/ai-bid-assistant.conf.example`。使用前必须替换域名和证书路径，并确认上游端口与 `APP_PORT` 一致。模板完成以下边界：

- HTTP 强制跳转 HTTPS；
- `client_max_body_size 50m` 与默认 `UPLOAD_MAX_BYTES` 对齐；调整应用上限时必须同步代理上限，且代理不得更大；
- 转发真实来源协议和地址；
- 为文档分析设置有限的连接、读取和发送超时。

不要未经鉴权直接把管理接口暴露到公网。后端共享密钥边界和单进程限流已实现，但前端凭据接入与完整业务回归完成前不得启用公网部署。

应用已提供单进程基础限流。默认不信任代理头；使用本仓库Nginx模板并确认后端端口只允许本机代理连接后，可设置：

```dotenv
TRUST_PROXY_HEADERS=true
TRUSTED_PROXY_IPS=127.0.0.1,::1
RATE_LIMIT_WINDOW_SECONDS=60
UPLOAD_RATE_LIMIT=30
AI_RATE_LIMIT=60
```

Nginx模板使用 `$remote_addr` 覆盖 `X-Forwarded-For`，不追加客户端提供的链。多worker或多实例必须在网关或共享存储层建立全局限流，不能把当前内存窗口视为分布式安全控制。

## 服务守护

- Linux参考：`deploy/linux/ai-bid-assistant.service.example`。复制前替换用户、安装路径、环境文件和持久化目录；模板先执行 `--check`，失败不会启动服务。
- Windows启动器：`deploy/windows/start-backend.ps1`，始终使用项目现有 `backend/.venv` 并先执行检查。
- Windows服务包装参考：`deploy/windows/ai-bid-assistant-service.xml.example`。该文件面向WinSW式包装器，安装服务会改变系统状态，因此必须由部署人员审核路径后手工执行，本项目不会自动注册。

## 日志与轮转

应用日志写向标准输出和标准错误，不在应用内保存含业务正文的日志文件：

- systemd模板交由journal管理；生产主机应在journald配置中设置磁盘上限和保留期。
- Windows服务模板按10 MiB轮转并保留10份；日志目录必须限制访问权限。
- Nginx默认访问日志已在模板中关闭，避免原始URL记录客户文件名；应用层安全JSON日志承担请求审计。Nginx错误日志仍交由系统logrotate或等效机制轮转并限制访问权限。
- 不记录API Key、完整上传正文、完整提示词、数据库URL或客户文件绝对路径。

当前模板不会被自动安装或启用。Docker镜像不在本小批范围内。
