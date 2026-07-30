from fastmcp import FastMCP

from app.tools import data_tools, hello_tools

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

# 创建可挂载的 ASGI 应用，使用 streamable-http（MCP 当前推荐协议）
mcp_app = mcp.http_app(path="/", transport="streamable-http")
