import asyncio
import json
import os
import sys
import httpx
import questionary
from typing import List, Dict, Optional

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

class USKGClient:
    def __init__(self, token: str, base_url: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        self.client = httpx.AsyncClient(base_url=base_url, headers=self.headers, timeout=15.0, follow_redirects=True)

    async def list_domains(self):
        try:
            response = await self.client.get("/domains")
            if response.status_code == 200:
                return response.json().get("data", [])
            
            # 针对 403 等非 JSON 错误的诊断
            error_msg = f"Error: {response.status_code}"
            if "text/html" in response.headers.get("Content-Type", ""):
                import re
                title = re.search(r"<title>(.*?)</title>", response.text)
                title_str = title.group(1) if title else "未知 HTML 错误"
                error_msg += f" (页面标题: {title_str})"
            else:
                error_msg += f" - {response.text[:200]}"
            return error_msg
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

def clear_screen():
    """清除终端屏幕内容"""
    os.system('cls' if os.name == 'nt' else 'clear')

async def interactive_menu():
    base_url, users = load_users_from_json()
    
    if not users:
        print("❌ [错误]: 未在 users.json 文件中检测到有效的用户配置。")
        print("请确保格式为 JSON，且包含 profiles 键。")
        return

    # 1. 选择账号
    clear_screen()
    if len(users) > 1:
        user_choices = [
            f"{u.get('USER')} ({u.get('MAIL')})" for u in users
        ]
        selected_index = await questionary.select(
            "请选择要使用的账号 (使用键盘上下键, 回车确认):",
            choices=user_choices
        ).ask_async()
        idx = user_choices.index(selected_index)
        current_account = users[idx]
    else:
        current_account = users[0]

    clear_screen()
    print(f"✅ 已登录账号: {current_account.get('USER')} ({current_account.get('MAIL')})")
    client = USKGClient(current_account.get("API_TOKEN"), base_url)
    
    try:
        while True:
            action = await questionary.select(
                f"[{current_account.get('USER')}] 请选择操作:",
                choices=[
                    "1. 查看域名",
                    "2. 注册域名",
                    "3. 修改记录 (NameServers)",
                    "4. 删除域名",
                    "5. 切换账号",
                    "6. 退出程序"
                ]
            ).ask_async()

            if action == "1. 查看域名":
                clear_screen()
                print(f"--- 账号: {current_account.get('USER')} | 域名列表 ---")
                print("🔍 正在获取列表...")
                domains = await client.list_domains()
                if isinstance(domains, list):
                    if not domains:
                        print(">> 目前没有任何域名。")
                    for d in domains:
                        ns = ", ".join(d.get('nameservers', []))
                        print(f"🔗 [{d.get('domain')}]")
                        print(f"   状态: {d.get('status')} | NS: {ns}")
                else:
                    print(f"❌ {domains}")
                
                await questionary.press_any_key_to_continue("按任意键返回主菜单...").ask_async()
                clear_screen()

            elif action == "2. 注册域名":
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
                print(f">> 结果: {result}")
                await questionary.press_any_key_to_continue("按任意键返回主菜单...").ask_async()
                clear_screen()

            elif action == "3. 修改记录 (NameServers)":
                print("🔍 正在拉取可操作域名...")
                domains = await client.list_domains()
                if not isinstance(domains, list) or not domains:
                    print(">> 没有可操作的域名。")
                    await asyncio.sleep(2)
                    clear_screen()
                    continue
                
                target = await questionary.select(
                    "请选择要修改的域名:",
                    choices=[d.get('domain') for d in domains]
                ).ask_async()
                
                ns_input = await questionary.text("请输入新的 DNS (逗号隔开):").ask_async()
                ns_list = [n.strip() for n in ns_input.split(",") if n.strip()]
                
                print(f"🚀 正在更新 {target} 的 DNS...")
                result = await client.update_dns(target, ns_list)
                print(f">> 结果: {result}")
                await questionary.press_any_key_to_continue("按任意键返回主菜单...").ask_async()
                clear_screen()

            elif action == "4. 删除域名":
                print("🔍 正在拉取可操作域名...")
                domains = await client.list_domains()
                if not isinstance(domains, list) or not domains:
                    print(">> 没有可操作的域名。")
                    await asyncio.sleep(2)
                    clear_screen()
                    continue
                
                target = await questionary.select(
                    "请选择要删除的域名:",
                    choices=[d.get('domain') for d in domains]
                ).ask_async()
                
                confirm = await questionary.confirm(f"⚠️ 确定要删除域名 {target} 吗？").ask_async()
                if confirm:
                    print(f"🔥 正在删除 {target}...")
                    result = await client.delete_domain(target)
                    print(f">> 结果: {result}")
                
                await questionary.press_any_key_to_continue("按任意键返回主菜单...").ask_async()
                clear_screen()

            elif action == "5. 切换账号":
                await client.close()
                clear_screen()
                return await interactive_menu()

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
