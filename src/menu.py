import asyncio
import os
import sys
import questionary
from src.config import load_users_from_json
from src.client import USKGClient

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
