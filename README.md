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
│   ├── user.py              # t_users / t_user_refresh_tokens ORM 模型
│   └── main_activity.py     # t_main_activity ORM 模型（跑步数据）
└── tools/
    ├── data_tools.py        # MCP tool 实现（用户信息）
    ├── activity_tools.py    # MCP tool 实现（跑步数据）
    └── hello_tools.py       # 示例 tool
```

## 环境变量

复制 `.env.example` 为 `.env` 并填写实际值：

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | PostgreSQL 连接串（asyncpg 驱动） |
| `SECRET_KEY` | JWT 签名密钥，需与主站一致 |
| `JWT_ALGORITHM` | JWT 算法，默认 `HS256` |

## GitHub Secrets 配置

自动化部署通过 `.github/workflows/deploy.yml` 执行，需要在仓库的 **Settings → Secrets and variables → Actions** 中配置以下 secrets：

| Secret | 用途 | 是否必填 |
| --- | --- | --- |
| `REMOTE_HOST` | 部署目标服务器的 IP 或域名 | 是 |
| `REMOTE_USER` | SSH 登录用户名 | 是 |
| `SECRET_KEY` | SSH 私钥；部署时也会写入 `.env` 作为 JWT 签名密钥 | 是 |
| `DATABASE_URL` | PostgreSQL 连接串，部署时写入 `.env` | 是 |
| `SUPABASE_STORAGE_BUCKET` | Supabase 存储桶名称 | 否（仅当使用对象存储） |
| `SUPABASE_STORAGE_ENDPOINT` | Supabase S3 兼容端点 | 否（仅当使用对象存储） |
| `SUPABASE_STORAGE_REGION` | Supabase 存储区域 | 否（仅当使用对象存储） |
| `SUPABASE_ACCESS_KEY_ID` | Supabase 访问密钥 ID | 否（仅当使用对象存储） |
| `SUPABASE_SECRET_ACCESS_KEY` | Supabase 私有访问密钥 | 否（仅当使用对象存储） |

> **注意**：当前 `deploy.yml` 使用同一个 `SECRET_KEY` 既作为 SSH 私钥，又作为应用 JWT 密钥。建议将两者分离，例如 SSH 私钥使用 `SSH_PRIVATE_KEY`，应用密钥保留 `SECRET_KEY`。

## MCP Tools

| Tool | 描述 |
| --- | --- |
| `get_latest_run` | 获取当前用户最近一次跑步记录 |
| `get_run_history` | 分页查询当前用户的历史跑步记录 |
| `query_user_profile` | 获取当前登录用户的基本信息（用户名、邮箱、会员状态等） |

### 跑步数据工具

跑步数据直接查询 `t_main_activity` 表（与主站 blunt-serv 共享同一 PostgreSQL），不经过 FastAPI 转发。

**`get_latest_run`**

无参数，返回最近一条跑步记录的完整数据（距离、时长、心率、配速、爬升等）：

```json
{
  "status": "success",
  "data": {
    "id": 123,
    "activity_name": "晨跑",
    "sport_type_raw": "running",
    "start_time_local": "2026-08-05T07:30:00",
    "distance_meters": 5210.0,
    "duration_seconds": 2100.0,
    "average_hr": 152,
    "max_hr": 178,
    "...": "..."
  }
}
```

**`get_run_history`**

分页查询历史跑步记录，按本地开始时间倒序：

| 参数 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `limit` | int | 10 | 每页条数 |
| `offset` | int | 0 | 跳过的条数 |
| `start_date` | str | 无 | 起始日期过滤（本地时间），格式 `YYYY-MM-DD` |
| `end_date` | str | 无 | 结束日期过滤（本地时间），格式 `YYYY-MM-DD` |

返回 `{"status": "success", "data": [...], "total": N}`。

> 跑步类型过滤与后端一致：`running` / `treadmill_running` / `trail_running` / `track_running` / `indoor_running` 及 key `100`-`103`。

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
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload

# 查看运行日志
journalctl -u incremental-mcp -n 50

# 运行冒烟测试
python test_smoke.py
```

MCP 端点：`http://localhost:8001/mcp`

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
docker run -d --env-file .env -p 8001:8001 incremental-mcp
```

### 反向代理

在 nginx / Caddy 中配置反向代理，将 `/mcp` 路径指向服务端口 8001：

```nginx
location /mcp {
    proxy_pass http://127.0.0.1:8001/mcp;
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
