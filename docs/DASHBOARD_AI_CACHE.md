# Dashboard AI 缓存契约

更新时间：2026-08-29

## 指纹输入

后端只使用 AI 管理摘要实际需要的字段生成 SHA-256 指纹：

- `days`
- `total_projects`
- `total_risks`
- `average_score`
- `risk_distribution`
- `score_distribution`
- `period_comparison`
- `attention_projects`

请求中的 UI 临时字段或其他附加字段不参与指纹。`days` 统一转换为整数，仅允许 7 或 30，缺失或非法值回退到 7；缺失的对象、列表和基础统计使用稳定默认值。JSON 使用排序键和紧凑分隔符序列化。

## 命中与失效

- 同一规范化数据只调用一次模型，后续请求返回 `cached: true`。
- 任一参与指纹的业务数据变化都会生成新指纹，不复用旧摘要。
- 缓存内容必须是合法 JSON 对象；损坏 JSON 或非对象内容会被删除并视为未命中。
- 损坏缓存删除后允许同一指纹重新生成并写入有效摘要。
- 模型超时、上游错误或非对象结果不写入缓存。

## 安全与测试

自动测试使用隔离 SQLite 和替身模型，不调用真实 DeepSeek。实现位于 `backend/app/api/dashboard.py`，回归位于 `backend/tests/test_dashboard_cache.py`。
