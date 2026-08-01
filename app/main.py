from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import decode_token
from app.db import init_db, close_db
from app.mcp_server import mcp_app, MCP_RESOURCE

# MCP OAuth discovery —— PRM 托管在 MCP 服务自身（OpenAI 要求），
# 通过 401 的 WWW-Authenticate 头告知客户端去 /mcp/.well-known/ 发现
PRM_URL = f"{MCP_RESOURCE}/.well-known/oauth-protected-resource"


class JWTMiddleware(BaseHTTPMiddleware):
    """在 ASGI 层校验 Bearer JWT。

    未登录请求返回 401 + WWW-Authenticate，指向 PRM 元数据，
    使 ChatGPT / OAuth 客户端可以自动发现并启动 OAuth 2.1 流程。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路由放行（含 MCP 服务的 PRM 发现端点，OpenAI 需要匿名访问）
        if (
            path in ("/", "/health")
            or path.startswith("/openapi")
            or path.startswith("/docs")
            or "/.well-known/" in path
        ):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse(
                {"detail": "Missing or invalid Authorization header"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{PRM_URL}", scope="read"'
                },
            )

        token = auth[7:]
        try:
            request.state.user = decode_token(token)
        except ValueError:
            return JSONResponse(
                {"detail": "Invalid or expired token"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{PRM_URL}", scope="read"'
                },
            )

        return await call_next(request)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """组合数据库连接 + FastMCP StreamableHTTP lifespan。

    FastMCP 3.x 在 streamable-http 模式下通过 mcp_app.lifespan 初始化
    内部的 StreamableHTTPSessionManager 任务组，缺失会导致 502。
    """
    init_db()
    async with mcp_app.lifespan(app):
        yield
    close_db()


app = FastAPI(
    title="Incremental MCP Server",
    version="0.1.0",
    lifespan=lifespan,
)

# 注意：中间件需要在 mount /mcp 之前注册，否则挂载的子应用不会经过它
app.add_middleware(JWTMiddleware)


@app.get("/")
async def root():
    return {"service": "Incremental MCP Server", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# 将 MCP 服务挂载到 /mcp；生产环境通过反向代理暴露为 https://incremental.icu/mcp
app.mount("/mcp", mcp_app)
