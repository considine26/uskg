import os
import json
from typing import List, Dict

def load_users_from_json(file_path: str = "users.json") -> tuple[str, List[Dict[str, str]]]:
    """从 users.json 加载 API 基础 URL 和用户列表"""
    if not os.path.exists(file_path):
        return "", []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        base_url = data.get("api_base_url", "https://domain-api.digitalplat.org/api/v1")
        profiles_data = data.get("profiles", {})
        users = []
        for username, profile in profiles_data.items():
            users.append({
                "USER": username,
                "MAIL": profile.get("mail", ""),
                "API_TOKEN": profile.get("api_token", "")
            })
        return base_url, users
    except Exception as e:
        print(f"❌ [错误]: 解析 {file_path} 失败: {e}")
        return "", []
