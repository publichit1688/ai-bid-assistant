# V1.5智能编标工作台设计

状态：P5-01设计基线

日期：2026-09-03

范围：目录生成、人工编辑、评分点映射；不生成整本投标文件。

## 1. 目标与边界

工作台建立在V1已经完成分析的 `BidFile` 上，不改变上传、风险分析、PDF/Word预览、Dashboard、项目对比和报告接口。用户选择一个历史项目后创建工作台，AI只能生成“待确认建议”，人工确认后才能成为有效目录或评分点映射。

本阶段明确不做：

- 一键生成整本投标文件或自动提交投标；
- 无来源引用的章节、评分点或响应内容；
- 静默覆盖用户已经编辑的标题、顺序和映射；
- 把完整招标文件正文重复保存到工作台表；
- 在Dashboard继续增加工作台统计卡片。

## 2. 与V1的关系

- `bid_files` 继续是招标文件、项目名称、分析结果和风险数据的唯一V1来源。
- 一个 `BidFile` 最多对应一个活动工作台；删除工作台不删除原始项目或上传文件。
- 来源定位复用V1页码、连续原文片段和OCR坐标语义；工作台只保存必要引用，不复制整份正文。
- 新API沿用现有Bearer鉴权、请求ID、结构化脱敏日志、限流和统一AI错误契约。
- 工作台在前端作为独立一级视图出现，不嵌入Dashboard，不改变现有三栏分析页行为。

## 3. 数据模型

所有表均为增量新增；P5实现前必须补充安全迁移方案，不能删除或重建现有SQLite数据库。

### `bid_workspaces`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 工作台ID |
| bid_file_id | Integer | FK, unique, not null | 对应现有项目 |
| title | String | not null | 默认取项目名称，可人工修改 |
| status | String | not null | `draft` / `reviewing` / `frozen` |
| revision | Integer | not null, default 1 | 乐观并发版本号 |
| created_time | DateTime | not null | 创建时间 |
| updated_time | DateTime | not null | 最后修改时间 |

### `outline_sections`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 章节ID |
| workspace_id | Integer | FK, not null, index | 所属工作台 |
| parent_id | Integer | self FK, nullable | 根章节为空 |
| stable_key | String | unique per workspace | 跨排序和修订保持稳定 |
| title | String | not null | 章节标题 |
| sort_order | Integer | not null | 同级排序 |
| origin | String | not null | `ai` / `user` |
| review_status | String | not null | `suggested` / `confirmed` / `rejected` |
| source_ref_id | Integer | FK, nullable | 章节建议来源；人工章节可为空 |
| created_time | DateTime | not null | 创建时间 |
| updated_time | DateTime | not null | 修改时间 |

删除有子节点或评分点映射的章节必须显式确认；默认采用事务内级联调整或拒绝，不留下悬空映射。

### `scoring_criteria`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 评分点ID |
| workspace_id | Integer | FK, not null, index | 所属工作台 |
| stable_key | String | unique per workspace | 稳定业务标识 |
| title | String | not null | 评分点短标题 |
| requirement | Text | not null | 必须响应的原文要求 |
| max_score | Numeric, nullable | nullable | 无明确分值时为空，不猜测 |
| review_status | String | not null | `suggested` / `confirmed` / `rejected` |
| source_ref_id | Integer | FK, not null | 评分点必须有来源 |
| created_time | DateTime | not null | 创建时间 |
| updated_time | DateTime | not null | 修改时间 |

### `criterion_section_mappings`

评分点与章节是多对多关系；联合唯一键为 `(criterion_id, section_id)`。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 映射ID |
| criterion_id | Integer | FK, not null | 评分点 |
| section_id | Integer | FK, not null | 响应章节 |
| coverage_status | String | not null | `proposed` / `confirmed` / `gap` |
| rationale | Text | nullable | 映射理由，不作为投标正文 |
| origin | String | not null | `ai` / `user` |
| created_time | DateTime | not null | 创建时间 |
| updated_time | DateTime | not null | 修改时间 |

### `source_references`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 来源ID |
| bid_file_id | Integer | FK, not null | 原招标文件 |
| page | Integer | nullable | 可确认页码；无法确认时为空 |
| quote | Text | not null | 连续、最小充分原文片段 |
| locator | Text(JSON) | nullable | OCR归一化坐标或文本定位信息 |
| fingerprint | String | not null | 文件与引用内容指纹，用于失效检测 |

### `workspace_revisions`

只在用户显式保存、确认AI建议或批量调整映射后创建，不记录每次输入事件。

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| id | Integer | PK | 修订ID |
| workspace_id | Integer | FK, not null | 所属工作台 |
| revision | Integer | unique per workspace | 修订号 |
| action | String | not null | `create` / `edit` / `confirm_ai` / `freeze` |
| snapshot | Text(JSON) | not null | 目录、评分点与映射的结构化快照 |
| created_time | DateTime | not null | 修订时间 |

## 4. 状态和一致性规则

- AI响应先写入建议事务，所有新实体状态均为 `suggested` 或 `proposed`；用户确认后才变为 `confirmed`。
- 客户端更新必须提交当前 `revision`；版本不一致返回HTTP 409，前端提示重新加载，禁止后写覆盖先写。
- `frozen` 工作台默认只读；解冻必须是显式动作并产生新修订。
- 评分点必须有 `source_ref_id`；没有可靠引用的数据不落库，作为模型警告返回。
- 删除原项目时，若存在工作台应明确提示并在同一事务处理；不允许留下孤立工作台。
- AI失败不改变已确认数据，不写入半成品修订。

## 5. API草案

| 方法与路径 | 用途 | 关键约束 |
| --- | --- | --- |
| `POST /api/workspaces` | 从现有 `bid_file_id` 创建空工作台 | 幂等；已有工作台返回现有资源 |
| `GET /api/workspaces/{id}` | 获取目录、评分点、映射及覆盖摘要 | 不返回整份原文 |
| `POST /api/workspaces/{id}/outline-suggestions` | 生成目录建议 | 显式操作；只生成建议，不覆盖确认项 |
| `PATCH /api/workspaces/{id}/sections/{section_id}` | 修改标题、父级或排序 | 必须携带 `revision` |
| `POST /api/workspaces/{id}/sections` | 人工新增章节 | 默认直接标记 `confirmed` |
| `POST /api/workspaces/{id}/criteria-extractions` | 提取评分点建议 | 每项必须带来源，无法定位项进入warnings |
| `PUT /api/workspaces/{id}/mappings` | 批量确认映射 | 单事务、校验章节与评分点同属工作台 |
| `POST /api/workspaces/{id}/freeze` | 冻结当前修订 | 返回覆盖率与未映射缺口 |
| `GET /api/workspaces/{id}/revisions` | 查看版本列表 | 默认不返回大快照正文 |
| `GET /api/workspaces/{id}/revisions/{revision}` | 查看指定快照 | 只读 |

错误码沿用V1的安全结构，并增加：`WORKSPACE_CONFLICT`（409）、`SOURCE_REQUIRED`（422）、`WORKSPACE_FROZEN`（409）。

## 6. 前端交互原型

入口放在项目中心的单个项目操作区：“进入编标工作台”。不在Dashboard增加卡片。

```text
┌ 项目中心 / 项目名称 / 智能编标工作台 ─────────────────────────────┐
│ [目录与映射] [版本记录]                 保存状态  修订#  [冻结] │
├──────────────────┬──────────────────────┬──────────────────────┤
│ 招标原文/预览     │ 投标文件目录          │ 评分点与覆盖          │
│ 页码、连续引用    │ 树形拖拽、增删、改名  │ 全部/未映射/待确认    │
│ 点击引用定位原文  │ AI建议带“待确认”标记  │ 拖到章节或选择映射    │
│                  │ [生成目录建议]        │ [提取评分点]          │
└──────────────────┴──────────────────────┴──────────────────────┘
```

交互规则：

- 首次进入先创建空工作台，不自动调用AI。
- “生成目录建议”和“提取评分点”分别触发，允许单独重试。
- AI建议使用待确认样式；接受、拒绝、编辑均由用户主动操作。
- 选择评分点时，左侧定位来源，中央高亮已映射章节，右侧显示映射理由与状态。
- 顶部持续显示未映射数、待确认数和当前修订；不使用虚假的“完成率100%”。
- 1024px宽度下右栏改为抽屉，原文和目录仍可操作；不要求手机端完成复杂拖拽。

## 7. 分批实施顺序

1. 新增安全迁移、工作台基础表和不调用AI的CRUD/并发测试。
2. 实现目录建议的结构化模型调用、来源校验、建议确认和失败零污染。
3. 实现评分点提取、来源引用与章节映射。
4. 增加缺口、责任人和状态跟踪。
5. 完成合成数据、授权样本和浏览器最小闭环回归。

每批均不得修改V1风险评分含义，不得自动改写已确认内容，不得把真实标书或模型完整响应加入Git。

## 8. 当前实现进度

### `response_materials`

| 字段 | 类型 | 约束 | 说明 |
| --- | --- | --- | --- |
| workspace_id | Integer | FK, not null, index | 所属工作台 |
| criterion_id | Integer | FK, nullable, index | 关联评分点 |
| section_id | Integer | FK, nullable, index | 关联目录章节 |
| stable_key | String | unique per workspace | 稳定业务标识 |
| title | String | not null | 响应材料名称 |
| material_status | String | not null | pending/in_progress/completed/blocked |
| owner_name | String | nullable | 人工填写责任人，不自动分派 |
| notes | Text | nullable | 缺口或阻塞说明 |

`criterion_id`和`section_id`至少一个非空；后续接口必须继续校验所关联对象属于同一工作台。状态为`pending`或`blocked`的材料进入缺口视图，但不能据此虚构材料内容。

P5-02四个小批已完成迁移、人工目录编辑、来源可验证的AI目录建议及人工审核后端闭环。P5-03已完成带来源的评分点提取、人工审核、同工作台已确认对象映射、修订快照及覆盖统计。P5-04已完成响应材料安全迁移、新增/列表/修改API、人工责任人与说明、四态汇总及修订快照。P5-05已完成后端闭环回归、前端总览、建议审核、材料维护、人工目录及评分点—章节人工映射；显式AI提取入口尚未接入前端。
