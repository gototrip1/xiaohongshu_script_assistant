import os

import yaml
from pathlib import Path

from deepagents import create_deep_agent
from deepagents.backends import LocalShellBackend
from deepagents.middleware.subagents import SubAgent

from agent.config import CHECKPOINTER
from agent.models.model import qwen_llm
from agent.tools.mcp_client import load_mcp_tools, MCP_SERVER_CONFIG
from agent.tools.web_search import web_search


def load_subagent_config(yaml_path: str) -> dict:
    """从 YAML 文件加载子代理配置。"""
    path = Path(__file__).parent / "subagents" / yaml_path
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

# 获取当前项目根目录，并指向里面的 workspaces 文件夹
#__file__是当前的脚本的文件，输入文件的名字得到绝对路径os.path.abspath（），之后得到对应的os.path.dirname()得到这个文件的 src
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) # 假设代码在根目录或适当层级
target_dir = os.path.join(project_root, "workspaces")

async def create_main_agent():
    """
    创建主智能体。

    主代理管理以下子代理：
    - investigation: 小红书博主调研（使用 web_search + 爬虫 skill）
    - script_generate: 短视频脚本创作（使用飞书 15 个工具 + generate_content skill）
    """
    # 加载飞书 MCP 工具
    feishu_tools = await load_mcp_tools(server_config=MCP_SERVER_CONFIG)

    # 加载 investigation 子代理配置
    inv_config = load_subagent_config("investigation.yaml")

    investigation_subagent = SubAgent(
        name=inv_config["name"],
        description=inv_config["description"],
        system_prompt=inv_config["system_prompt"],
        skills=inv_config["skills"],
        tools=[web_search],
        model=qwen_llm,
    )

    # 加载 script_generate 子代理配置
    script_config = load_subagent_config("script_generate.yaml")

    script_generate_subagent = SubAgent(
        name=script_config["name"],
        description=script_config["description"],
        system_prompt=script_config["system_prompt"],
        skills=script_config["skills"],
        tools=feishu_tools,
        model=qwen_llm,
    )

    # 创建主代理
    agent_graph = create_deep_agent(
        model=qwen_llm,
        system_prompt=(
            "你是一个智能助手，帮助用户回答问题。如果是通用的问题，则不需要子代理，直接调用web_search工具或者直接回答即可。\n"
            "你可以调用子代理来完成专业任务：\n"
            "1. investigation - 博主调研（当用户需要寻找小红书博主、做达人甄选时调用）\n"
            "2. script_generate - 脚本创作（当用户需要为博主创作短视频脚本、生成分镜方案时调用）\n"
            "典型流程：先用 investigation 调研博主，再用 script_generate 生成脚本。\n"
            "你也可以直接使用飞书文档工具来创建和编辑文档。"
        ),
        tools=[web_search],
        backend=LocalShellBackend(
            root_dir=f"{target_dir}/",
            virtual_mode=True   # 不允许有..和.路径
        ),
        subagents=[investigation_subagent, script_generate_subagent],
        checkpointer=CHECKPOINTER,
    )

    return agent_graph


# if __name__ == '__main__':
#     project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # 假设代码在根目录或适当层级
#     target_dir = os.path.join(project_root, "workspaces")
#     print(target_dir)
