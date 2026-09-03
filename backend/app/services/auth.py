import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import get_app_access_token, get_auth_mode


PUBLIC_PATHS = {"/", "/api/health"}
MINIMUM_TOKEN_LENGTH = 32


def auth_is_enabled():
    return get_auth_mode() != "disabled"


def auth_configuration_is_valid():
    mode = get_auth_mode()
    if mode == "disabled":
        return True
    return mode == "shared_token" and len(get_app_access_token()) >= MINIMUM_TOKEN_LENGTH


def error_response(status_code, code, message, headers=None):
    return JSONResponse(
        status_code=status_code,
        content={"detail": {"code": code, "message": message}},
        headers=headers,
    )


class SharedTokenAuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        if (
            request.method == "OPTIONS"
            or request.url.path in PUBLIC_PATHS
            or not auth_is_enabled()
        ):
            return await call_next(request)

        if not auth_configuration_is_valid():
            return error_response(
                503,
                "AUTH_NOT_CONFIGURED",
                "访问控制配置无效，请联系管理员。",
            )

        scheme, _, credential = request.headers.get("Authorization", "").partition(" ")
        expected = get_app_access_token()
        if scheme.lower() != "bearer" or not credential or not secrets.compare_digest(
            credential, expected
        ):
            return error_response(
                401,
                "AUTH_REQUIRED",
                "需要有效访问凭据。",
                {"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
