# 报告导出数据契约

更新时间：2026-08-29

## 风险报告

- 前端导出时提交当前页面的 `risk`、评分、等级计数和总扣分，而不是只依赖历史 `analysis` 快照。
- 后端以当前 `risk` 为事实来源，使用统一风险评分契约重新计算评分、评级、数量和总扣分。
- 报告必须包含项目名称、投标建议指数、风险评级、风险总数、高/中/低计数及风险总扣分。
- 风险集合缺失、损坏或字段为空时安全降级，不生成无法打开的 Word 文件。

## 项目对比报告

- 项目名称优先使用 `project_name`，缺失时回退到 `filename`，再回退到“未命名项目”。
- 项目 A/B 的页面评分、风险评级、高/中/低计数和总扣分直接来自当前 `compareResult.projectA/projectB`。
- 决策综合指数使用 `decisionScoreA/decisionScoreB`，不得与项目自身 AI 风险评分混为同一字段。
- AI 决策摘要允许为空，不阻止基础对比报告生成。

## 文件规则

- 两类服务端报告均写入 `reports/`，采用包含微秒的唯一文件名，不覆盖已有报告。
- HTTP 下载名称保持用户友好的固定中文名称。
- 自动测试只在 pytest 临时目录生成报告，读取响应字节重新打开 Word，并在测试结束后清理临时产物。

实现位于 `backend/app/services/report.py`、`backend/app/services/compare_report.py`，回归位于 `backend/tests/test_report_contract.py`。
