import asyncio
import os
import sys
import httpx
import questionary
from typing import List, Dict, Optional

BASE_URL = "https://domain-api.digitalplat.org/api/v1"

def load_users_from_env(file_path: str = ".env") -> List[Dict[str, str]]:
    """手动解析 .env 文件以支持多账号配置"""
    users = []
    current_user = {}
    
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            # 忽略注释和空行
            if not line or line.startswith("#"):
                continue
            
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip()
                
                # 如果遇到重复的 USER 键，说明进入了下一个用户块
                if key == "USER" and "USER" in current_user:
                    users.append(current_user)
                    current_user = {}
                
                current_user[key] = val

        # 添加最后一个用户块
        if current_user:
            users.append(current_user)
            
    return [u for u in users if "API_TOKEN" in u]

class USKGClient:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=15.0)

    async def list_domains(self):
        try:
            response = await self.client.get("/domains")
            if response.status_code == 200:
                return response.json().get("data", [])
            return f"Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"Network Error: {str(e)}"

    async def register_domain(self, domain: str, slot_type: str, nameservers: List[str]):
        data = {"domain": domain, "slot_type": slot_type, "nameservers": nameservers}
        response = await self.client.post("/domains", json=data)
        return response.json()

    async def update_dns(self, domain: str, nameservers: List[str]):
        data = {"nameservers": nameservers}
        response = await self.client.patch(f"/domains/{domain}/nameservers", json=data)
        return response.json()

    async def delete_domain(self, domain: str):
        response = await self.client.delete(f"/domains/{domain}")
        return response.json()

    async def close(self):
        await self.client.aclose()

async def interactive_menu():
    users = load_users_from_env()
    
    if not users:
        print("❌ [错误]: 未在 .env 文件中检测到有效的用户配置。")
        print("请确保格式为: \nUSER=xxx\nMAIL=xxx\nAPI_TOKEN=xxx")
        return

    # 1. 选择账号
    if len(users) > 1:
        user_choices = [
            f"{u.get('USER')} ({u.get('MAIL')})" for u in users
        ]
        selected_index = await questionary.select(
            "请选择要使用的账号:",
            choices=user_choices
        ).ask_async()
        # 找到匹配的索引
        idx = user_choices.index(selected_index)
        current_account = users[idx]
    else:
        current_account = users[0]

    print(f"✅ 已登录账号: {current_account.get('USER')} ({current_account.get('MAIL')})")
    client = USKGClient(current_account.get("API_TOKEN"))
    
    try:
        while True:
            action = await questionary.select(
                f"[{current_account.get('USER')}] 请选择操作:",
                choices=[
                    "1. 列出所有域名",
                    "2. 注册新域名",
                    "3. 修改 DNS (Nameservers)",
                    "4. 删除域名",
                    "5. 切换账号",
                    "6. 退出程序"
                ]
            ).ask_async()

            if action == "1. 列出所有域名":
                print("\n🔍 正在获取列表...")
                domains = await client.list_domains()
                if isinstance(domains, list):
                    if not domains:
                        print(">> 目前没有任何域名。")
                    for d in domains:
                        ns = ", ".join(d.get('nameservers', []))
                        print(f"- [{d.get('domain')}] | 状态: {d.get('status')} | NS: {ns}")
                else:
                    print(domains)
                print("\n")

            elif action == "2. 注册新域名":
                domain = await questionary.text("请输入要注册的域名 (例如 example.us.kg):").ask_async()
                if not domain: continue
                slot_type = await questionary.select(
                    "请选择槽位类型:",
                    choices=["free", "paid", "subscription"]
                ).ask_async()
                ns_input = await questionary.text("请输入 DNS (多个用逗号隔开):").ask_async()
                ns_list = [n.strip() for n in ns_input.split(",") if n.strip()]
                
                print(f"🚀 正在注册 {domain}...")
                result = await client.register_domain(domain, slot_type, ns_list)
                print(f">> 结果: {result}\n")

            elif action == "3. 修改 DNS (Nameservers)":
                domains = await client.list_domains()
                if not isinstance(domains, list) or not domains:
                    print(">> 没有可操作的域名。\n")
                    continue
                
                target = await questionary.select(
                    "请选择要修改的域名:",
                    choices=[d.get('domain') for d in domains]
                ).ask_async()
                
                ns_input = await questionary.text("请输入新的 DNS (逗号隔开):").ask_async()
                ns_list = [n.strip() for n in ns_input.split(",") if n.strip()]
                
                print(f"🚀 正在更新 {target} 的 DNS...")
                result = await client.update_dns(target, ns_list)
                print(f">> 结果: {result}\n")

            elif action == "4. 删除域名":
                domains = await client.list_domains()
                if not isinstance(domains, list) or not domains:
                    print(">> 没有可操作的域名。\n")
                    continue
                
                target = await questionary.select(
                    "请选择要删除的域名:",
                    choices=[d.get('domain') for d in domains]
                ).ask_async()
                
                confirm = await questionary.confirm(f"确定要删除域名 {target} 吗？").ask_async()
                if confirm:
                    print(f"🔥 正在删除 {target}...")
                    result = await client.delete_domain(target)
                    print(f">> 结果: {result}\n")

            elif action == "5. 切换账号":
                await client.close()
                return await interactive_menu() # 递归调用重新进入选择流程

            elif action == "6. 退出程序":
                print("👋 再见！")
                break
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n👋 用户中止程序。")
        sys.exit(0)
