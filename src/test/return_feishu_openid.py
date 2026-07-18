# import requests
# from agent.models.env_utils import APP_ID, APP_SECRET
# from test.test_feishu import DOC_TOKEN
#
# DOC_TOKEN = DOC_TOKEN
#
# token = requests.post(
#     "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
#     json={"app_id": APP_ID, "app_secret": APP_SECRET}
# ).json()["tenant_access_token"]
#
# url = f"https://open.feishu.cn/open-apis/drive/v1/permissions/{DOC_TOKEN}/public?type=docx"
# headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
# resp = requests.patch(url, headers=headers, json={
#     "view_permission": "anyone",
#     "comment_permission": "only_editable",
#     "edit_permission": "only_editable"
# }).json()
# print(resp)

import requests

from agent.models.env_utils import APP_ID, APP_SECRET, DOC_TOKEN, YOUR_PHONE, YOUR_OPEN_ID

# ========== 配置信息 ==========
APP_ID = APP_ID  # 开发者后台获取
APP_SECRET = APP_SECRET  # 开发者后台获取
FILE_TOKEN = DOC_TOKEN  # 云文档URL里的token
FILE_TYPE = "wiki"  # 文档类型：doc/sheet/bitable/file 等
USER_OPEN_ID = YOUR_OPEN_ID  # 目标用户
PERMISSION = "edit"  # 权限：view(可阅读) / edit(可编辑) / full_access(可管理)


# ================================



def get_tenant_access_token():
    """获取 tenant_access_token"""
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    payload = {
        "app_id": APP_ID,
        "app_secret": APP_SECRET
    }
    resp = requests.post(url, json=payload).json()
    if resp.get("code") == 0:
        return resp["tenant_access_token"]
    raise Exception(f"获取token失败: {resp}")

def get_user_openid_by_mobile(tenant_token, mobile):
    """通过手机号查当前应用下用户的 open_id"""
    url = "https://open.feishu.cn/open-apis/contact/v3/users/batch_get_id"
    headers = {
        "Authorization": f"Bearer {tenant_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "mobiles": [mobile]
    }
    resp = requests.post(url, headers=headers, json=payload).json()
    return resp
tenant_token = get_tenant_access_token()
# 调用试试，填你自己的飞书手机号
result = get_user_openid_by_mobile(tenant_token, YOUR_PHONE)
print(result)

def add_collaborator(token):
    """批量添加协作者"""
    url = f"https://open.feishu.cn/open-apis/drive/v1/permissions/{FILE_TOKEN}/members/batch_create"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    params = {
        "type": FILE_TYPE
    }
    payload = {
        "members": [
            {
                "member_type": "userid",
                "member_id": USER_OPEN_ID,
                "perm": PERMISSION
            }
        ]
    }
    resp = requests.post(url, headers=headers, params=params, json=payload).json()
    return resp


if __name__ == "__main__":
    tenant_token = get_tenant_access_token()
    print(f"tenant_access_token: {tenant_token[:30]}...")

    result = add_collaborator(tenant_token)
    print(f"\n添加结果: {result}")