import asyncio
import os
import sys
import httpx
import questionary
from dotenv import load_dotenv
from typing import List, Optional

# 加载环境变量
load_dotenv()

BASE_URL = "https://domain-api.digitalplat.org/api/v1"
API_TOKEN = os.getenv("USKG_API_TOKEN")

class USKGClient:
    def __init__(self, token: str):
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json"
        }
        self.client = httpx.AsyncClient(base_url=BASE_URL, headers=self.headers, timeout=15.0)

    async def list_domains(self):
        """获取域名列表"""
        response = await self.client.get("/domains")
        if response.status_code == 200:
            return response.json().get("data", [])
        return f"Error: {response.status_code} - {response.text}"

    async def register_domain(self, domain: str, slot_type: str, nameservers: List[str]):
        """注册新域名"""
        data = {
            "domain": domain,
            "slot_type": slot_type,
            "nameservers": nameservers
        }
        response = await self.client.post("/domains", json=data)
        return response.json()

    async def update_dns(self, domain: str, nameservers: List[str]):
        """更新 DNS 解析服务器"""
        data = {"nameservers": nameservers}
        response = await self.client.patch(f"/domains/{domain}/nameservers", json=data)
        return response.json()

    async def delete_domain(self, domain: str):
        """删除域名"""
        response = await self.client.delete(f"/domains/{domain}")
        return response.json()

    async def close(self):
        await self.client.aclose()

async def interactive_menu():
    if not API_TOKEN:
        print("鈿 [错误]: 未在环境变量或 .env 文件中找到 USKG_API_TOKEN。")
        print("请参考 .env.example 创建 .env 文件并填入您的 API Token。")
        return

    client = USKGClient(API_TOKEN)
    
    try:
        while True:
            action = await questionary.select(
                "请选择操作 (使用键盘上下键, 回车确认):",
                choices=[
                    "1. 列出所有域名",
                    "2. 注册新域名",
                    "3. 修改 DNS (Nameservers)",
                    "4. 删除域名",
                    "5. 退出程序"
                ],
                style=questionary.Style([
                    ('qmark', 'fg:#673ab7 bold'),
                    ('question', 'bold'),
                    ('answer', 'fg:#f44336 bold'),
                    ('pointer', 'fg:#673ab7 bold'),
                    ('highlighted', 'fg:#673ab7 bold'),
                    ('selected', 'fg:#cc5454'),
                    ('separator', 'fg:#cc5454'),
                    ('instruction', ''),
                ])
            ).ask_async()

            if action == "1. 列出所有域名":
                print("\n馃攞 正在获取列表...")
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
                slot_type = await questionary.select(
                    "请选择槽位类型:",
                    choices=["free", "paid", "subscription"]
                ).ask_async()
                ns_input = await questionary.text("请输入 DNS (多个用逗号隔开, 如 ns1.he.net,ns2.he.net):").ask_async()
                ns_list = [n.strip() for n in ns_input.split(",") if n.strip()]
                
                print(f"馃毃 正在注册 {domain}...")
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
                
                print(f"馃毃 正在更新 {target} 的 DNS...")
                result = await client.update_dns(target, ns_list)
                print(f">> 结果: {result}\n")

            elif action == "4. 删除域名":
                domains = await client.list_domains()
                if not isinstance(domains, list) or not domains:
                    print(">> 没有可操作的域名。\n")
                    continue
                
                target = await questionary.select(
                    "请选择要删除的域名 (警告: 删除不可撤销!):",
                    choices=[d.get('domain') for d in domains]
                ).ask_async()
                
                confirm = await questionary.confirm(f"确定要删除域名 {target} 吗？").ask_async()
                if confirm:
                    print(f"馃毃 正在删除 {target}...")
                    result = await client.delete_domain(target)
                    print(f">> 结果: {result}\n")

            elif action == "5. 退出程序":
                print("馃憢 再见！")
                break
    finally:
        await client.close()

if __name__ == "__main__":
    try:
        asyncio.run(interactive_menu())
    except KeyboardInterrupt:
        print("\n馃憢 用户中止程序。")
        sys.exit(0)
