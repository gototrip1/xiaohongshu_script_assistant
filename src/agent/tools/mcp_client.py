"""
MCP 工具客户端。

在 Agent 启动时连接所有 MCP Server，获取全部 MCP 工具，
并按分组筛选后分配给不同的子 Agent。

使用方式:
    from agent.tools.mcp_client import load_mcp_tools
"""


from langchain_mcp_adapters.client import MultiServerMCPClient

from agent.models.env_utils import APP_SECRET, APP_ID

MCP_SERVER_CONFIG = {
    "feishu-mcp": {
        "command": "npx",
        "args": ["-y", "feishu-mcp", "--stdio"],
        "env": {"FEISHU_APP_ID": APP_ID, "FEISHU_APP_SECRET": APP_SECRET},
        "transport": "stdio",
    }
}

async def load_mcp_tools(
    server_config: dict | None = None,
):
    """
    连接到所有 MCP Server，加载全部工具并分组。

    Args:
        server_config: MCP Server 连接配置，默认使用 MCP_SERVER_CONFIG。

    Returns:
        (all_tools, analyst_tools, order_tools, chart_tools) 四元组
        - all_tools: 全部 MCP 工具列表（ERP + 图表）
        - analyst_tools: 供应商查询 + 零部件查询 + 库存预警工具
        - order_tools: 订单创建 + 订单更新 + 订单搜索工具
        - chart_tools: 图表/地图/可视化生成工具（来自魔塔社区 MCP Server，27 种）
    """
    if server_config is None:
        server_config = MCP_SERVER_CONFIG

    print("[INFO] 正在连接 MCP Server...")
    mcp_client = MultiServerMCPClient(server_config)

    # 从飞书 MCP Server 获取业务工具
    feishu_mcp_tools = await mcp_client.get_tools(server_name="feishu-mcp")
    print(f"[INFO] 已从飞书 MCP Server 加载 {len(feishu_mcp_tools)} 个工具")
    # print(feishu_mcp_tools)


    return feishu_mcp_tools

if __name__ == "__main__":
    import asyncio
    asyncio.run(load_mcp_tools())
