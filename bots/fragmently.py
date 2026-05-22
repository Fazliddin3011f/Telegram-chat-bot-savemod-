"""Fragment API uchun async klient.

Hujjatlar: https://fragment-api.uz/api
Base URL: https://fragment-api.uz/api/v1
Auth: header `X-API-Key: <api-key>`
"""
from __future__ import annotations

from typing import Any

import httpx


BASE_URL = "https://fragment-api.uz/api/v1"


class FragmentlyError(Exception):
    """API tomonidan qaytarilgan xatolik (detail xabari bilan)."""

    def __init__(self, status_code: int, message: str, code: str | None = None):
        self.status_code = status_code
        self.message = message
        self.code = code
        super().__init__(f"[{status_code}] {code or 'ERROR'}: {message}")


class FragmentlyClient:
    def __init__(self, token: str, timeout: float = 30.0):
        self._token = token
        self._timeout = timeout

    def _headers(self) -> dict[str, str]:
        return {
            "X-API-Key": self._token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(
        self,
        path: str,
        *,
        json_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Barcha so'rovlar POST va JSON body formatida yuboriladi."""
        url = f"{BASE_URL}{path}"
        if json_data is None:
            json_data = {}
            
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            resp = await client.post(
                url, headers=self._headers(), json=json_data
            )
            
        try:
            data = resp.json()
        except Exception:
            data = {"ok": False, "message": resp.text or "Noma'lum xatolik", "code": "PARSE_ERROR"}

        # HTTP error yoki ok=False bo'lsa xatolik otamiz
        if resp.status_code >= 400 or not data.get("ok"):
            message = data.get("message") or "Noma'lum xatolik"
            code = data.get("code") or "HTTP_ERROR"
            raise FragmentlyError(resp.status_code, message, code)
            
        return data

    # ---------- GET INFO ----------
    async def get_info(self, username: str) -> dict[str, Any]:
        """Telegram foydalanuvchi ma'lumotlarini olish."""
        clean_username = username.lstrip("@")
        res = await self._request("/getInfo", json_data={"username": clean_username})
        return res.get("result") or {}

    # ---------- WALLET ----------
    async def get_balance(self) -> dict[str, Any]:
        """Loyiha hamyoni balansini olish."""
        res = await self._request("/wallet/balance")
        result = res.get("result") or {}
        # Eski bot.py bilan moslikni saqlash
        if "address" in result:
            result["wallet_address"] = result["address"]
        return result

    async def calculate_wallet(self) -> dict[str, Any]:
        """Loyiha hamyoni bilan nimalar olish mumkinligini hisoblash."""
        res = await self._request("/wallet/calculate")
        return res.get("result") or {}

    # ---------- PRICING ----------
    async def get_stars_price(self, quantity: int = 50) -> dict[str, Any]:
        """N ta Stars uchun TON narxini hisoblaydi."""
        res = await self._request("/stars/pricing", json_data={"amount": quantity})
        result = res.get("result") or {}
        price_info = result.get("price") or {}
        
        # Balansni alohida olib, expectationlar bilan moslashtiramiz
        bal_res = await self.get_balance()
        bal_ton = float(bal_res.get("balance_ton") or 0)
        
        price_ton = float(price_info.get("ton") or 0)
        can_afford = bal_ton >= price_ton
        
        return {
            "stars": {
                "quantity": result.get("amount", quantity),
                "price_ton": price_info.get("ton"),
                "price_usd": price_info.get("usd"),
                "can_afford": can_afford
            },
            "balance_ton": bal_ton
        }

    async def get_premium_price(self, months: int = 3) -> dict[str, Any]:
        """3/6/12 oylik Premium uchun TON narxini hisoblaydi."""
        res = await self._request("/premium/pricing")
        result = res.get("result") or {}
        packages = result.get("packages") or []
        
        target_pkg = None
        for pkg in packages:
            if int(pkg.get("months", 0)) == months:
                target_pkg = pkg
                break
        
        if not target_pkg:
            raise FragmentlyError(400, f"{months} oylik paket topilmadi", "PACKAGE_NOT_FOUND")
            
        price_ton = float(target_pkg.get("ton") or 0)
        
        bal_res = await self.get_balance()
        bal_ton = float(bal_res.get("balance_ton") or 0)
        
        can_afford = bal_ton >= price_ton
        
        return {
            "price_ton": target_pkg.get("ton"),
            "price_usd": target_pkg.get("usd"),
            "balance_ton": bal_ton,
            "can_afford": can_afford
        }

    # ---------- BUY ----------
    async def buy_stars(self, username: str, quantity: int) -> dict[str, Any]:
        """Berilgan @username uchun Stars sotib oladi."""
        clean_username = username.lstrip("@")
        res = await self._request(
            "/stars/buy",
            json_data={"amount": quantity, "username": clean_username},
        )
        result = res.get("result") or {}
        return {
            "username": result.get("username", username),
            "quantity": result.get("amount", quantity),
            "amount_ton": result.get("cost"),
            "payment_method": result.get("payment_method", "USDT")
        }

    async def buy_premium(self, username: str, months: int) -> dict[str, Any]:
        """Berilgan @username uchun Premium sotib oladi (3 / 6 / 12 oy)."""
        clean_username = username.lstrip("@")
        res = await self._request(
            "/premium/buy",
            json_data={"duration": months, "username": clean_username},
        )
        result = res.get("result") or {}
        return {
            "username": result.get("username", username),
            "duration": result.get("duration", months),
            "amount_ton": result.get("cost"),
            "payment_method": result.get("payment_method", "TON")
        }
