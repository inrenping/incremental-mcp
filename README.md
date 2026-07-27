# Incremental MCP Server

基于 FastAPI + FastMCP 的 MCP 服务，为 `i.incremental.icu` 提供可通过 ChatGPT Desktop 调用的数据库查询能力。

## 架构

```
ChatGPT Desktop ──(stdio bridge)──▶ https://i.incremental.icu/mcp
                                        │
                          FastAPI (JWT 中间件)
                                        │
                          FastMCP (streamable-http)
                                        │
                          SQLAlchemy 2.0 + asyncpg
                                        │
                                 PostgreSQL
```

- **鉴权**：复用 `i.incremental.icu` 的 JWT（`SECRET_KEY` + `HS256`），在 FastAPI ASGI 中间件层统一校验
- **传输协议**：`streamable-http`（MCP 2025-11-25 规范推荐）
- **ORM**：SQLAlchemy 2.0 异步 + asyncpg

## 项目结构

```
app/
├── main.py              # FastAPI 入口，JWT 中间件，/mcp 挂载
├── mcp_server.py        # FastMCP 定义，tools 注册
├── config.py            # pydantic-settings，从 .env 读取配置
├── auth.py              # JWT 解码与用户 ID 提取
├── db.py                # async SQLAlchemy engine + session
├── models/
│   └── user.py          # t_users / t_user_refresh_tokens ORM 模型
└── tools/
    └── data_tools.py    # MCP tool 实现
```

## 环境变量

复制 `.env.example` 为 `.env` 并填写实际值：

| 变量 | 说明 |
|---|---|
| `DATABASE_URL` | PostgreSQL 连接串（asyncpg 驱动） |
| `SECRET_KEY` | JWT 签名密钥，需与主站一致 |
| `JWT_ALGORITHM` | JWT 算法，默认 `HS256` |

## MCP Tools

| Tool | 描述 |
|---|---|
| `query_user_profile` | 获取当前登录用户的基本信息（用户名、邮箱、会员状态等） |
| `query_active_users` | 列出所有已激活的用户 |
| `query_db_stats` | 查询用户统计（总数、激活数、VIP 用户数） |

## 本地开发

```bash
# 创建虚拟环境并安装依赖
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

# 复制环境变量
cp .env.example .env
# 编辑 .env 填写真实数据库连接和 SECRET_KEY

# 启动服务
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 运行冒烟测试
python test_smoke.py
```

MCP 端点：`http://localhost:8000/mcp`

## 鉴权方式

所有 `/mcp` 下的请求需携带：

```
Authorization: Bearer <JWT>
```

JWT 需与主站 `i.incremental.icu` 使用相同的 `SECRET_KEY` 和 `HS256` 算法签发，payload 中需包含用户标识字段（`sub` / `user_id` / `id`）。

## ChatGPT Desktop 集成

ChatGPT 桌面端通过 `mcp-streamable-http-shim` 桥接到远程 HTTP MCP 服务。

`claude_desktop_config.json` / ChatGPT MCP 配置示例：

```json
{
  "mcpServers": {
    "incremental-mcp": {
      "command": "npx",
      "args": [
        "-y", "@tollbit/mcp-streamable-http-shim",
        "--url", "https://i.incremental.icu/mcp",
        "-H", "Authorization: Bearer <YOUR_JWT>"
      ]
    }
  }
}
```

## 部署

### Docker

```bash
docker build -t incremental-mcp .
docker run -d --env-file .env -p 8000:8000 incremental-mcp
```

### 反向代理

在 nginx / Caddy 中配置反向代理，将 `/mcp` 路径指向服务端口 8000：

```nginx
location /mcp {
    proxy_pass http://127.0.0.1:8000/mcp;
    proxy_http_version 1.1;
    proxy_read_timeout 300s;       # MCP 长连接需要
    proxy_buffering off;           # SSE 流式传输
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## 添加新 Tool

在 [app/tools/data_tools.py](app/tools/data_tools.py) 中编写异步函数，然后在 [app/mcp_server.py](app/mcp_server.py) 中注册：

```python
# data_tools.py
async def my_new_tool(param: str) -> dict:
    """Tool 的描述（AI 会根据描述决定是否调用）。"""
    ...

# mcp_server.py
mcp.tool()(data_tools.my_new_tool)
```
