#!/usr/bin/env python3
"""
网页抓取工具 — 从沙箱内直接发起 HTTP 请求，解析 HTML 并转换为 Markdown 保存。

用法:
    python scrape_page.py --url "https://www.xiaohongshu.com/explore"
    python scrape_page.py --url "https://www.xiaohongshu.com/explore" --output "workspaces/explore.md"
"""

import argparse
import os
import re
import sys
import time
from urllib.parse import urlparse

import httpx

# ── 常量 ──────────────────────────────────────────────

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaohongshu.com/",
}

# 默认输出根目录（相对于项目根目录）
DEFAULT_OUTPUT_DIR = "workspaces"


# ── HTML → Markdown 转换 ──────────────────────────────

# 需要移除的标签（连同内容）
_REMOVE_TAGS = ["script", "style", "nav", "footer", "header", "noscript", "svg", "iframe"]

# 需要移除的标签（保留内容，只去标签）
_STRIP_TAGS = ["span", "div", "section", "article", "main", "aside", "figure"]

# HTML 标签 → Markdown 映射
_HEADING_MAP = {"h1": "#", "h2": "##", "h3": "###", "h4": "####", "h5": "#####", "h6": "######"}


def _remove_tags(html: str, tags: list[str]) -> str:
    """移除指定标签及其内容。"""
    for tag in tags:
        html = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            "",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
        # 自闭合标签
        html = re.sub(rf"<{tag}\b[^>]*/?>", "", html, flags=re.IGNORECASE)
    return html


def _strip_tags(html: str, tags: list[str]) -> str:
    """移除标签但保留内容。"""
    for tag in tags:
        html = re.sub(rf"</?{tag}\b[^>]*>", "", html, flags=re.IGNORECASE)
    return html


def _convert_headings(html: str) -> str:
    """将 h1-h6 转换为 Markdown 标题。"""
    for tag, prefix in _HEADING_MAP.items():
        html = re.sub(
            rf"<{tag}\b[^>]*>(.*?)</{tag}>",
            lambda m, p=prefix: f"\n\n{p} {m.group(1).strip()}\n\n",
            html,
            flags=re.DOTALL | re.IGNORECASE,
        )
    return html


def _convert_links(html: str) -> str:
    """将 <a href="...">text</a> 转换为 [text](url)。"""
    def replace_link(m):
        attrs = m.group(1)
        text = m.group(2).strip()
        href_match = re.search(r'href\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        href = href_match.group(1) if href_match else ""
        if not text:
            text = href
        if not href:
            return text
        return f"[{text}]({href})"

    html = re.sub(
        r'<a\b([^>]*)>(.*?)</a>',
        replace_link,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html


def _convert_images(html: str) -> str:
    """将 <img> 转换为 ![](src)。"""
    def replace_img(m):
        attrs = m.group(1)
        alt_match = re.search(r'alt\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        src_match = re.search(r'src\s*=\s*["\']([^"\']*)["\']', attrs, re.IGNORECASE)
        alt = alt_match.group(1) if alt_match else ""
        src = src_match.group(1) if src_match else ""
        if not src:
            return ""
        return f"![{alt}]({src})"

    html = re.sub(r'<img\b([^>]*)/?>', replace_img, html, flags=re.IGNORECASE)
    return html


def _convert_lists(html: str) -> str:
    """将 <ul>/<ol>/<li> 转换为 Markdown 列表。"""
    def replace_li(m):
        indent = m.group(1)
        content = m.group(2).strip()
        # 检查是否在 ol 中
        return f"{indent}- {content}\n"

    # 先处理 li
    html = re.sub(
        r'<li\b[^>]*>(.*?)</li>',
        lambda m: f"- {m.group(1).strip()}\n",
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    # 移除 ul/ol 标签
    html = re.sub(r"</?(ul|ol)\b[^>]*>", "\n", html, flags=re.IGNORECASE)
    return html


def _convert_table(html: str) -> str:
    """将简单表格转换为 Markdown 表格。"""
    def replace_table(m):
        table_html = m.group(0)
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", table_html, re.DOTALL | re.IGNORECASE)
        if not rows:
            return ""

        md_rows = []
        for row in rows:
            cells = re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", row, re.DOTALL | re.IGNORECASE)
            cells = [re.sub(r"<[^>]+>", "", c).strip() for c in cells]
            md_rows.append("| " + " | ".join(cells) + " |")

        if len(md_rows) >= 1:
            # 在第一行后加分隔行
            header = md_rows[0]
            separator = "| " + " | ".join(["---"] * (header.count("|") - 1)) + " |"
            md_rows.insert(1, separator)

        return "\n".join(md_rows) + "\n"

    html = re.sub(
        r"<table\b[^>]*>.*?</table>",
        replace_table,
        html,
        flags=re.DOTALL | re.IGNORECASE,
    )
    return html


def _convert_paragraphs_and_brs(html: str) -> str:
    """将 <p> 和 <br> 转换为换行。"""
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>", "\n\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<p\b[^>]*>", "", html, flags=re.IGNORECASE)
    return html


def _convert_inline_formatting(html: str) -> str:
    """转换加粗、斜体等行内格式。"""
    html = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", r"**\2**", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(em|i)\b[^>]*>(.*?)</\1>", r"*\2*", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<code\b[^>]*>(.*?)</code>", r"`\1`", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<blockquote\b[^>]*>(.*?)</blockquote>", lambda m: "\n> " + m.group(1).strip() + "\n", html, flags=re.DOTALL | re.IGNORECASE)
    return html


def _clean_whitespace(text: str) -> str:
    """清理多余空白。"""
    # 合并连续空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    # 去除行首尾多余空格
    lines = [line.rstrip() for line in text.split("\n")]
    text = "\n".join(lines)
    return text.strip()


def html_to_markdown(html: str) -> str:
    """将 HTML 转换为 Markdown。"""
    # 1. 移除干扰标签
    html = _remove_tags(html, _REMOVE_TAGS)

    # 2. 转换结构化标签
    html = _convert_headings(html)
    html = _convert_table(html)
    html = _convert_lists(html)
    html = _convert_images(html)
    html = _convert_links(html)
    html = _convert_inline_formatting(html)
    html = _convert_paragraphs_and_brs(html)

    # 3. 移除剩余 HTML 标签
    html = _strip_tags(html, _STRIP_TAGS)
    html = re.sub(r"<[^>]+>", "", html)

    # 4. 解码 HTML 实体
    html = html.replace("&nbsp;", " ").replace("&amp;", "&")
    html = html.replace("&lt;", "<").replace("&gt;", ">")
    html = html.replace("&quot;", '"').replace("&#39;", "'")

    # 5. 清理空白
    return _clean_whitespace(html)


# ── 网页抓取 ──────────────────────────────────────────

def fetch_page(url: str, timeout: int = 15, encoding: str | None = None) -> tuple[str, str]:
    """
    发起 HTTP GET 请求，返回 (html, 最终url)。

    Args:
        url: 目标 URL
        timeout: 超时秒数
        encoding: 强制编码，None 则自动检测
    """
    with httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers=DEFAULT_HEADERS,
    ) as client:
        response = client.get(url)
        response.raise_for_status()

        if encoding:
            response.encoding = encoding
        else:
            response.encoding = response.charset_encoding or "utf-8"

        return response.text, str(response.url)


def generate_output_path(url: str, output_dir: str = DEFAULT_OUTPUT_DIR) -> str:
    """根据 URL 自动生成输出文件路径。"""
    parsed = urlparse(url)
    domain = parsed.netloc.replace("www.", "").replace(".", "_")

    path_part = parsed.path.strip("/").replace("/", "_")
    if not path_part:
        path_part = "index"

    filename = f"{domain}_{path_part}.md"
    return os.path.join(output_dir, filename)


def save_markdown(content: str, output_path: str, source_url: str) -> str:
    """
    将 Markdown 内容保存到文件。

    在文件头部添加来源 URL 元信息。

    Returns:
        实际保存的绝对路径
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    # 添加元信息头
    header = f"> 来源: {source_url}\n> 抓取时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n---\n\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(header + content)

    return os.path.abspath(output_path)


# ── 主入口 ────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="网页抓取工具 — 抓取网页并转换为 Markdown 保存",
    )
    parser.add_argument("--url", required=True, help="目标网页 URL")
    parser.add_argument(
        "--output",
        default=None,
        help=f"输出 Markdown 文件路径，默认 {DEFAULT_OUTPUT_DIR}/{{domain}}_{{path}}.md",
    )
    parser.add_argument("--timeout", type=int, default=15, help="请求超时秒数（默认 15）")
    parser.add_argument("--encoding", default=None, help="强制指定页面编码（默认自动检测）")

    args = parser.parse_args()

    url = args.url
    print(f"[INFO] 正在抓取: {url}")

    try:
        html, final_url = fetch_page(url, timeout=args.timeout, encoding=args.encoding)
    except httpx.HTTPError as e:
        print(f"[ERROR] 请求失败: {e}")
        sys.exit(1)

    print(f"[INFO] 页面大小: {len(html)} 字符")

    # 转换为 Markdown
    markdown = html_to_markdown(html)

    if not markdown.strip():
        print("[WARN] 转换后内容为空，页面可能是 JavaScript 动态渲染。保存原始 HTML 前缀。")
        # 仍然保存，但标注可能是动态页面
        markdown = f"（注意：页面内容可能由 JavaScript 动态渲染，以下为可提取的有限内容）\n\n{html[:2000]}"

    # 确定输出路径
    output_path = args.output or generate_output_path(url)
    print(f"[INFO] 输出路径: {output_path}")

    # 保存
    saved_path = save_markdown(markdown, output_path, final_url)
    print(f"[OK] 已保存到: {saved_path}")
    print(f"[INFO] Markdown 内容: {len(markdown)} 字符")


if __name__ == "__main__":
    main()
