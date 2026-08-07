from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.tools import activity_tools, data_tools, heart_rate_tools, hello_tools

# MCP 服务暴露给 OpenAI/ChatGPT 的 resource 标识，必须与 PRM 中的 resource 字段一致
MCP_RESOURCE = "https://incremental.icu/mcp"
# 授权服务器（blunt-serv）的 OAuth 元数据
AUTH_SERVER = "https://incremental.icu"

# 与 blunt-serv /.well-known/oauth-authorization-server 保持一致的元数据
_AUTH_SERVER_METADATA = {
    "issuer": AUTH_SERVER,
    "authorization_endpoint": f"{AUTH_SERVER}/oauth/authorize",
    "token_endpoint": f"{AUTH_SERVER}/oauth/token",
    "registration_endpoint": f"{AUTH_SERVER}/oauth/register",
    "registration_endpoint_auth_methods_supported": ["none"],
    "response_types_supported": ["code"],
    "code_challenge_methods_supported": ["S256"],
    "token_endpoint_auth_methods_supported": ["none"],
    "scopes_supported": ["read"],
    "grant_types_supported": ["authorization_code", "refresh_token"],
}

mcp = FastMCP(
    "Incremental MCP Server",
    instructions="""
    这是一个为 incremental.icu 提供的 MCP 服务。
    通过 OAuth 2.1 (Authorization Code + PKCE) 进行身份验证。
    未认证的请求会返回 401 及 WWW-Authenticate 头以触发 OAuth discovery。
    """.strip(),
)

# 注册 tools
mcp.tool()(activity_tools.get_latest_run)
mcp.tool()(activity_tools.get_run_history)
mcp.tool()(data_tools.query_user_profile)
mcp.tool()(heart_rate_tools.get_heart_rate_history)
mcp.tool()(heart_rate_tools.get_daily_heart_rate)
mcp.tool()(hello_tools.say_hello)


@mcp.custom_route("/health", methods=["GET"])
async def health_check(request: Request) -> JSONResponse:
    """MCP 子应用健康检查端点，供外部监控服务（如 Better Stack）使用。"""
    return JSONResponse({"status": "ok"})


@mcp.custom_route("/.well-known/oauth-protected-resource", methods=["GET"])
async def protected_resource_metadata(request: Request) -> JSONResponse:
    """RFC 9728 Protected Resource Metadata — 让 ChatGPT 发现授权服务器位置。

    OpenAI/ChatGPT 要求 PRM 必须托管在 MCP 服务 URL 本身（或 401 的
    WWW-Authenticate 头中 advertised 的 URL）。本端点挂载在 /mcp 下，
    resource 字段与 MCP 服务 URL 严格一致。
    """
    return JSONResponse(
        {
            "resource": MCP_RESOURCE,
            "authorization_servers": ["https://incremental.icu"],
            "scopes_supported": ["read"],
            "bearer_methods_supported": ["header"],
            "resource_documentation": "https://incremental.icu/docs",
        }
    )


@mcp.custom_route("/.well-known/oauth-authorization-server", methods=["GET"])
async def authorization_server_metadata(request: Request) -> JSONResponse:
    """RFC 8414 授权服务器元数据 — 兼容 OpenAI 从 MCP URL 路径下发现 OAuth 配置。

    部分客户端（如 ChatGPT 手动配置 Authorization server base = MCP Server URL 时）
    会请求 {mcp_url}/.well-known/oauth-authorization-server，这里直接返回与
    blunt-serv 一致的元数据。
    """
    return JSONResponse(_AUTH_SERVER_METADATA)


@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration(request: Request) -> JSONResponse:
    """OpenID Connect Discovery — 兼容 OpenAI 用 OIDC 方式发现 OAuth 配置。"""
    meta = dict(_AUTH_SERVER_METADATA)
    meta.update(
        {
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256", "HS256"],
            "claims_supported": ["sub"],
            "response_modes_supported": ["query"],
        }
    )
    return JSONResponse(meta)


# 创建可挂载的 ASGI 应用，使用 streamable-http（MCP 当前推荐协议）
mcp_app = mcp.http_app(path="/", transport="streamable-http")
