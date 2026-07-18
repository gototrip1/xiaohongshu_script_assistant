#!/usr/bin/env python3
"""
小红书 Agent 界面 - 基于 Gradio 的流式对话 UI

使用方法：
    1. 安装依赖：pip install gradio
    2. 运行：python test/ui_agent.py
    3. 浏览器访问：http://127.0.0.1:7860

功能：
    - 调用 main_agent.create_main_agent() 获取主 Agent
    - 流式输出 Agent 回复
    - 使用 checkpointer 维持会话状态（thread_id 随机生成）
    - 显示工具调用过程
"""

import asyncio
import uuid
import sys
from pathlib import Path

from agent.main_agent import create_main_agent

# 将 src 目录加入 sys.path，以便导入 agent 包
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import gradio as gr




# ---------------------------------------------------------------------------
# 全局 Agent 实例（启动时初始化一次，避免每次对话重复加载工具）
# ---------------------------------------------------------------------------
_agent = None
_thread_id = str(uuid.uuid4())  # 随机生成 thread_id，用于 checkpointer 会话隔离


async def init_agent():
    """初始化主 Agent（只执行一次）。"""
    global _agent
    if _agent is None:
        print("[初始化] 正在加载主 Agent 及飞书 MCP 工具...")
        _agent = await create_main_agent()
        print(f"[初始化] 完成 | thread_id={_thread_id}")


def reset_thread():
    """重置会话：生成新的 thread_id。"""
    global _thread_id
    _thread_id = str(uuid.uuid4())
    return f"已开启新会话 | thread_id: {_thread_id}", [], None


async def stream_agent_response(message: str, history: list):
    """
    流式调用 Agent，逐字输出回复。

    Args:
        message: 用户当前输入
        history: gr.ChatInterface 传入的对话历史 [[user, assistant], ...]

    Yields:
        实时更新的回复文本（含工具调用过程）
    """
    if _agent is None:
        await init_agent()

    # 构建 LangGraph 消息历史（转换为 messages 列表）
    messages = []
    for user_msg, assistant_msg in history:
        if user_msg:
            messages.append({"role": "user", "content": user_msg})
        if assistant_msg:
            messages.append({"role": "assistant", "content": assistant_msg})
    messages.append({"role": "user", "content": message})

    # checkpointer 配置（recursion_limit 调大，避免子代理+多工具调用触发 25 步上限）
    config = {
        "configurable": {
            "thread_id": _thread_id,
            "user_id": "AI_Math",
        },
        "recursion_limit": 150,
    }

    # 累积输出
    full_response = ""
    tool_logs = []  # 工具调用记录

    try:
        # 使用 astream_events 流式获取事件
        async for event in _agent.astream_events(
            {"messages": messages},
            config=config,
            version="v2",
        ):
            event_type = event["event"]
            event_data = event.get("data", {})

            # 1. 捕获 LLM 的流式文本输出
            if event_type == "on_chat_model_stream":
                chunk = event_data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    full_response += chunk.content
                    yield full_response, _format_tool_logs(tool_logs)

            # 2. 捕获工具开始调用
            elif event_type == "on_tool_start":
                tool_name = event.get("name", "unknown")
                tool_input = event_data.get("input", "")
                tool_input_str = str(tool_input)
                if len(tool_input_str) > 200:
                    tool_input_str = tool_input_str[:200] + "..."
                tool_logs.append(f"🔧 调用工具: {tool_name} | 输入: {tool_input_str}")
                yield full_response, _format_tool_logs(tool_logs)

            # 3. 捕获工具调用结束
            elif event_type == "on_tool_end":
                tool_name = event.get("name", "unknown")
                output = event_data.get("output", "")
                output_str = str(output)
                if len(output_str) > 300:
                    output_str = output_str[:300] + "..."
                tool_logs.append(f"✅ 工具完成: {tool_name} | 输出: {output_str}")
                yield full_response, _format_tool_logs(tool_logs)

            # 4. 捕获子代理开始（deepagents 子代理调度）
            elif event_type == "on_chain_start" and "subagent" in event.get("name", "").lower():
                tool_logs.append(f"🤖 启动子代理: {event.get('name')}")
                yield full_response, _format_tool_logs(tool_logs)

            # 5. 最终消息输出（确保完整内容）
            elif event_type == "on_chain_end" and event.get("name") == "agent":
                output = event_data.get("output", {})
                if hasattr(output, "get"):
                    msgs = output.get("messages", [])
                    if msgs:
                        last_msg = msgs[-1]
                        if hasattr(last_msg, "content") and last_msg.content:
                            if not full_response or len(last_msg.content) > len(full_response):
                                full_response = last_msg.content
                                yield full_response, _format_tool_logs(tool_logs)

    except Exception as e:
        err_type = type(e).__name__
        # 专门处理递归超限：给出可操作提示
        if "Recursion" in err_type or "recursion" in str(e).lower():
            error_msg = (
                "\n\n---\n⚠️ **任务过于复杂，已达到最大执行步数限制。**\n"
                "可能原因：子代理调用链过长，或工具在循环调用。\n"
                "建议：\n1. 将任务拆分为更小的步骤分多轮对话完成；\n"
                "2. 或在 config 中进一步调大 `recursion_limit`。"
            )
            full_response += error_msg
            tool_logs.append(f"❌ 递归超限: {str(e)[:200]}")
        else:
            error_msg = f"\n\n❌ 发生错误: {err_type}: {str(e)}"
            full_response += error_msg
            tool_logs.append(f"❌ 错误: {str(e)[:300]}")
        yield full_response, _format_tool_logs(tool_logs)

    # 如果没有任何流式输出，兜底返回
    if not full_response:
        full_response = "（Agent 未返回内容，请检查日志）"
        yield full_response, _format_tool_logs(tool_logs)


def _format_tool_logs(logs: list) -> str:
    """格式化工具调用日志为 HTML（固定高度容器 + 内部滚动）。"""
    if not logs:
        return '<div class="tool-log-container" style="color:#8b949e;">工具调用日志将显示在这里...</div>'
    # 将每条日志转为 HTML，保留换行
    import html as _html
    items = []
    for log in logs:
        # 根据前缀着色
        safe = _html.escape(log)
        if safe.startswith("🔧"):
            color = "#0969da"
        elif safe.startswith("✅"):
            color = "#1a7f37"
        elif safe.startswith("🤖"):
            color = "#8250df"
        elif safe.startswith("❌"):
            color = "#cf222e"
        else:
            color = "#57606a"
        items.append(f'<div style="color:{color};margin-bottom:6px;">{safe}</div>')
    content = "\n".join(items)
    return f'<div class="tool-log-container">{content}</div>'


# ---------------------------------------------------------------------------
# Gradio 界面
# ---------------------------------------------------------------------------

def create_ui():
    """创建 Gradio 界面。"""

    with gr.Blocks(
        title="小红书 Agent",
        theme=gr.themes.Soft(),
        css="""
        .main-container { max-width: 900px; margin: auto; }
        .tool-log-container {
            background: #f6f8fa;
            border: 1px solid #d0d7de;
            border-radius: 8px;
            padding: 12px;
            font-family: "Cascadia Code", "Fira Code", Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            height: 260px;
            max-height: 260px;
            overflow-y: auto;
            overflow-x: hidden;
            white-space: pre-wrap;
            word-break: break-all;
            box-sizing: border-box;
        }
        .tool-log-container::-webkit-scrollbar { width: 8px; }
        .tool-log-container::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 4px; }
        .tool-log-container::-webkit-scrollbar-thumb { background: #c1c1c1; border-radius: 4px; }
        .tool-log-container::-webkit-scrollbar-thumb:hover { background: #a8a8a8; }
        """,
    ) as demo:
        gr.Markdown(
            """
            # 🤖 小红书 Agent
            智能助手，支持博主调研（investigation）和短视频脚本创作（script_generate）。

            **使用示例：**
            - "帮我找一个适合推广夏日护肤产品的小红书博主"
            - "基于刚才选定的博主，帮我写一个短视频脚本"
            - "帮我搜索一下最新的美妆趋势"
            """
        )

        with gr.Row():
            thread_display = gr.Textbox(
                label="当前会话",
                value=f"thread_id: {_thread_id} | user_id: AI_Math",
                interactive=False,
                scale=3,
            )
            reset_btn = gr.Button("🔄 开启新会话", scale=1)

        # 对话区
        chatbot = gr.Chatbot(
            label="对话",
            height=450,
            # type="messages",
            # show_copy_button=True,
        )

        with gr.Row():
            msg_input = gr.Textbox(
                label="输入消息",
                placeholder="输入你的需求，按回车发送...",
                scale=4,
                lines=2,
            )
            send_btn = gr.Button("发送", scale=1, variant="primary")
            clear_btn = gr.Button("清空对话", scale=1)

        # 工具调用日志（使用 HTML 组件，固定高度 + 内部滚动，避免页面溢出）
        gr.Markdown("### 工具调用过程")
        tool_log = gr.HTML(
            value='<div class="tool-log-container" style="color:#8b949e;">工具调用日志将显示在这里...</div>',
            elem_classes=["tool-log-wrapper"],
        )

        # ---------------- 事件绑定 ----------------

        # 发送消息（流式输出）
        async def on_send(message, history):
            """处理发送消息。"""
            if not message.strip():
                yield history, "", ""
                return

            # 添加用户消息到历史
            history = history + [{"role": "user", "content": message}]
            # 添加空的 assistant 占位
            history = history + [{"role": "assistant", "content": ""}]
            yield history, "", ""

            # 流式更新 assistant 回复
            async for response_text, tool_logs in stream_agent_response(
                message, _extract_history_for_agent(history[:-1])
            ):
                history[-1] = {"role": "assistant", "content": response_text}
                yield history, tool_logs, ""

        def _extract_history_for_agent(gradio_history):
            """从 Gradio messages 格式提取为 [[user, assistant], ...] 格式。"""
            result = []
            i = 0
            while i < len(gradio_history):
                if gradio_history[i].get("role") == "user":
                    user_msg = gradio_history[i]["content"]
                    assistant_msg = ""
                    if i + 1 < len(gradio_history) and gradio_history[i + 1].get("role") == "assistant":
                        assistant_msg = gradio_history[i + 1]["content"]
                    result.append([user_msg, assistant_msg])
                    i += 2
                else:
                    i += 1
            return result

        send_btn.click(
            on_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, tool_log, msg_input],
        )

        msg_input.submit(
            on_send,
            inputs=[msg_input, chatbot],
            outputs=[chatbot, tool_log, msg_input],
        )

        # 清空对话
        def on_clear():
            return [], _format_tool_logs([]), ""

        clear_btn.click(on_clear, outputs=[chatbot, tool_log, msg_input])

        # 重置会话
        def on_reset():
            msg, _, _ = reset_thread()
            return msg + " | user_id: AI_Math", [], _format_tool_logs([]), ""

        reset_btn.click(
            on_reset,
            outputs=[thread_display, chatbot, tool_log, msg_input],
        )

    return demo


# ---------------------------------------------------------------------------
# 启动
# ---------------------------------------------------------------------------

def main():
    """启动 Gradio 界面。"""
    print("=" * 60)
    print("  小红书 Agent - Gradio UI")
    print(f"  thread_id: {_thread_id}")
    print(f"  user_id: AI_Math")
    print("=" * 60)

    demo = create_ui()

    # 启动时先初始化 Agent
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_agent())

    # 启动 Gradio
    demo.launch(
        server_name="127.0.0.1",
        server_port=7860,
        share=False,
        show_error=True,
    )


if __name__ == "__main__":
    main()
