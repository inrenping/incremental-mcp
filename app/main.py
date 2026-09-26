from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp, Receive, Scope, Send

from app.auth import decode_token
from app.db import init_db, close_db
from app.mcp_server import mcp_app, MCP_RESOURCE

# MCP 挂载路径
MCP_MOUNT_PATH = "/mcp"

# MCP OAuth discovery —— PRM 托管在 MCP 服务自身（OpenAI 要求），
# 通过 401 的 WWW-Authenticate 头告知客户端去 /mcp/.well-known/ 发现
PRM_URL = f"{MCP_RESOURCE}/.well-known/oauth-protected-resource"


class MCPPathNormalizer:
    """把不带尾斜杠的 /mcp 请求在路由前重写为 /mcp/。

    Starlette 的 Mount 只匹配 "<mount>/..." 形式的路径，命中不到 "/mcp"，
    于是上层 Router 会返回 307 重定向到 "/mcp/"。部分 MCP 客户端不跟随
    POST 的 307，或在重定向时丢弃 Authorization 头，表现为 Unauthorized。

    这里在路由之前统一路径，使 /mcp 与 /mcp/ 都由 MCP 子应用直接应答，
    不再产生任何 3xx。
    """

    def __init__(self, app: ASGIApp, mount_path: str = MCP_MOUNT_PATH) -> None:
        self.app = app
        self.mount_path = mount_path

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "") or ""
            if path.rstrip("/") == self.mount_path:
                normalized = self.mount_path + "/"
                scope = dict(scope)
                scope["path"] = normalized
                scope["raw_path"] = normalized.encode("latin-1")
        await self.app(scope, receive, send)


class JWTMiddleware(BaseHTTPMiddleware):
    """在 ASGI 层校验 Bearer JWT。

    未登录请求返回 401 + WWW-Authenticate，指向 PRM 元数据，
    使 ChatGPT / OAuth 客户端可以自动发现并启动 OAuth 2.1 流程。
    """

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路由放行（含 MCP 服务的 PRM 发现端点，OpenAI 需要匿名访问）
        if (
            path in ("/", "/health", "/mcp/health")
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
    """组合数据库连接校验与 MCP 服务生命周期管理。"""
    init_db()
    async with mcp_app.lifespan(app):
        try:
            yield
        finally:
            close_db()


app = FastAPI(
    title="Incremental MCP Server",
    version="0.1.0",
    lifespan=lifespan,
)

# 注意：中间件需要在 mount /mcp 之前注册，否则挂载的子应用不会经过它
app.add_middleware(JWTMiddleware)
# 该中间件必须最后注册 —— Starlette 中越晚添加的中间件越靠外，
# 才能在路由匹配发生之前把 /mcp 规范成 /mcp/。
app.add_middleware(MCPPathNormalizer)


@app.get("/")
async def root():
    return {"service": "Incremental MCP Server", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# 将 MCP 服务挂载到 /mcp；生产环境通过反向代理暴露为 https://incremental.icu/mcp
# /mcp（不带尾斜杠）由 MCPPathNormalizer 规范路径后直连，不再 307 到 /mcp/
app.mount(MCP_MOUNT_PATH, mcp_app)
