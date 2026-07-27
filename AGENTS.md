# AGENTS.md — Incremental MCP Server

面向 AI 编码助手的项目指南。

## 技术栈

- **Web 框架**：FastAPI（ASGI）
- **MCP 协议**：FastMCP（`fastmcp>=2.0`），streamable-http transport
- **ORM**：SQLAlchemy 2.0 异步 + asyncpg（PostgreSQL）
- **鉴权**：JWT（PyJWT），HS256，密钥与主站 `i.incremental.icu` 共享
- **配置**：pydantic-settings，从 `.env` 文件加载
- **测试**：pytest + pytest-asyncio

## 项目约定

### 命名与代码风格

- Python 3.11+，类型注解必填
- 环境变量：使用 `SECRET_KEY` 命名（与主站一致），不是 `JWT_SECRET`
- 数据库表名：`t_users`、`t_user_refresh_tokens`（与现有数据库一致）
- 工具函数：`async def`，返回 `dict` 或 `list[dict]`

### 配置文件

- `.env` 包含真实密钥，**不提交到 Git**
- `.env.example` 为模板，key 用占位符
- `app/config.py` 中通过 `pydantic-settings` 读取配置

### 鉴权流程

1. FastAPI ASGI 中间件 `JWTMiddleware` 拦截所有请求
2. 公开路由 `/`、`/health`、`/openapi*`、`/docs` 放行
3. 其他路由检查 `Authorization: Bearer <token>`，调用 `app.auth.decode_token()` 验证
4. MCP tool 内部通过 `get_http_headers()` 二次获取 token，解析 `sub`/`user_id`/`id` 字段

### 数据库

- 异步 engine 在 `app/db.py` 中创建
- 所有数据库操作使用 `AsyncSessionLocal()` 上下文管理器
- ORM 模型定义在 `app/models/`，对应 PostgreSQL 表

### 添加新功能

1. **新 Tool**：在 `app/tools/` 下写 `async def`，在 `app/mcp_server.py` 中用 `mcp.tool()` 注册
2. **新 Resource/Prompt**：同上，用 `mcp.resource()` / `mcp.prompt()` 注册
3. **新模型**：在 `app/models/` 下定义 SQLAlchemy ORM 类，表名使用 `__tablename__`
4. **新中间件**：在 `app/main.py` 的 `app.add_middleware()` 处注册

### 关键文件

| 文件 | 用途 |
|---|---|
| `app/config.py` | 环境变量配置，基于 pydantic-settings |
| `app/main.py` | FastAPI 主入口，JWT 中间件，lifespan，路由挂载 |
| `app/auth.py` | JWT 解码 + `get_user_id_from_payload` |
| `app/db.py` | 异步数据库引擎与会话工厂 |
| `app/mcp_server.py` | FastMCP 定义，工具注册，ASGI 应用创建 |
| `app/models/user.py` | `t_users` 和 `t_user_refresh_tokens` ORM 模型 |
| `app/tools/data_tools.py` | 所有 MCP 工具实现 |
| `test_smoke.py` | 冒烟测试（JWT 编解码、路由注册验证） |

### 测试策略

- `test_smoke.py` 不依赖数据库，仅验证应用结构
- 集成测试需启动 PostgreSQL，使用 `pytest-asyncio`
- MCP 工具测试可通过 FastMCP 客户端或直接调用函数

### 部署注意事项

- 反向代理需配置 `proxy_read_timeout >= 300s`（MCP 长连接）
- 关闭 `proxy_buffering`（SSE 流式传输需要）
- stateless 模式适合水平扩展，stateful 模式适合单实例
- JWT 中的用户 ID 需与 `t_users.id` 类型匹配（bigint）
