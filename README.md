## 飞书 MCP 配置指南

 1.访问并登录
打开网址：在浏览器中访问 https://open.feishu.cn/
登录账号：点击右上角的“登录”，使用你的飞书账号扫码登录。

2.创建应用（对应方案中的“第一步”）
登录成功后，按照以下路径操作：
进入后台：点击页面上的“开发者后台”。
创建应用：
选择“企业自建应用”页签。
点击“创建企业自建应用”。
填写应用名称（如“xiaohongshu_script_generate”），点击创建。

3.开启机器人：
在应用详情页左侧菜单，点击“添加应用能力”。
找到“机器人”卡片，点击“添加”。


4.配置权限（关键）：
点击左侧菜单的“权限管理”。
搜索并批量添加方案中要求的权限（如 im:chat:create, im:message 等）。

5.获取凭证：
点击左侧菜单的“凭证与基础信息”。
记下这里的 App ID 和 App Secret，稍后配置代码时需要用到。

6.配置 MCP（对应方案中的“第二步”和“第三步”）
将其中的写入到.env文件中即可


注意：将 <你的AppID> 和 <你的AppSecret> 替换为你在第二步中记下的真实字符串。


---

## 一个可复用 Skill说明
没有放在 skills/mcn-script-assistant/SKILL.md。

在我的后端

src/workspaces/skills/script_generate/fenerate_content/SKILL.md

中。


## 项目功能说明

### 使用了哪些 AI 工具
使用了Tace，模式是GLM-5.2,Doubao-Seed-2.1-Turbo工具，同时使用了桌面端的千问，豆包工具。

本项目是一个基于 **LangGraph + DeepAgents** 的多代理小红书智能营销系统，包含以下 AI 工具与子代理：

| 工具/子代理 | 说明 | 文件位置 |
|------------|------|---------|
| **主代理 (main_agent)** | 调度子代理的顶层智能体，负责意图识别和任务分发 | [src/agent/main_agent.py](/xiaohongshu_script_assistant/src/agent/main_agent.py) |
| **investigation 子代理** | 小红书博主调研专家，自动搜索 10 位博主、推荐最优人选、输出内容拆解 | [src/agent/subagents/investigation.yaml](/xiaohongshu_script_assistant/src/agent/subagents/investigation.yaml) |
| **script_generate 子代理** | 短视频脚本创作专家，产出口播文案、产品植入点、分镜设计、飞书文档写入 | [src/agent/subagents/script_generate.yaml](/xiaohongshu_script_assistant/src/agent/subagents/script_generate.yaml) |
| **web_search 工具** | 智谱 AI 搜索 API，用于搜索小红书博主和内容信息 | [src/agent/tools/web_search.py](/xiaohongshu_script_assistant/src/agent/tools/web_search.py) |
| **飞书 15 个 MCP 工具** | 飞书文档读写、表格创建、图片上传、文件夹管理等 | [src/agent/tools/mcp_client.py](/xiaohongshu_script_assistant/src/agent/tools/mcp_client.py) |
| **爬虫 skill** | 网页抓取工具，抓取博主主页内容并转 Markdown | [src/skills/investigation/web-scraper/SKILL.md](/xiaohongshu_script_assistant/src/skills/investigation/web-scraper/SKILL.md) |
| **脚本生成 skill** | 可复用的短视频脚本生成方法论（5 步流程 + 风险检查清单） | [src/workspaces/skills/script_generate/generate_content/SKILL.md](/xiaohongshu_script_assistant/src/workspaces/skills/script_generate/generate_content/SKILL.md) |
| **LLM 模型** | 通义千问 (qwen_llm)，通过 LangChain 调用 | [src/agent/models/model.py](/xiaohongshu_script_assistant/src/agent/models/model.py) |
| **Gradio UI** | 流式对话界面，支持工具调用过程展示 | [src/test/ui_agent.py](/xiaohongshu_script_assistant/src/test/ui_agent.py) |

**典型工作流：**
```
用户输入 brief
    ↓
主代理 → investigation 子代理（web_search 搜索博主）
    ↓
输出：10位博主清单 + 推荐1位 + 内容拆解 + 创作提示词
    ↓
主代理 → script_generate 子代理（飞书 MCP 写文档）
    ↓
输出：口播文案 + 产品植入点 + 分镜设计 + 飞书文档链接
```

### 如何运行

#### 环境准备

```bash
# 1. 进入项目目录
cd xiaohongshu_script_assistant

# 2. 创建虚拟环境,激活虚拟环境
python -m venv .my_venv

.my_venv\Scripts\activate


# 3. 安装依赖
pip install -r requirements.txt

# 4.替换.env.example为.env
mv .env.example .env

```

#### 配置环境变量

在 `src/.env` 文件中配置以下变量（参考 [src/agent/models/env_utils.py](/xiaohongshu_script_assistant/src/agent/models/env_utils.py)）：

```
# 智谱 AI（web_search 工具）
ZHIPU_API_KEY=你的智谱APIKey
ZHIPU_BASE_URL=https://open.bigmodel.cn/api/paas/v4

# 通义千问（主 LLM）
QWEN3_API_KEY=你的通义APIKey
QWEN3_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 飞书应用（MCP 工具）
APP_ID=你的飞书AppID
APP_SECRET=你的飞书AppSecret
YOUR_OPEN_ID=你的飞书OpenID
DOC_TOKEN=你的测试文档Token

# 你的信息
YOUR_EMAIL=你的邮箱
YOUR_PHONE=你的手机号
```

#### 启动 Gradio 界面

```bash
cd src
python test/ui_agent.py
```

启动后浏览器访问：**http://127.0.0.1:7860**

#### 运行飞书公网权限测试

```bash
cd src
python test/test_feishu.py
```

### 飞书文档如何接入

本项目通过 **飞书 MCP Server** 接入飞书文档能力，共 15 个工具：

| 工具名称 | 功能 |
|---------|------|
| `create_feishu_document` | 创建飞书文档（支持文件夹/维基空间两种模式） |
| `get_feishu_document_info` | 获取飞书文档基本信息 |
| `get_feishu_document_blocks` | 获取文档块层级结构 |
| `search_feishu_documents` | 搜索飞书文档和知识库 |
| `batch_update_feishu_block_text` | 批量更新文档块文本和样式 |
| `batch_create_feishu_blocks` | 批量创建文档块（文本/代码/标题/列表/图片等） |
| `delete_feishu_document_blocks` | 删除文档块范围 |
| `get_feishu_image_resource` | 下载飞书图片资源 |
| `upload_and_bind_image_to_block` | 上传图片并绑定到图片块 |
| `create_feishu_table` | 创建表格块 |
| `get_feishu_whiteboard_content` | 获取白板内容 |
| `fill_whiteboard_with_plantuml` | 用 PlantUML/Mermaid 填充白板 |
| `get_feishu_root_folder_info` | 获取根文件夹/维基空间列表 |
| `get_feishu_folder_files` | 获取文件夹/维基空间文件列表 |
| `create_feishu_folder` | 创建飞书文件夹 |

**接入步骤：**

1. **创建飞书自建应用**（见本 README 上方第 2 步）
2. **开通机器人能力**（第 3 步）
3. **配置权限**（第 4 步，需开通文档相关权限）
4. **获取凭证**（第 5 步，APP_ID + APP_SECRET）
5. **MCP 自动连接**：代码在 [mcp_client.py](/xiaohongshu_script_assistant/src/agent/tools/mcp_client.py) 中通过 `npx -y feishu-mcp --stdio` 自动启动飞书 MCP Server，无需手动配置
6. **授权文档**：应用创建的文档自动归属于应用云空间，如需给个人用户访问，调用 `batch_create_feishu_permission` 或使用 [test_feishu.py](/xiaohongshu_script_assistant/src/test/test_feishu.py) 中的 `set_public_permission()` 设置公网权限

**脚本子代理自动写入飞书文档的流程：**

```
script_generate 子代理
    ↓
create_feishu_document(title=脚本标题)  → 创建文档
    ↓
batch_create_feishu_blocks()           → 写入标题、口播文案、产品植入点
    ↓
create_feishu_table()                  → 生成分镜表格
    ↓
返回文档链接给用户
```

### 最终飞书文档链接或截图在哪里

**方式 1：Gradio 界面直接查看**

运行 `python test/ui_agent.py` 后，在对话界面中让 Agent 生成脚本，最终回复中会包含飞书文档链接，点击即可跳转打开。

**方式 2：飞书客户端/网页查看**

链接：[‍‍﻿‬‌﻿﻿‬‬﻿‍﻿﻿⁠‍‌⁠﻿﻿‌‬‌‬‌‌轻醒×菜菜的减脂日记 — 短视频脚本 - 飞书云文档](https://mcnzkvbntyxl.feishu.cn/docx/ZUyEdZo6RoZDLaxDdxXcLv37nce)

截图：![](.\images\1.png)

运行 `python test/test_feishu.py` 后，终端第 4 步会输出文档 URL，第 5 步会验证公网可访问性。

**方式 4：调研/脚本生成报告**

- 博主调研报告：`src/analyst/{关键词}_博主调研报告.md`（由 investigation 子代理生成）
- 脚本文档：直接在飞书中查看（由 script_generate 子代理创建）

**示例文档：**
- 已有的博主调研报告案例：[docs/light醒_小红书博主调研报告.md](/xiaohongshu_script_assistant/docs/light醒_小红书博主调研报告.md)
- 方法论说明文档：[docs/小红书Agent方法论说明_找博主_参考内容_脚本分镜设计.md](/xiaohongshu_script_assistant/docs/小红书Agent方法论说明_找博主_参考内容_脚本分镜设计.md)