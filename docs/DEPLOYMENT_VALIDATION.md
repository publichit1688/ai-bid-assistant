# P3-03 类生产验证记录

验证日期：2026-09-02

## 隔离边界

- 使用项目已忽略的 `.pytest-tmp/production-smoke/` 保存测试SQLite、上传目录和报告目录。
- 使用独立监听地址 `127.0.0.1:18081`、单worker和warning日志级别。
- 未读取或修改用户 `bid.db`、上传文件、报告和 `.env`，未调用DeepSeek、OCR或Office转换。

## 首次启动

标准生产入口启动检查通过：`database`、`upload_storage`、`report_storage` 均为 `ok`。

HTTP结果：

| 接口 | 结果 |
| --- | --- |
| `/` | `Hello AI Bid Assistant` |
| `/api/health` | `status=ok` |
| `/api/health/ready` | `status=ready`，三项依赖均为`ok` |
| `/api/files` | HTTP 200，隔离数据库初始0条 |

进程收到正常中断后停止，端口复查为不可连接。

## 持久化重启

首次停止后仅向隔离SQLite写入一条脱敏记录，再使用完全相同的生产配置重启。就绪探针仍为`ready`，`/api/files`返回1条，文件名为`persistence-check.pdf`，证明配置的数据库在进程重启后保持一致。

第二次进程同样通过正常中断停止。本记录不代表模板已经安装为系统服务；Nginx、systemd和Windows服务配置仍需在目标主机人工审核路径、权限、证书和秘密来源。
