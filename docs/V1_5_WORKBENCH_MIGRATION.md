# V1.5工作台数据库迁移说明

迁移版本：

- `20260903_01_workbench_foundation`
- `20260903_02_response_materials`

## 安全边界

- 迁移只新增 `schema_migrations`、6张工作台基础表和1张响应材料表，不删除、不重命名、不改写V1表或数据。
- 每个迁移版本只登记一次；重复启动会校验结构并保持幂等。
- 同名表存在但缺少预期字段时启动失败，不把未知结构误登记为成功。
- 当前迁移仅支持SQLite；若以后更换数据库，必须先实现对应方言迁移，禁止静默执行。
- 自动测试使用独立临时SQLite，开发批次不对用户 `backend/bid.db` 执行试迁移。

## 新增表

- `bid_workspaces`
- `source_references`
- `outline_sections`
- `scoring_criteria`
- `criterion_section_mappings`
- `workspace_revisions`
- `response_materials`

第二版本在基础迁移成功后独立执行。响应材料必须至少关联一个评分点或目录章节，状态只允许 `pending`、`in_progress`、`completed`、`blocked`；责任人是可空人工文本，不自动绑定账号或分派真实人员。

字段语义和状态约束见 `docs/V1_5_WORKBENCH_DESIGN.md`，机器可读边界见 `docs/contracts/V1_5_WORKBENCH_CONTRACT.json`。

## 上线步骤

1. 停止写入并使用现有备份脚本创建数据库、上传和报告快照。
2. 在隔离恢复目录启动新代码，确认2条迁移记录和7张工作台表完整。
3. 验证原 `bid_files` 数量及关键只读接口不变。
4. 验证空工作台创建、重复创建幂等和读取接口。
5. 通过后才切换正式运行目录；不得把隔离数据库覆盖回原文件。

## 回滚

代码回滚不会自动删除新增表；旧V1代码会忽略这些表。若必须移除工作台数据，应先另建备份并使用单独、经审核的降级迁移，禁止人工直接删除用户数据库或原位执行 `DROP TABLE`。
