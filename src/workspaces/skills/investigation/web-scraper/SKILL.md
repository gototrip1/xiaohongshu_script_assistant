---
name: web-scraper
description: "网页抓取工具 | 从沙箱内直接发起 HTTP 请求获取网页内容，解析 HTML 并转换为干净的 Markdown 文件保存到本地的workspaces这个目录下。网址是 `https://www.xiaohongshu.com/explore`"
author: Boss
metadata:
  openclaw:
    emoji: 🕷️
    tags: [web, scraper, markdown, html-parsing, direct-http]
---

# 网页抓取工具 (Web Scraper)

从沙箱内直接发起 HTTP 请求，解析 HTML 并转换为 Markdown 保存。不依赖任何外部代理服务，可直接访问内网 URL。

## 适用场景

- 抓取小红书探索页面内容（`https://www.xiaohongshu.com/explore`）
- 需要将网页内容保存为 Markdown 文件供后续分析
- 批量抓取博主主页、笔记内容
- 抓取内网页面，外部代理服务无法访问的场景

## 使用方法

```bash
# 基本用法（自动生成输出文件名）
python /skills/investigation/web-scraper/scrape_page.py \
  --url "https://www.xiaohongshu.com/explore"

# 指定输出路径
python /skills/investigation/web-scraper/scrape_page.py \
  --url "https://www.xiaohongshu.com/explore" \
  --output "workspaces/xiaohongshu_explore.md"

# 抓取博主主页
python /skills/investigation/web-scraper/scrape_page.py \
  --url "https://www.xiaohongshu.com/user/profile/xxxxx" \
  --output "workspaces/blogger_profile.md"

# 抓取单篇笔记
python /skills/investigation/web-scraper/scrape_page.py \
  --url "https://www.xiaohongshu.com/explore/xxxxx" \
  --output "workspaces/note_detail.md"
```

## 参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `--url` | 是 | 目标网页 URL |
| `--output` | 否 | 输出 Markdown 文件路径，默认 `workspaces/{domain}_{path}.md` |
| `--timeout` | 否 | 请求超时秒数，默认 15 |
| `--encoding` | 否 | 强制指定页面编码，默认自动检测 |

## 工作原理

1. **直接 HTTP 请求** — 使用 `httpx` 库从沙箱内发起 GET 请求，模拟浏览器 User-Agent
2. **HTML 解析** — 使用正则移除 script/style/nav/footer 等干扰元素，提取主体内容
3. **Markdown 转换** — 将 HTML 标签转换为 Markdown 格式，保留标题/链接/列表/表格结构
4. **保存文件** — 写入 `workspaces/` 目录，自动创建父目录

## 输出目录

所有抓取结果默认保存到项目根目录下的 `workspaces/` 文件夹：

```
workspaces/
├── xiaohongshu_explore.md       # 探索页内容
├── blogger_profile_xxx.md       # 博主主页
├── note_detail_xxx.md           # 笔记详情
└── ...
```

## 示例

```
用户: 帮我抓取 https://www.xiaohongshu.com/explore 的内容并保存
助手: (执行 python scrape_page.py --url "https://www.xiaohongshu.com/explore")
     → 保存到 workspaces/xiaohongshu_explore.md

用户: 抓取这个博主的主页 https://www.xiaohongshu.com/user/profile/abc123
助手: (执行 python scrape_page.py --url "..." --output "workspaces/blogger_abc123.md")
     → 保存到 workspaces/blogger_abc123.md
```

## 注意事项

- 小红书部分页面需要登录才能查看完整内容，未登录状态下可能只能获取有限信息
- 请合理控制请求频率，避免触发反爬机制
- 抓取的内容仅供分析参考，请遵守平台使用条款

---

*直接 HTTP，不依赖外部代理 🕷️*
