"""Google Sheets integratsiya - Buyurtmalar va to'lovlarni yozish.

Funksiyalar:
  - Yangi buyurtmalarni avto yozish
  - To'lov holatini yangilash
  - Statistika va hisobotlar
  - Chiroyli formatlash (ranglar, borderlar)
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import gspread
from google.oauth2.service_account import Credentials
from gspread.utils import rowcol_to_a1

load_dotenv = lambda: None
from dotenv import load_dotenv as _load_dotenv
_load_dotenv()

log = logging.getLogger("google_sheets")

# ----------------------- Konfiguratsiya -----------------------
SPREADSHEET_ID = os.getenv("GOOGLE_SHEETS_ID", "").strip()
CREDENTIALS_FILE = Path(__file__).resolve().parent / "credentials.json"

# Dizayn ranglari
COLORS = {
    "header_bg": {"red": 0.12, "green": 0.56, "blue": 0.92},      # #2196F3 - Moviy
    "pending": {"red": 1.0, "green": 0.76, "blue": 0.03},        # #FFC107 - Sariq
    "paid": {"red": 0.3, "green": 0.69, "blue": 0.31},           # #4CAF50 - Yashil
    "failed": {"red": 0.96, "green": 0.26, "blue": 0.21},        # #F44336 - Qizil
    "stripe": {"red": 0.95, "green": 0.95, "blue": 0.95},       # Kulrang (qatorlar)
    "white": {"red": 1, "green": 1, "blue": 1},
}


class GoogleSheetsManager:
    """Google Sheets bilan ishlash uchun manager."""

    def __init__(self):
        self.client = None
        self.spreadsheet = None
        self._connect()

    def _connect(self) -> None:
        """Google Sheets API ga ulanish."""
        if not CREDENTIALS_FILE.exists():
            log.warning("credentials.json fayli topilmadi!")
            return

        try:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            creds = Credentials.from_service_account_file(
                str(CREDENTIALS_FILE), scopes=scopes
            )
            self.client = gspread.authorize(creds)

            if SPREADSHEET_ID:
                self.spreadsheet = self.client.open_by_key(SPREADSHEET_ID)
                log.info("Google Sheets ulanish muvaffaqiyatli!")
                self._init_sheets()
            else:
                log.warning("GOOGLE_SHEETS_ID ko'rsatilmagan!")

        except Exception as e:
            log.error(f"Google Sheets ulanish xatolik: {e}")

    def _init_sheets(self) -> None:
        """Boshlang'ich sheetlarni yaratish."""
        if not self.spreadsheet:
            return

        # Asosiy sheetlar
        required_sheets = ["Buyurtmalar", "Statistika", "Mijozlar"]
        existing = [sheet.title for sheet in self.spreadsheet.worksheets()]

        for sheet_name in required_sheets:
            if sheet_name not in existing:
                self.spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
                log.info(f"Yangi sheet yaratildi: {sheet_name}")

        # Buyurtmalar sheet formatlash
        self._format_orders_sheet()
        self._format_stats_sheet()

    def _format_orders_sheet(self) -> None:
        """Buyurtmalar sheet ni chiroyli formatlash."""
        try:
            sheet = self.spreadsheet.worksheet("Buyurtmalar")

            # Header qator
            headers = [
                "ID", "Sana", "Mijoz", "Username", "Turi", "Miqdor",
                "Narx (UZS)", "To'lov holati", "Stars yuborildi", "Izoh"
            ]

            # Agar bo'sh bo'lsa, header yozish
            if not sheet.acell("A1").value:
                sheet.update("A1:J1", [headers])

                # Header formatlash
                header_format = {
                    "backgroundColor": COLORS["header_bg"],
                    "textFormat": {"bold": True, "foregroundColor": {"red": 1, "green": 1, "blue": 1}},
                    "horizontalAlignment": "CENTER",
                    "verticalAlignment": "MIDDLE",
                }
                sheet.format("A1:J1", header_format)

                # Ustun kengliklari
                sheet.set_column_width(1, 50)   # ID
                sheet.set_column_width(2, 120)  # Sana
                sheet.set_column_width(3, 150)  # Mijoz
                sheet.set_column_width(4, 120)  # Username
                sheet.set_column_width(5, 80)  # Turi
                sheet.set_column_width(6, 80)  # Miqdor
                sheet.set_column_width(7, 100) # Narx
                sheet.set_column_width(8, 120) # Holat
                sheet.set_column_width(9, 120) # Stars
                sheet.set_column_width(10, 200) # Izoh

                # Freeze header
                sheet.freeze(rows=1)

            log.info("Buyurtmalar sheet formatlandi")

        except Exception as e:
            log.warning(f"Formatlash xatolik: {e}")

    def _format_stats_sheet(self) -> None:
        """Statistika sheet formatlash."""
        try:
            sheet = self.spreadsheet.worksheet("Statistika")

            stats_data = [
                ["📊 UMUMIY STATISTIKA", ""],
                ["", ""],
                ["Ko'rsatkich", "Qiymat"],
                ["Jami buyurtmalar", "=COUNTA('Buyurtmalar'!A:A)-1"],
                ["To'langan buyurtmalar", "=COUNTIF('Buyurtmalar'!H:H,\"To'langan\")"],
                ["Kutilayotgan buyurtmalar", "=COUNTIF('Buyurtmalar'!H:H,\"Kutilmoqda\")"],
                ["", ""],
                ["💰 MOLIYAVIY", ""],
                ["Jami tushum (UZS)", "=SUMIF('Buyurtmalar'!H:H,\"To'langan\",'Buyurtmalar'!G:G)"],
                ["Kutilayotgan summa", "=SUMIF('Buyurtmalar'!H:H,\"Kutilmoqda\",'Buyurtmalar'!G:G)"],
                ["", ""],
                ["⭐ STARS", ""],
                ["Jami stars sotildi", "=SUMIF('Buyurtmalar'!H:H,\"To'langan\",'Buyurtmalar'!F:F)"],
                ["", ""],
                ["📅 OYLIK STATISTIKA", ""],
                ["Bu oy", "=SUMIFS('Buyurtmalar'!G:G,'Buyurtmalar'!H:H,\"To'langan\",'Buyurtmalar'!B:B,\">\"&EOMONTH(TODAY(),-1)+1)"],
            ]

            # Ma'lumotlarni yozish
            for i, row in enumerate(stats_data, 1):
                sheet.update(f"A{i}:B{i}", [row])

            # Formatlash
            sheet.format("A1", {
                "textFormat": {"bold": True, "fontSize": 14},
                "backgroundColor": COLORS["header_bg"],
            })

            sheet.set_column_width(1, 200)
            sheet.set_column_width(2, 150)

            log.info("Statistika sheet formatlandi")

        except Exception as e:
            log.warning(f"Statistika formatlash xatolik: {e}")

    def add_order(
        self,
        order_id: int,
        username: str,
        order_type: str,  # "Stars", "Premium", "TON"
        amount: int,
        price_uzs: float,
        status: str = "Kutilmoqda",
        note: str = "",
    ) -> bool:
        """Yangi buyurtma qo'shish."""
        if not self.spreadsheet:
            return False

        try:
            sheet = self.spreadsheet.worksheet("Buyurtmalar")

            # Joriy qatorni topish
            all_values = sheet.get_all_values()
            next_row = len(all_values) + 1

            # Sana
            now = datetime.now().strftime("%d.%m.%Y %H:%M")

            # Ma'lumotlar
            row_data = [
                order_id,
                now,
                username,  # Ism (keyin to'ldiriladi)
                f"@{username}",
                order_type,
                amount,
                price_uzs,
                status,
                "Yo'q",  # Stars yuborildi
                note,
            ]

            # Yozish
            range_name = f"A{next_row}:J{next_row}"
            sheet.update(range_name, [row_data])

            # Rang formatlash
            if status == "Kutilmoqda":
                bg_color = COLORS["pending"]
            elif status == "To'langan":
                bg_color = COLORS["paid"]
            else:
                bg_color = COLORS["failed"]

            # Juft/toq qatorlar uchun almashtirish
            if next_row % 2 == 0:
                bg_color = COLORS["stripe"]

            sheet.format(range_name, {
                "backgroundColor": bg_color,
                "horizontalAlignment": "CENTER",
                "verticalAlignment": "MIDDLE",
                "borders": {
                    "top": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                    "bottom": {"style": "SOLID", "width": 1, "color": {"red": 0.8, "green": 0.8, "blue": 0.8}},
                }
            })

            log.info(f"Buyurtma #{order_id} Sheets ga qo'shildi")
            return True

        except Exception as e:
            log.error(f"Buyurtma qo'shish xatolik: {e}")
            return False

    def update_payment_status(
        self,
        order_id: int,
        status: str,  # "To'langan", "Bekor qilindi"
        stars_sent: bool = False,
    ) -> bool:
        """To'lov holatini yangilash."""
        if not self.spreadsheet:
            return False

        try:
            sheet = self.spreadsheet.worksheet("Buyurtmalar")

            # Order ID ni qidirish
            all_values = sheet.get_all_values()
            for i, row in enumerate(all_values, 1):
                if row and str(row[0]) == str(order_id):
                    # Status yangilash (H ustun - 8-index)
                    sheet.update_cell(i, 8, status)

                    # Stars yuborilganini yangilash (I ustun - 9-index)
                    sheet.update_cell(i, 9, "Ha" if stars_sent else "Yo'q")

                    # Rang yangilash
                    range_name = f"A{i}:J{i}"
                    if status == "To'langan":
                        bg_color = COLORS["paid"]
                    elif status == "Bekor qilindi":
                        bg_color = COLORS["failed"]
                    else:
                        bg_color = COLORS["pending"]

                    sheet.format(range_name, {
                        "backgroundColor": bg_color,
                    })

                    log.info(f"Buyurtma #{order_id} status yangilandi: {status}")
                    return True

            log.warning(f"Buyurtma #{order_id} topilmadi")
            return False

        except Exception as e:
            log.error(f"Status yangilash xatolik: {e}")
            return False

    def get_daily_report(self) -> dict[str, Any]:
        """Kunlik hisobot."""
        if not self.spreadsheet:
            return {}

        try:
            sheet = self.spreadsheet.worksheet("Buyurtmalar")
            all_values = sheet.get_all_values()[1:]  # Header o'tkazib yuborish

            today = datetime.now().strftime("%d.%m.%Y")
            today_orders = [row for row in all_values if row[1].startswith(today)]

            total = len(today_orders)
            paid = len([r for r in today_orders if r[7] == "To'langan"])
            revenue = sum(float(r[6]) for r in today_orders if r[7] == "To'langan")

            return {
                "date": today,
                "total_orders": total,
                "paid_orders": paid,
                "pending_orders": total - paid,
                "revenue": revenue,
            }

        except Exception as e:
            log.error(f"Hisobot olish xatolik: {e}")
            return {}


# Global instance
gs_manager = GoogleSheetsManager()


# ----------------------- Yordamchi funksiyalar -----------------------
def add_order_to_sheets(**kwargs) -> bool:
    """Yangi buyurtma qo'shish (qo'llab-quvvatlash uchun)."""
    return gs_manager.add_order(**kwargs)


def update_order_payment(order_id: int, status: str, stars_sent: bool = False) -> bool:
    """To'lov holatini yangilash."""
    return gs_manager.update_payment_status(order_id, status, stars_sent)


def get_today_report() -> dict:
    """Bugungi hisobot."""
    return gs_manager.get_daily_report()
