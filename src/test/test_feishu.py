"""
飞书文档公网访问权限设置与验证脚本

功能：
1. 获取 tenant_access_token
2. 调用 PATCH 接口打开文档公网访问权限（anyone_readable）
3. 调用 GET 接口验证权限设置
4. 获取文档公网链接
5. 验证链接确实可以公网访问

飞书 API 参考：
- 设置权限: PATCH /open-apis/drive/v1/permissions/{token}/public?type=doc
- 获取权限: GET  /open-apis/drive/v1/permissions/{token}/public?type=doc
- 文档信息: GET  /open-apis/docx/v1/documents/{document_id}
"""

import requests
import json
import sys
import os
from pathlib import Path

# 修复 Windows 终端 GBK 编码问题，确保 emoji 和中文正常输出
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# 将 src 目录加入 sys.path，以便导入 agent 包
SRC_DIR = Path(__file__).resolve().parent.parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from agent.models.env_utils import APP_ID, APP_SECRET, YOUR_OPEN_ID, DOC_TOKEN

# 飞书 API 基础地址
BASE_URL = "https://open.feishu.cn/open-apis"


def get_tenant_access_token() -> str:
    """获取飞书机器人的 tenant_access_token。"""
    url = f"{BASE_URL}/auth/v3/tenant_access_token/internal"
    resp = requests.post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"获取 token 失败: {data}")
    token = data["tenant_access_token"]
    print(f"[1/5] ✅ 获取 tenant_access_token 成功（前10位: {token[:10]}...）")
    return token


def set_public_permission(token: str, doc_token: str, doc_type: str = "doc") -> dict:
    """
    打开文档公网访问权限。

    Args:
        token: tenant_access_token
        doc_token: 文档 token
        doc_type: 文档类型（doc/sheet/wiki/bitable）

    Returns:
        API 响应
    """
    url = f"{BASE_URL}/drive/v1/permissions/{doc_token}/public?type={doc_type}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    payload = {
        "external_access": True,          # 允许分享到租户外
        "security_entity": "anyone_can_view",  # 所有可访问用户可创建副本/打印/导出
        "comment_entity": "anyone_can_view",   # 所有可访问用户可评论
        "share_entity": "anyone",              # 所有可阅读/编辑的用户可添加协作者
        "link_share_entity": "anyone_readable",  # 获得链接的任何人可阅读（公网可访问的关键）
        "invite_external": True,           # 允许邀请外部人
    }
    resp = requests.patch(url, headers=headers, json=payload)
    data = resp.json()
    print(f"[2/5] 设置公网权限 (type={doc_type}) | HTTP {resp.status_code} | code={data.get('code')} | msg={data.get('msg')}")
    return data


def get_public_permission(token: str, doc_token: str, doc_type: str = "doc") -> dict:
    """获取文档权限设置（验证用）。"""
    url = f"{BASE_URL}/drive/v1/permissions/{doc_token}/public?type={doc_type}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    print(f"[3/5] 验证权限设置 | HTTP {resp.status_code} | code={data.get('code')}")
    if data.get("code") == 0:
        perm = data["data"]["permission_public"]
        print(f"       external_access: {perm.get('external_access')}")
        print(f"       link_share_entity: {perm.get('link_share_entity')}")
        print(f"       share_entity: {perm.get('share_entity')}")
    return data


def get_document_url(token: str, doc_token: str) -> str:
    """
    获取文档信息，构造公网可访问链接。

    新版文档（docx）的链接格式: https://{tenant}.feishu.cn/docx/{document_id}
    通过获取文档信息接口拿到 URL。
    """
    url = f"{BASE_URL}/docx/v1/documents/{doc_token}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    data = resp.json()
    print(f"[4/5] 获取文档信息 | HTTP {resp.status_code} | code={data.get('code')}")

    if data.get("code") == 0:
        doc = data["data"]["document"]
        doc_url = doc.get("url", "")
        title = doc.get("title", "")
        print(f"       文档标题: {title}")
        print(f"       文档 URL: {doc_url}")
        return doc_url
    else:
        print(f"       获取失败: {data.get('msg')}")
        # 兜底：用 token 直接拼接（新版文档）
        return f"https://feishu.cn/docx/{doc_token}"


def verify_url_accessible(doc_url: str) -> bool:
    """验证公网链接是否可访问（不需要登录即可打开）。"""
    print(f"[5/5] 验证公网链接可访问性...")
    print(f"       URL: {doc_url}")
    try:
        resp = requests.get(doc_url, timeout=15, allow_redirects=True)
        print(f"       HTTP 状态码: {resp.status_code}")
        print(f"       最终 URL（重定向后）: {resp.url}")
        print(f"       响应长度: {len(resp.text)} 字符")

        # 判断是否可访问
        if resp.status_code == 200:
            # 检查页面内容是否包含文档内容（而非登录页）
            if "登录" in resp.text or "login" in resp.text.lower():
                print("       ⚠️ 页面跳转到登录页，公网访问可能未完全生效")
                return False
            else:
                print("       ✅ 链接公网可访问，无需登录")
                return True
        elif resp.status_code in (301, 302):
            print(f"       ⚠️ 重定向到: {resp.headers.get('Location')}")
            return False
        else:
            print(f"       ❌ 访问失败，状态码: {resp.status_code}")
            return False
    except Exception as e:
        print(f"       ❌ 请求异常: {type(e).__name__}: {e}")
        return False


def main():
    print("=" * 70)
    print("  飞书文档公网访问权限设置与验证")
    print(f"  文档 Token: {DOC_TOKEN}")
    print("=" * 70)

    errors = []

    # 第 1 步：获取 token
    try:
        access_token = get_tenant_access_token()
    except Exception as e:
        print(f"[1/5] ❌ 获取 token 失败: {e}")
        errors.append(f"获取 token 失败: {e}")
        return errors

    # 第 2 步：设置公网权限
    # 飞书新版文档（docx）type 参数尝试 doc
    # 如果 doc 报错，依次尝试其他类型
    perm_result = None
    tried_types = []
    for doc_type in ["doc", "docx", "sheet", "wiki"]:
        tried_types.append(doc_type)
        try:
            result = set_public_permission(access_token, DOC_TOKEN, doc_type)
            if result.get("code") == 0:
                perm_result = result
                print(f"       ✅ 使用 type={doc_type} 成功设置权限")
                break
            else:
                print(f"       ⚠️ type={doc_type} 失败: code={result.get('code')} msg={result.get('msg')}")
                # 1063001 = 参数不匹配（token 和 type 不匹配），继续尝试
                # 1063002 = 权限不足，不需要再尝试其他 type
                if result.get("code") == 1063002:
                    errors.append(f"权限不足(type={doc_type}): {result.get('msg')}")
                    break
        except Exception as e:
            print(f"       ❌ type={doc_type} 异常: {e}")
            errors.append(f"设置权限异常(type={doc_type}): {e}")

    if perm_result is None:
        print(f"\n❌ 所有类型尝试失败: {tried_types}")
        errors.append(f"所有文档类型设置权限失败: {tried_types}")
        # 继续验证步骤以获取更多信息

    # 第 3 步：验证权限设置
    verify_result = None
    for doc_type in ["doc", "docx"]:
        try:
            result = get_public_permission(access_token, DOC_TOKEN, doc_type)
            if result.get("code") == 0:
                verify_result = result
                print(f"       ✅ 使用 type={doc_type} 验证成功")
                break
        except Exception as e:
            print(f"       ❌ 验证异常(type={doc_type}): {e}")
            errors.append(f"验证权限异常(type={doc_type}): {e}")

    # 第 4 步：获取文档 URL
    doc_url = None
    try:
        doc_url = get_document_url(access_token, DOC_TOKEN)
    except Exception as e:
        print(f"[4/5] ❌ 获取文档 URL 失败: {e}")
        errors.append(f"获取文档 URL 失败: {e}")
        doc_url = f"https://feishu.cn/docx/{DOC_TOKEN}"

    # 第 5 步：验证链接可访问
    accessible = False
    try:
        accessible = verify_url_accessible(doc_url)
    except Exception as e:
        print(f"[5/5] ❌ 验证链接异常: {e}")
        errors.append(f"验证链接异常: {e}")

    # 汇总
    print("\n" + "=" * 70)
    print("  测试结果汇总")
    print("=" * 70)
    print(f"  获取 token:      ✅ 成功")
    print(f"  设置公网权限:    {'✅ 成功' if perm_result else '❌ 失败'}")
    print(f"  验证权限设置:    {'✅ 成功' if verify_result else '❌ 失败'}")
    print(f"  获取文档 URL:    {doc_url or '❌ 失败'}")
    print(f"  公网可访问:      {'✅ 是' if accessible else '❌ 否'}")
    print(f"  期间报错数:      {len(errors)}")
    if errors:
        print("\n  报错详情:")
        for i, err in enumerate(errors, 1):
            print(f"    {i}. {err}")
    print("=" * 70)

    return errors


if __name__ == "__main__":
    main()
