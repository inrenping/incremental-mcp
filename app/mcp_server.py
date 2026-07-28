from fastmcp import FastMCP

from app.tools import data_tools, hello_tools

mcp = FastMCP(
    "Incremental MCP Server",
    instructions="""
    这是一个为 i.incremental.icu 提供的 MCP 服务。
    所有 tool 都需要通过 Authorization: Bearer <JWT> 进行身份验证。
    """.strip(),
)

# 注册 tools
mcp.tool()(data_tools.query_user_profile)
mcp.tool()(hello_tools.say_hello)
mcp.tool()(hello_tools.server_info)

# 创建可挂载的 ASGI 应用，使用 streamable-http（MCP 当前推荐协议）
mcp_app = mcp.http_app(path="/", transport="streamable-http")
