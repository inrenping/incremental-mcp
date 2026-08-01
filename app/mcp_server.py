from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.tools import data_tools, hello_tools

# MCP 服务暴露给 OpenAI/ChatGPT 的 resource 标识，必须与 PRM 中的 resource 字段一致
MCP_RESOURCE = "https://incremental.icu/mcp"

mcp = FastMCP(
    "Incremental MCP Server",
    instructions="""
    这是一个为 incremental.icu 提供的 MCP 服务。
    通过 OAuth 2.1 (Authorization Code + PKCE) 进行身份验证。
    未认证的请求会返回 401 及 WWW-Authenticate 头以触发 OAuth discovery。
    """.strip(),
)

# 注册 tools
mcp.tool()(data_tools.query_user_profile)
mcp.tool()(hello_tools.say_hello)
mcp.tool()(hello_tools.server_info)


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


# 创建可挂载的 ASGI 应用，使用 streamable-http（MCP 当前推荐协议）
mcp_app = mcp.http_app(path="/", transport="streamable-http")
