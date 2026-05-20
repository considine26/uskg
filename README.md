# US.KG 域名管理工具 (USKG Manager)

这是一个基于 Python 的命令行交互式工具，用于管理 [US.KG](https://nic.us.kg/) 域名（通过 DigitalPlat API）。它支持多账号配置、域名注册、DNS 修改、列表查看等功能。

## 🚀 功能特性

- **多账号支持**：在 `users.json` 文件中配置多个账号，程序运行后可自由切换。
- **交互式菜单**：使用 `questionary` 提供流畅的命令行交互体验。
- **全生命周期管理**：
  - 🔍 **查看域名**：获取账号下所有域名及其状态、NameServers。
  - 🆕 **注册域名**：一键注册新域名（支持 free/paid/subscription 槽位）。
  - 🛠️ **修改 DNS**：便捷修改域名的 NameServers 记录。
  - 🗑️ **删除域名**：释放不再需要的域名。
- **异步驱动**：基于 `httpx` 和 `asyncio`，响应迅速。

## 🛠️ 安装步骤

1. **克隆/下载项目**
2. **安装依赖**（建议在虚拟环境中进行）：
   ```bash
   pip install httpx questionary
   ```
   或者如果你使用 `uv`：
   ```bash
   uv sync
   ```

## ⚙️ 配置说明

在项目根目录下配置 `users.json` 文件，用于存放账号信息与 API Base URL。格式如下：

```json
{
    "version": "1.0",
    "api_base_url": "https://domain-api.digitalplat.org/api/v1",
    "profiles": {
        "User1": {
            "mail": "user1@example.com",
            "api_token": "your_token_here_1"
        },
        "User2": {
            "mail": "user2@example.com",
            "api_token": "your_token_here_2"
        }
    }
}
```

> **注意**：`api_token` 可以从 DigitalPlat 控制面板获取。

## 📖 使用指南

直接运行 `main.py` 即可进入交互界面：

```bash
python main.py
```

### 操作流程：
1. **选择账号**：如果配置了多个账号，程序会提示选择当前操作的账号。
2. **主菜单**：
   - **查看域名**：列出当前账号下的所有域名及其 NS 记录。
   - **注册域名**：输入域名名称、选择槽位类型、输入 DNS（多个 DNS 用逗号分隔）。
   - **修改记录**：从列表中选择一个域名，输入新的 DNS。
   - **删除域名**：从列表中选择一个域名并确认删除。
   - **切换账号**：返回账号选择界面。
   - **退出程序**：安全关闭连接并退出。

## ⚠️ 常见问题

- **403 错误**：通常是 API Token 无效或过期，请检查 `users.json` 配置。
- **网络错误**：请检查网络连接，或确保能够访问 `domain-api.digitalplat.org`。
- **注册失败**：请检查域名是否符合规则，或者对应的槽位（Slot）是否已满。

## 📄 许可证

MIT License
