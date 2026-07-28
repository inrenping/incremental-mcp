from contextlib import contextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.auth import decode_token
from app.db import init_db, close_db
from app.mcp_server import mcp_app


class JWTMiddleware(BaseHTTPMiddleware):
    """在 ASGI 层校验 Bearer JWT，保护包括 /mcp 在内的所有路由。"""

    async def dispatch(self, request: Request, call_next):
        path = request.url.path

        # 公开路由放行
        if path in ("/", "/health") or path.startswith("/openapi") or path.startswith("/docs"):
            return await call_next(request)

        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return JSONResponse({"detail": "Missing or invalid Authorization header"}, status_code=401)

        token = auth[7:]
        try:
            request.state.user = decode_token(token)
        except ValueError:
            return JSONResponse({"detail": "Invalid or expired token"}, status_code=401)

        return await call_next(request)


@contextmanager
def lifespan(app: FastAPI):
    """组合数据库连接校验与服务生命周期管理。"""
    init_db()
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


@app.get("/")
async def root():
    return {"service": "Incremental MCP Server", "status": "ok"}


@app.get("/health")
async def health():
    return {"status": "ok"}


# 将 MCP 服务挂载到 /mcp；生产环境通过反向代理暴露为 https://i.incremental.icu/mcp
app.mount("/mcp", mcp_app)
