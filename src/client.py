import httpx
from typing import List

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
