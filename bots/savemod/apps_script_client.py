"""Apps Script Client - Google Sheets bilan webhook orqali ishlash.

Bu modul Google Apps Script web app'iga so'rov yuboradi.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger("apps_script")

# Apps Script Web App URL
APPS_SCRIPT_URL = os.getenv("APPS_SCRIPT_URL", "").strip()
APPS_SCRIPT_TOKEN = os.getenv("APPS_SCRIPT_TOKEN", "your_secret_token_here").strip()


class AppsScriptClient:
    """Google Apps Script bilan ishlash uchun client."""

    def __init__(self):
        self.url = APPS_SCRIPT_URL
        self.token = APPS_SCRIPT_TOKEN
        self.enabled = bool(self.url)

        if not self.enabled:
            log.warning("APPS_SCRIPT_URL ko'rsatilmagan! Google Sheets o'chiq.")
        else:
            log.info(f"Apps Script ulangan: {self.url[:50]}...")

    async def _send_request(self, data: dict) -> dict:
        """Apps Script'ga POST so'rov yuborish."""
        if not self.enabled:
            return {"success": False, "error": "Apps Script not configured"}

        payload = {
            "token": self.token,
            **data
        }

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(
                    self.url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    log.info(f"Apps Script javob: {result}")
                    return result
                else:
                    error_msg = f"HTTP {resp.status_code}: {resp.text}"
                    log.error(error_msg)
                    return {"success": False, "error": error_msg}

        except Exception as e:
            error_msg = f"Apps Script so'rov xatolik: {e}"
            log.error(error_msg)
            return {"success": False, "error": str(e)}

    async def add_order(
        self,
        order_id: int,
        username: str,
        order_type: str = "Stars",
        amount: int = 0,
        price_uzs: float = 0.0,
        status: str = "Kutilmoqda",
        note: str = "",
    ) -> bool:
        """Yangi buyurtma qo'shish."""
        result = await self._send_request({
            "action": "addOrder",
            "order": {
                "order_id": order_id,
                "username": username,
                "order_type": order_type,
                "amount": amount,
                "price_uzs": price_uzs,
                "status": status,
                "stars_sent": False,
                "note": note,
            }
        })
        
        success = result.get("success", False)
        if success:
            log.info(f"✅ Buyurtma #{order_id} Google Sheets (Apps Script) ga qo'shildi")
        else:
            log.warning(f"⚠️ Buyurtma qo'shish xatolik: {result.get('error')}")
        
        return success

    async def update_payment(
        self,
        order_id: int,
        status: str,
        stars_sent: bool = False,
    ) -> bool:
        """To'lov holatini yangilash."""
        result = await self._send_request({
            "action": "updatePayment",
            "order_id": order_id,
            "status": status,
            "stars_sent": stars_sent,
        })
        
        success = result.get("success", False)
        if success:
            log.info(f"✅ Buyurtma #{order_id} status yangilandi: {status}")
        else:
            log.warning(f"⚠️ Status yangilash xatolik: {result.get('error')}")
        
        return success

    async def get_stats(self) -> dict:
        """Statistikani olish."""
        result = await self._send_request({
            "action": "getStats",
        })
        return result

    async def get_daily_report(self) -> dict:
        """Kunlik hisobot."""
        result = await self._send_request({
            "action": "getDailyReport",
        })
        return result

    async def find_by_username(self, username: str) -> dict:
        """Username bo'yicha buyurtma qidirish."""
        result = await self._send_request({
            "action": "findByUsername",
            "username": username,
        })
        return result

    async def update_order_by_id_or_username(
        self,
        order_id: int = None,
        username: str = None,
        status: str = None,
        stars_sent: bool = None,
        new_username: str = None,
    ) -> bool:
        """ID yoki username bo'yicha yangilash.
        
        Username o'zgarganda ham buyurtmani topib yangilaydi.
        """
        updates = {}
        if status:
            updates["status"] = status
        if stars_sent is not None:
            updates["stars_sent"] = stars_sent
        if new_username:
            updates["username"] = new_username

        result = await self._send_request({
            "action": "updateOrderByIdOrUsername",
            "order_id": order_id,
            "username": username,
            "updates": updates,
        })
        
        success = result.get("success", False)
        if success:
            log.info(f"✅ Buyurtma yangilandi (ID: {order_id} yoki @{username})")
        else:
            log.warning(f"⚠️ Yangilash xatolik: {result.get('error')}")
        
        return success

    async def test_connection(self) -> bool:
        """Ulanishni tekshirish."""
        if not self.enabled:
            return False

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(self.url)
                if resp.status_code == 200:
                    data = resp.json()
                    log.info(f"✅ Apps Script test: {data.get('message')}")
                    return True
                return False
        except Exception as e:
            log.error(f"❌ Test xatolik: {e}")
            return False


# Global client instance
apps_script = AppsScriptClient()


# ============================================
# Yordamchi funksiyalar
# ============================================

async def add_order_to_sheets(**kwargs) -> bool:
    """Yangi buyurtma qo'shish (qo'llab-quvvatlash uchun)."""
    return await apps_script.add_order(**kwargs)


async def update_order_payment(order_id: int, status: str, stars_sent: bool = False) -> bool:
    """To'lov holatini yangilash."""
    return await apps_script.update_payment(order_id, status, stars_sent)


async def get_sheets_stats() -> dict:
    """Statistikani olish."""
    return await apps_script.get_stats()


async def find_order_by_username(username: str) -> dict:
    """Username bo'yicha buyurtma qidirish.
    
    Username o'zgarganda ham topadi (oxirgi buyurtma).
    """
    return await apps_script.find_by_username(username)


async def update_order_by_username(
    username: str,
    status: str = None,
    stars_sent: bool = None,
    new_username: str = None,
) -> bool:
    """Username bo'yicha buyurtma yangilash.
    
    Args:
        username: Qidirilayotgan username
        status: Yangi status (To'langan, Kutilmoqda, Bekor qilindi)
        stars_sent: Stars yuborilgani haqi
        new_username: Yangi username (agar o'zgargan bo'lsa)
    """
    return await apps_script.update_order_by_id_or_username(
        username=username,
        status=status,
        stars_sent=stars_sent,
        new_username=new_username,
    )


async def test_sheets_connection() -> bool:
    """Ulanishni tekshirish."""
    return await apps_script.test_connection()
