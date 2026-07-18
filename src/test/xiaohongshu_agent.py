import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from deepagents import create_deep_agent

from agent.config import CHECKPOINTER
from agent.models.model import qwen_llm
from agent.tools.mcp_client import load_mcp_tools, MCP_SERVER_CONFIG


XIAOHONGSHU_SYSTEM_PROMPT = """
你是一位专业的小红书内容运营专家，擅长打造爆款笔记。你的任务是根据用户提供的主题或产品信息，生成高质量的小红书脚本/文案，并可以将生成的内容保存到飞书文档中。

## 小红书爆款文案结构

每篇小红书笔记必须包含以下要素：

### 1. 标题（吸引眼球）
- 善用数字、emoji、疑问句式
- 突出痛点或利益点
- 控制在20字以内

### 2. 开头钩子（前3秒抓住注意力）
- 用共鸣、痛点、或悬念开头
- 一句话戳中用户

### 3. 正文内容
- 分段清晰，善用小标题
- 多用emoji增加活泼感
- 干货满满，有具体细节
- 加入个人体验/真实感受
- 每段不要太长

### 4. 结尾引导
- 互动提问
- 引导点赞收藏关注
- 相关话题推荐

### 5. 标签（Hashtag）
- 5-10个相关标签
- 包含大流量标签+精准标签

## 工作流程

当用户要求生成小红书脚本时：
1. 先生成高质量的小红书文案
2. 如果用户要求保存到飞书，使用 create_feishu_document 创建文档，然后用 batch_create_feishu_blocks 将内容写入
3. 文档标题使用小红书笔记的标题

记住：小红书的调性是真诚、分享、有干货、有温度。多用"姐妹们"、"谁懂啊"、"亲测"等口语化表达。
"""


async def create_xiaohongshu_agent():
    tools = await load_mcp_tools(server_config=MCP_SERVER_CONFIG)


    agent_graph = create_deep_agent(
        model=qwen_llm,
        system_prompt=XIAOHONGSHU_SYSTEM_PROMPT,
        tools=tools,
        checkpointer=CHECKPOINTER,
    )

    return agent_graph


async def generate_script(topic: str, save_to_feishu: bool = False):
    agent = await create_xiaohongshu_agent()

    user_message = f"请帮我生成一篇关于「{topic}」的小红书爆款脚本。"
    if save_to_feishu:
        user_message += " 生成后请保存到飞书文档中。"

    print(f"[INFO] 正在生成关于「{topic}」的小红书脚本...")
    print("=" * 60)
    config={"configurable": {"thread_id": "xiaohongshu-thread-001", "user_id": "laoxiao"}}
    result = await agent.ainvoke(
        config=config,
        input={"messages": [{"role": "user", "content": user_message}]}
    )

    print("\n" + "=" * 60)
    print("[INFO] 生成完成！")
    print("=" * 60)

    return result


if __name__ == "__main__":
    # import argparse
    #
    # parser = argparse.ArgumentParser(description="小红书脚本生成器")
    # parser.add_argument("--topic", help="小红书脚本主题")
    # parser.add_argument("--save", action="store_true", help="保存到飞书文档")
    # args = parser.parse_args()

    result = asyncio.run(generate_script(topic="小红书脚本生成器", save_to_feishu=True))

    for msg in result["messages"]:
        print(msg)
        # if msg["type"] == "ai":
        #     print("\n🤖 AI回复：")
        #     print(msg["content"])
