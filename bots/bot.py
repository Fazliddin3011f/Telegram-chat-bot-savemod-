"""Fragmently Telegram bot — Stars va Premium sotib olish uchun.

Ishga tushirish:
    1) `pip install -r requirements.txt`
    2) `.env.example` ni `.env` ga ko'chiring va tokenlarni to'ldiring
    3) `python bot.py`
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    BotCommand,
    BotCommandScopeDefault,
    CallbackQuery,
    FSInputFile,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from dotenv import load_dotenv

from fragmently import FragmentlyClient, FragmentlyError


# ----------------------- Konfiguratsiya -----------------------
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FRAGMENTLY_TOKEN = os.getenv("FRAGMENTLY_TOKEN", "").strip()
_allowed_raw = os.getenv("ALLOWED_USER_IDS", "").strip()
ALLOWED_USER_IDS: set[int] = {
    int(x) for x in _allowed_raw.split(",") if x.strip().isdigit()
}
_admin_raw = os.getenv("ADMIN_USERNAMES", "").strip()
ADMIN_USERNAMES: set[str] = {
    x.strip().lstrip("@").lower()
    for x in _admin_raw.split(",")
    if x.strip()
}
TON_MARKUP_PERCENT = float(os.getenv("TON_MARKUP_PERCENT", "20").strip() or 20)
SETTINGS_FILE = Path("bot_settings.json")
KARTA_FILE = Path("karta.txt")
BACKUP_DIR = Path("backups")
TON_RATE_CACHE_SECONDS = 300

if not BOT_TOKEN:
    raise SystemExit("BOT_TOKEN .env faylida ko'rsatilmagan")
if not FRAGMENTLY_TOKEN:
    raise SystemExit("FRAGMENTLY_TOKEN .env faylida ko'rsatilmagan")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("fragmently-bot")


# ----------------------- API klient -----------------------
api = FragmentlyClient(FRAGMENTLY_TOKEN)


def load_settings() -> dict:
    if not SETTINGS_FILE.exists():
        return {}
    try:
        return json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Sozlamalarni o'qishda xatolik: %s", e)
        return {}


def save_settings(settings: dict) -> None:
    SETTINGS_FILE.write_text(
        json.dumps(settings, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


settings = load_settings()
TON_MARKUP_PERCENT = float(settings.get("ton_markup_percent", TON_MARKUP_PERCENT))
TON_MANUAL_RATE_UZS = settings.get("ton_manual_rate_uzs")
ton_rate_cache: dict[str, float | str] = {}


# ----------------------- FSM -----------------------
class StarsFlow(StatesGroup):
    username = State()
    quantity = State()
    confirm = State()


class PremiumFlow(StatesGroup):
    username = State()
    months = State()
    confirm = State()


class PriceFlow(StatesGroup):
    stars_qty = State()


# ----------------------- Yordamchi -----------------------
USERNAME_RE = re.compile(r"^@?[A-Za-z0-9_]{4,32}$")
TON_AMOUNT_RE = re.compile(r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?:ton|тон)\b", re.IGNORECASE)


def normalize_username(text: str) -> str | None:
    text = text.strip()
    if not USERNAME_RE.match(text):
        return None
    return text if text.startswith("@") else "@" + text


def is_allowed(user_id: int, username: str | None = None) -> bool:
    # Cheklov o'rnatilmagan bo'lsa - hammaga ochiq
    if not ALLOWED_USER_IDS and not ADMIN_USERNAMES:
        return True
    if user_id in ALLOWED_USER_IDS:
        return True
    if username and username.lower() in ADMIN_USERNAMES:
        return True
    return False


def main_menu_kb() -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(text="⭐ Stars sotib olish", callback_data="buy:stars"),
            InlineKeyboardButton(text="💎 Premium sotib olish", callback_data="buy:premium"),
        ],
        [
            InlineKeyboardButton(text="💰 Balans", callback_data="info:balance"),
        ],
        [
            InlineKeyboardButton(text="🧮 Stars narxi", callback_data="price:stars"),
            InlineKeyboardButton(text="🧮 Premium narxi", callback_data="price:premium"),
        ],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="menu:home")]
        ]
    )


WALLET_ERROR_HINTS = (
    "hamyon",
    "wallet",
    "ulanmagan",
    "topilmadi",
)


def is_wallet_error(detail: str) -> bool:
    if not detail:
        return False
    low = detail.lower()
    return any(h in low for h in WALLET_ERROR_HINTS)


def wallet_help_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔗 Hamyonni ulash (Fragmently)",
                    url="https://www.fragmently.uz",
                )
            ],
            [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="menu:home")],
        ]
    )


def format_api_error(detail: str) -> tuple[str, InlineKeyboardMarkup]:
    """API xatosi uchun foydalanuvchiga qulay matn va tugmalar qaytaradi."""
    if is_wallet_error(detail):
        text = (
            "⚠️ <b>TON hamyon ulanmagan yoki topilmadi</b>\n\n"
            f"API javobi: <code>{detail}</code>\n\n"
            "Bot xaridlarni amalga oshirishi uchun avval <b>Fragmently "
            "dashboard</b>ida TON hamyonni ulashingiz kerak.\n\n"
            "📝 <b>Qadamlar:</b>\n"
            "1️⃣ <a href=\"https://www.fragmently.uz\">fragmently.uz</a> ga kiring\n"
            "2️⃣ Profil → <b>Hamyonni ulash</b> tugmasini bosing\n"
            "3️⃣ Tonkeeper / TON Wallet orqali tasdiqlang\n"
            "4️⃣ Balansga TON yuboring va qaytadan urinib koʻring"
        )
        return text, wallet_help_kb()
    return f"❌ Xatolik: <code>{detail}</code>", back_kb()


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="menu:home")]
        ]
    )


def months_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="3 oy", callback_data="months:3"),
                InlineKeyboardButton(text="6 oy", callback_data="months:6"),
                InlineKeyboardButton(text="12 oy", callback_data="months:12"),
            ],
            [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="menu:home")],
        ]
    )


def confirm_kb(action: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"confirm:{action}"),
                InlineKeyboardButton(text="❌ Bekor qilish", callback_data="menu:home"),
            ]
        ]
    )


def fmt_ton(value) -> str:
    try:
        return f"{float(value):.4f} TON"
    except (TypeError, ValueError):
        return f"{value} TON"


def fmt_uzs(value: float) -> str:
    return f"{round(value):,}".replace(",", " ") + " so'm"


def fmt_percent(value: float) -> str:
    if value.is_integer():
        return str(int(value))
    return str(value).rstrip("0").rstrip(".")


async def get_ton_rate_uzs() -> tuple[float | None, str]:
    if TON_MANUAL_RATE_UZS:
        return float(TON_MANUAL_RATE_UZS), "ruchnoy"
    now = time.time()
    cached_rate = ton_rate_cache.get("rate")
    cached_source = ton_rate_cache.get("source")
    cached_at = float(ton_rate_cache.get("time") or 0)
    if cached_rate and cached_source and now - cached_at < TON_RATE_CACHE_SECONDS:
        return float(cached_rate), str(cached_source)
    usd_uzs = float(os.getenv("USD_UZS_RATE", "12700").strip() or 12700)
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.get(
                "https://api.coingecko.com/api/v3/simple/price",
                params={"ids": "the-open-network", "vs_currencies": "uzs,usd"},
            )
            resp.raise_for_status()
            data = resp.json()
        ton = data.get("the-open-network", {})
        rate = float(ton.get("uzs") or 0)
        if rate > 0:
            ton_rate_cache.update({"rate": rate, "source": "real", "time": now})
            return rate, "real"
        usd = float(ton.get("usd") or 0)
        if usd > 0:
            rate = usd * usd_uzs
            ton_rate_cache.update({"rate": rate, "source": "real", "time": now})
            return rate, "real"
    except Exception as e:
        log.warning("CoinGecko TON kursi xatolik: %s", e)
    try:
        async with httpx.AsyncClient(timeout=10, headers=headers) as client:
            resp = await client.get(
                "https://api.binance.com/api/v3/ticker/price",
                params={"symbol": "TONUSDT"},
            )
            resp.raise_for_status()
            usd = float(resp.json().get("price") or 0)
        if usd > 0:
            rate = usd * usd_uzs
            ton_rate_cache.update({"rate": rate, "source": "real", "time": now})
            return rate, "real"
    except Exception as e:
        log.warning("Binance TON kursi xatolik: %s", e)
    return None, "xato"


def extract_ton_amount(text: str) -> float | None:
    match = TON_AMOUNT_RE.search(text or "")
    if not match:
        return None
    try:
        amount = float(match.group("amount").replace(",", "."))
    except ValueError:
        return None
    return amount if amount > 0 else None


def ton_sales_reply(amount: float, rate: float, source: str = "real") -> str:
    markup_rate = rate * (1 + TON_MARKUP_PERCENT / 100)
    total = amount * markup_rate
    return (
        "Assalomu alaykum ✅\n\n"
        f"💎 <b>{amount:g} ton</b> bor\n"
        f"💰 Sizga kurs: <b>{fmt_uzs(markup_rate)}</b>\n\n"
        f"🧾 Jami: <b>{fmt_uzs(total)}</b>\n\n"
        "Olish uchun wallet manzilingizni va to'lov chekini yuboring."
    )


# ----------------------- Router -----------------------
router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        await message.answer("⛔ Sizga ushbu bot orqali xizmatdan foydalanishga ruxsat yo'q.")
        return
    await state.clear()
    name = message.from_user.first_name or "do'st"
    text = (
        f"👋 Assalomu alaykum, <b>{name}</b>!\n\n"
        "🪐 <b>Fragmently Bot</b>ga xush kelibsiz — bu bot orqali siz "
        "istalgan Telegram foydalanuvchisiga <b>Stars</b> yuborishingiz yoki "
        "<b>Premium</b> sovgʼa qilishingiz mumkin.\n\n"
        "✨ <b>Imkoniyatlar:</b>\n"
        "• ⭐ Stars sotib olish (kamida 50 dona)\n"
        "• 💎 Premium obuna (3 / 6 / 12 oy)\n"
        "• 💰 TON hamyon balansini koʻrish\n"
        "• 🧮 Stars va Premium narxlarini hisoblash\n\n"
        "👇 Quyidagi tugmalardan birini tanlang yoki /help buyrugʻini bosing:"
    )
    await message.answer(text, reply_markup=main_menu_kb(), disable_web_page_preview=True)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    text = (
        "ℹ️ <b>Yordam</b>\n\n"
        "<b>Buyruqlar:</b>\n"
        "/start — botni qayta ishga tushirish\n"
        "/menu — bosh menyu\n"
        "/balance — TON hamyon balansi\n"
        "/ton — TON kursi va ustama narx\n"
        "/rate — TON kursini auto/ruchnoy sozlash\n"
        "/markup — TON ustamasini sozlash\n"
        "/stars — ⭐ Stars sotib olish\n"
        "/premium — 💎 Premium sotib olish\n"
        "/cancel — joriy amalni bekor qilish\n"
        "/help — ushbu yordam\n\n"
        "<b>Qanday ishlatish:</b>\n"
        "1️⃣ ‘Stars sotib olish’ yoki ‘Premium’ tugmasini bosing\n"
        "2️⃣ Qabul qiluvchining @username’ini kiriting\n"
        "3️⃣ Miqdor yoki muddatni tanlang\n"
        "4️⃣ Narxni koʻring va tasdiqlang\n\n"
        "⚠️ Xaridlar Fragmently TON balansingizdan amalga oshiriladi.\n"
        "💬 Support: @fragmently_support"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("balance"))
async def cmd_balance(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    try:
        data = await api.get_balance()
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)
        return
    address = data.get('wallet_address', '—')
    bal_ton = data.get('balance_ton', 0)
    bal_usdt = data.get('balance_usdt')
    text = (
        "💰 <b>Hamyon ma'lumotlari</b>\n\n"
        f"📍 Manzil: <code>{address}</code>\n"
        f"💎 Balans TON: <b>{fmt_ton(bal_ton)}</b>"
    )
    if bal_usdt is not None:
        text += f"\n💵 Balans USDT: <b>{bal_usdt} USDT</b>"
    await message.answer(text, reply_markup=main_menu_kb())


@router.message(Command("ton"))
async def cmd_ton(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    amount = extract_ton_amount(message.text or "") or 1
    rate, source = await get_ton_rate_uzs()
    if rate is None:
        await message.answer("⚠️ Hozir real TON kursini olishda xatolik bo'ldi. Birozdan keyin qayta urinib ko'ring.")
        return
    text = ton_sales_reply(amount, rate, source)
    try:
        balance = await api.get_balance()
        bal_ton = float(balance.get("balance_ton") or 0)
        bal_uzs = bal_ton * rate * (1 + TON_MARKUP_PERCENT / 100)
        text += (
            f"\n\n💼 Hamyon balansi: <b>{fmt_ton(bal_ton)}</b>"
            f" (~{fmt_uzs(bal_uzs)})"
        )
    except FragmentlyError as e:
        log.warning("Balans olishda xatolik: %s", e.detail)
    await message.answer(text)


@router.message(Command("rate"))
async def cmd_rate(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    global TON_MANUAL_RATE_UZS
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        rate, source = await get_ton_rate_uzs()
        if rate is None:
            await message.answer("⚠️ Real TON kursini olishda xatolik bo'ldi.")
            return
        mode = "ruchnoy" if source == "ruchnoy" else "auto real"
        await message.answer(
            f"📊 TON kurs: <b>{fmt_uzs(rate)}</b>\n"
            f"⚙️ Rejim: <b>{mode}</b>\n\n"
            "Ruchnoy qo'yish: <code>/rate 42000</code>\n"
            "Real kursga qaytish: <code>/rate auto</code>"
        )
        return
    value = parts[1].strip().lower().replace(" ", "")
    if value in ("auto", "real"):
        TON_MANUAL_RATE_UZS = None
        settings.pop("ton_manual_rate_uzs", None)
        save_settings(settings)
        await message.answer("✅ TON kurs rejimi <b>auto real</b> qilindi.")
        return
    try:
        rate = float(value.replace(",", "."))
    except ValueError:
        await message.answer("⚠️ Kursni son qilib yozing. Masalan: <code>/rate 42000</code>")
        return
    if rate <= 0:
        await message.answer("⚠️ Kurs 0 dan katta bo'lishi kerak.")
        return
    TON_MANUAL_RATE_UZS = rate
    settings["ton_manual_rate_uzs"] = rate
    save_settings(settings)
    await message.answer(f"✅ TON ruchnoy kurs <b>{fmt_uzs(rate)}</b> qilib sozlandi.")


@router.message(Command("markup"))
async def cmd_markup(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    global TON_MARKUP_PERCENT
    parts = (message.text or "").split(maxsplit=1)
    if len(parts) == 1:
        await message.answer(
            f"📌 Hozirgi TON ustama: <b>{fmt_percent(TON_MARKUP_PERCENT)}%</b>\n\n"
            "O'zgartirish uchun: <code>/markup 35</code>"
        )
        return
    try:
        value = float(parts[1].replace("%", "").replace(",", ".").strip())
    except ValueError:
        await message.answer("⚠️ Foizni son qilib yozing. Masalan: <code>/markup 35</code>")
        return
    if value < 0 or value > 100:
        await message.answer("⚠️ Ustama 0 dan 100 gacha bo'lishi kerak.")
        return
    TON_MARKUP_PERCENT = value
    settings["ton_markup_percent"] = value
    save_settings(settings)
    await message.answer(f"✅ TON ustama <b>{fmt_percent(TON_MARKUP_PERCENT)}%</b> qilib sozlandi.")


@router.message(Command("addkarta"))
async def cmd_add_karta(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    text = (message.text or "").split(maxsplit=1)
    if len(text) == 1 or not text[1].strip():
        await message.answer(
            "⚠️ Karta matnini shu ko'rinishda yuboring:\n"
            "<code>/addkarta 💳 Karta orqali to'lov\\nKarta: 8600...</code>"
        )
        return
    KARTA_FILE.write_text(text[1].strip(), encoding="utf-8")
    await message.answer("✅ .karta uchun matn saqlandi.")


@router.message(F.text == "~")
async def cmd_send_backup(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    if not BACKUP_DIR.exists():
        await message.answer("⚠️ Hali backup papka yo'q.")
        return
    backups = sorted(BACKUP_DIR.glob("*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not backups:
        await message.answer("⚠️ Backup zip topilmadi.")
        return
    latest = backups[0]
    await message.answer_document(FSInputFile(latest), caption=f"📦 Oxirgi backup: {latest.name}")


@router.message(Command("stars"))
async def cmd_stars(message: Message, state: FSMContext) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    await state.set_state(StarsFlow.username)
    await message.answer(
        "⭐ <b>Stars sotib olish</b>\n\n"
        "Stars yuboriladigan Telegram username'ni kiriting.\n"
        "Masalan: <code>@durov</code>",
        reply_markup=cancel_kb(),
    )


@router.message(Command("premium"))
async def cmd_premium(message: Message, state: FSMContext) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    await state.set_state(PremiumFlow.username)
    await message.answer(
        "💎 <b>Premium sotib olish</b>\n\n"
        "Premium beriladigan Telegram username'ni kiriting.\n"
        "Masalan: <code>@durov</code>",
        reply_markup=cancel_kb(),
    )


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    await state.clear()
    await message.answer("🏠 Bosh menyu:", reply_markup=main_menu_kb())


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Bekor qilindi.", reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:home")
async def cb_home(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("🏠 Bosh menyu:", reply_markup=main_menu_kb())
    await call.answer()


# ---------- Balans ----------
@router.callback_query(F.data == "info:balance")
async def cb_balance(call: CallbackQuery) -> None:
    await call.answer("Yuklanmoqda...")
    try:
        data = await api.get_balance()
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await call.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        return
    address = data.get('wallet_address', '—')
    bal_ton = data.get('balance_ton', 0)
    bal_usdt = data.get('balance_usdt')
    text = (
        "💰 <b>Hamyon ma'lumotlari</b>\n\n"
        f"📍 Manzil: <code>{address}</code>\n"
        f"💎 Balans TON: <b>{fmt_ton(bal_ton)}</b>"
    )
    if bal_usdt is not None:
        text += f"\n💵 Balans USDT: <b>{bal_usdt} USDT</b>"
    await call.message.edit_text(text, reply_markup=back_kb())


# ---------- Stars narxi ----------
@router.callback_query(F.data == "price:stars")
async def cb_price_stars(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PriceFlow.stars_qty)
    await call.message.edit_text(
        "🧮 Nechta <b>Stars</b> uchun narxni hisoblay?\n"
        "Sonni kiriting (kamida 50). Masalan: <code>100</code>",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(PriceFlow.stars_qty)
async def msg_price_stars(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, butun son kiriting (masalan: 100).")
        return
    qty = int(message.text.strip())
    if qty < 50:
        await message.answer("⚠️ Stars miqdori kamida 50 bo'lishi kerak.")
        return
    await state.clear()
    try:
        data = await api.get_stars_price(qty)
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)
        return
    stars = data.get("stars", {})
    text = (
        f"⭐ <b>{stars.get('quantity', qty)} Stars</b> narxi\n\n"
        f"💵 Narx: <b>{fmt_ton(stars.get('price_ton'))}</b>\n"
        f"💼 Sizning balansingiz: <b>{fmt_ton(data.get('balance_ton'))}</b>\n"
        f"{'✅ Yetarli' if stars.get('can_afford') else '⚠️ Balans yetarli emas'}"
    )
    await message.answer(text, reply_markup=back_kb())


# ---------- Premium narxi ----------
@router.callback_query(F.data == "price:premium")
async def cb_price_premium(call: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="3 oy", callback_data="pricep:3"),
                InlineKeyboardButton(text="6 oy", callback_data="pricep:6"),
                InlineKeyboardButton(text="12 oy", callback_data="pricep:12"),
            ],
            [InlineKeyboardButton(text="◀️ Bosh menyu", callback_data="menu:home")],
        ]
    )
    await call.message.edit_text("💎 Premium muddatini tanlang:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data.startswith("pricep:"))
async def cb_price_premium_months(call: CallbackQuery) -> None:
    months = int(call.data.split(":")[1])
    await call.answer("Hisoblanmoqda...")
    try:
        data = await api.get_premium_price(months)
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await call.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        return
    text = (
        f"💎 <b>{months} oylik Premium</b> narxi\n\n"
        f"💵 Narx: <b>{fmt_ton(data.get('price_ton'))}</b>\n"
        f"💼 Sizning balansingiz: <b>{fmt_ton(data.get('balance_ton'))}</b>\n"
        f"{'✅ Yetarli' if data.get('can_afford') else '⚠️ Balans yetarli emas'}"
    )
    await call.message.edit_text(text, reply_markup=back_kb())


# ---------- Stars sotib olish ----------
@router.callback_query(F.data == "buy:stars")
async def cb_buy_stars(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(StarsFlow.username)
    await call.message.edit_text(
        "⭐ <b>Stars sotib olish</b>\n\n"
        "Stars yuboriladigan Telegram username'ni kiriting.\n"
        "Masalan: <code>@durov</code>",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(StarsFlow.username)
async def msg_stars_username(message: Message, state: FSMContext) -> None:
    username = normalize_username(message.text or "")
    if not username:
        await message.answer(
            "⚠️ Username noto'g'ri. Faqat harflar/raqamlar/_ va 5–32 ta belgi.\n"
            "Masalan: <code>@durov</code>"
        )
        return
    await state.update_data(username=username)
    await state.set_state(StarsFlow.quantity)
    await message.answer(
        f"✅ Qabul qiluvchi: <b>{username}</b>\n\n"
        "Endi Stars miqdorini kiriting (kamida 50). Masalan: <code>50</code>",
        reply_markup=cancel_kb(),
    )


@router.message(StarsFlow.quantity)
async def msg_stars_quantity(message: Message, state: FSMContext) -> None:
    if not message.text or not message.text.strip().isdigit():
        await message.answer("⚠️ Iltimos, butun son kiriting (masalan: 50).")
        return
    qty = int(message.text.strip())
    if qty < 50:
        await message.answer("⚠️ Stars miqdori kamida 50 bo'lishi kerak.")
        return
    data = await state.get_data()
    username = data["username"]
    # Narxni oldindan ko'rsatamiz
    try:
        price = await api.get_stars_price(qty)
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await message.answer(text, reply_markup=kb, disable_web_page_preview=True)
        await state.clear()
        return
    await state.update_data(quantity=qty)
    await state.set_state(StarsFlow.confirm)
    stars = price.get("stars", {})
    text = (
        "🧾 <b>Buyurtmani tasdiqlang</b>\n\n"
        f"👤 Qabul qiluvchi: <b>{username}</b>\n"
        f"⭐ Miqdor: <b>{qty} Stars</b>\n"
        f"💵 Narx: <b>{fmt_ton(stars.get('price_ton'))}</b>\n"
        f"💼 Balans: <b>{fmt_ton(price.get('balance_ton'))}</b>\n\n"
        "Davom etamizmi?"
    )
    await message.answer(text, reply_markup=confirm_kb("stars"))


@router.callback_query(F.data == "confirm:stars", StarsFlow.confirm)
async def cb_confirm_stars(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    username = data.get("username")
    qty = data.get("quantity")
    await state.clear()
    await call.message.edit_text("⏳ To'lov amalga oshirilmoqda...")
    await call.answer()
    try:
        result = await api.buy_stars(username, int(qty))
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await call.message.edit_text(
            f"❌ <b>Xarid amalga oshmadi.</b>\n\n{text}",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
        return
    cost_val = result.get('amount_ton')
    asset = result.get('payment_method', 'TON')
    text = (
        "✅ <b>Stars muvaffaqiyatli yuborildi!</b>\n\n"
        f"👤 Qabul qiluvchi: <b>{result.get('username', username)}</b>\n"
        f"⭐ Miqdor: <b>{result.get('quantity', qty)} Stars</b>\n"
        f"💵 To'landi: <b>{cost_val} {asset}</b>"
    )
    await call.message.edit_text(text, reply_markup=back_kb())


# ---------- Premium sotib olish ----------
@router.callback_query(F.data == "buy:premium")
async def cb_buy_premium(call: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(PremiumFlow.username)
    await call.message.edit_text(
        "💎 <b>Premium sotib olish</b>\n\n"
        "Premium beriladigan Telegram username'ni kiriting.\n"
        "Masalan: <code>@durov</code>",
        reply_markup=cancel_kb(),
    )
    await call.answer()


@router.message(PremiumFlow.username)
async def msg_premium_username(message: Message, state: FSMContext) -> None:
    username = normalize_username(message.text or "")
    if not username:
        await message.answer(
            "⚠️ Username noto'g'ri. Masalan: <code>@durov</code>"
        )
        return
    await state.update_data(username=username)
    await state.set_state(PremiumFlow.months)
    await message.answer(
        f"✅ Qabul qiluvchi: <b>{username}</b>\n\nPremium muddatini tanlang:",
        reply_markup=months_kb(),
    )


@router.callback_query(F.data.startswith("months:"), PremiumFlow.months)
async def cb_premium_months(call: CallbackQuery, state: FSMContext) -> None:
    months = int(call.data.split(":")[1])
    if months not in (3, 6, 12):
        await call.answer("Noto'g'ri muddat", show_alert=True)
        return
    data = await state.get_data()
    username = data["username"]
    try:
        price = await api.get_premium_price(months)
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await call.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        await state.clear()
        return
    await state.update_data(months=months)
    await state.set_state(PremiumFlow.confirm)
    text = (
        "🧾 <b>Buyurtmani tasdiqlang</b>\n\n"
        f"👤 Qabul qiluvchi: <b>{username}</b>\n"
        f"💎 Muddat: <b>{months} oy</b>\n"
        f"💵 Narx: <b>{fmt_ton(price.get('price_ton'))}</b>\n"
        f"💼 Balans: <b>{fmt_ton(price.get('balance_ton'))}</b>\n\n"
        "Davom etamizmi?"
    )
    await call.message.edit_text(text, reply_markup=confirm_kb("premium"))
    await call.answer()


@router.callback_query(F.data == "confirm:premium", PremiumFlow.confirm)
async def cb_confirm_premium(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    username = data.get("username")
    months = int(data.get("months"))
    await state.clear()
    await call.message.edit_text("⏳ To'lov amalga oshirilmoqda...")
    await call.answer()
    try:
        result = await api.buy_premium(username, months)
    except FragmentlyError as e:
        text, kb = format_api_error(e.detail)
        await call.message.edit_text(
            f"❌ <b>Xarid amalga oshmadi.</b>\n\n{text}",
            reply_markup=kb,
            disable_web_page_preview=True,
        )
        return
    cost_val = result.get('amount_ton')
    asset = result.get('payment_method', 'TON')
    text = (
        "✅ <b>Premium muvaffaqiyatli aktivlashtirildi!</b>\n\n"
        f"👤 Qabul qiluvchi: <b>{result.get('username', username)}</b>\n"
        f"💎 Muddat: <b>{months} oy</b>\n"
        f"💵 To'landi: <b>{cost_val} {asset}</b>"
    )
    await call.message.edit_text(text, reply_markup=back_kb())


# Universal access middleware via filter
@router.message()
async def fallback(message: Message) -> None:
    if not is_allowed(message.from_user.id, message.from_user.username):
        return
    await message.answer(
        "Buyruqni tushunmadim. /start yoki /menu ni bosing.",
        reply_markup=main_menu_kb(),
    )


# ----------------------- Entrypoint -----------------------
async def setup_bot_commands(bot: Bot) -> None:
    """Telegram ‘Menu’ tugmasi ostidagi buyruqlar ro'yxatini sozlash."""
    commands = [
        BotCommand(command="start", description="🚀 Botni ishga tushirish"),
        BotCommand(command="menu", description="🏠 Bosh menyu"),
        BotCommand(command="balance", description="💰 TON balansni ko'rish"),
        BotCommand(command="ton", description="💎 TON kursini hisoblash"),
        BotCommand(command="rate", description="📊 TON kursini sozlash"),
        BotCommand(command="markup", description="➕ TON ustamasini sozlash"),
        BotCommand(command="stars", description="⭐ Stars sotib olish"),
        BotCommand(command="premium", description="💎 Premium sotib olish"),
        BotCommand(command="cancel", description="❌ Joriy amalni bekor qilish"),
        BotCommand(command="help", description="ℹ️ Yordam va qo'llanma"),
    ]
    await bot.set_my_commands(commands, scope=BotCommandScopeDefault())


async def main() -> None:
    bot = Bot(
        BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    log.info(
        "Bot ishga tushdi (allowed_ids=%s, admin_usernames=%s)",
        ALLOWED_USER_IDS or "-",
        ADMIN_USERNAMES or "-",
    )
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await setup_bot_commands(bot)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Bot to'xtatildi.")
