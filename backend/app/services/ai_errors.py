from fastapi import HTTPException


class AIConfigurationError(RuntimeError):
    """The AI provider is not configured for this deployment."""


class AIResponseFormatError(ValueError):
    """The provider returned content that violates the JSON contract."""


def to_ai_http_exception(exc):
    """Map provider failures to a stable, sanitized API error contract."""
    if isinstance(exc, AIConfigurationError):
        status_code = 503
        code = "AI_NOT_CONFIGURED"
        message = "AI 服务尚未配置，请联系管理员配置后重试。"
    elif isinstance(exc, AIResponseFormatError):
        status_code = 502
        code = "AI_INVALID_RESPONSE"
        message = "AI 返回格式异常，请稍后重试。"
    elif isinstance(exc, TimeoutError) or "timeout" in type(exc).__name__.lower():
        status_code = 504
        code = "AI_TIMEOUT"
        message = "AI 服务响应超时，请稍后重试。"
    else:
        status_code = 502
        code = "AI_SERVICE_ERROR"
        message = "AI 服务暂时不可用，请稍后重试。"

    return HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message},
    )
