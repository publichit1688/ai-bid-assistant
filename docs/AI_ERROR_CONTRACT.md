# AI 接口错误契约

更新时间：2026-08-29

上传分析、项目对比 AI 决策和 Dashboard AI 摘要统一使用 FastAPI `detail` 对象返回错误：

```json
{
  "detail": {
    "code": "AI_TIMEOUT",
    "message": "AI 服务响应超时，请稍后重试。"
  }
}
```

## 错误类型

| HTTP | code | 使用场景 |
| --- | --- | --- |
| 503 | `AI_NOT_CONFIGURED` | 未配置 DeepSeek API Key |
| 504 | `AI_TIMEOUT` | 模型或网络请求超时 |
| 502 | `AI_INVALID_RESPONSE` | 模型返回非法 JSON 或不符合对象契约 |
| 502 | `AI_SERVICE_ERROR` | 其他上游 AI 服务错误 |

## 安全要求

- API 响应不得包含原始异常、API Key、请求头或模型供应商响应正文。
- AI API 日志只记录异常类型，不打印异常文本。
- 前端优先显示 `detail.message`，不得显示原始堆栈。
- 自动测试必须使用函数替身，不得调用真实 DeepSeek。

实现位于 `backend/app/services/ai_errors.py`，接口回归位于 `backend/tests/test_ai_errors.py`。
