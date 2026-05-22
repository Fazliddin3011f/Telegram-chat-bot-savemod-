"""Chat Bot - Savollarga javob beruvchi aiogram bot.

Funksiyalar:
  - Oddiy savollarga javob berish
  - /start, /help komandalar
  - SaveMod bilan birgalikda ishlash (alohida process)

Ishga tushirish:
    python savemod/chatbot.py
"""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from dotenv import load_dotenv

# ----------------------- Konfiguratsiya -----------------------
load_dotenv()

BOT_TOKEN = os.getenv("CHAT_BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()  # Fallback to main bot token

OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "").strip()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("chatbot")

# ----------------------- Bot va Dispatcher -----------------------
if not BOT_TOKEN:
    raise SystemExit("CHAT_BOT_TOKEN yoki BOT_TOKEN .env faylida ko'rsatilmagan")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# ----------------------- Javoblar -----------------------
FAQ_RESPONSES = {
    "salom": "Assalomu alaykum! 👋\n\nSizga qanday yordam berishim mumkin?",
    "hello": "Hello! 👋\n\nHow can I help you today?",
    "qanday": "Men sizga quyidagi mavzularda yordam beraman:\n\n"
              "• 💎 TON sotib olish/sotish\n"
              "• ⭐ Telegram Stars sotib olish\n"
              "• 👤 Telegram Premium obuna\n"
              "• 💳 Karta orqali to'lov\n\n"
              "Savolingizni bemalol yozib qoldiring!",
    "narx": "💎 TON kursi doim yangilanib turadi.\n"
            "Joriy kursni bilish uchun @FragmentlyBot dan /ton buyrug'ini yuboring.",
    "ton": "💎 TON sotib olish uchun:\n\n"
           "1️⃣ @FragmentlyBot ga kiring\n"
           "2️⃣ /ton buyrug'ini yuboring\n"
           "3️⃣ Kerakli miqdorni tanlang\n"
           "4️⃣ To'lovni amalga oshiring\n\n"
           "Wallet manzilingizni va to'lov chekini yuboring.",
    "stars": "⭐ Telegram Stars sotib olish:\n\n"
             "1️⃣ @FragmentlyBot ga kiring\n"
             "2️⃣ /stars buyrug'ini yuboring\n"
             "3️⃣ Username va miqdorni kiriting\n"
             "4️⃣ To'lovni amalga oshiring",
    "premium": "👤 Telegram Premium obuna:\n\n"
               "1️⃣ @FragmentlyBot ga kiring\n"
               "2️⃣ /premium buyrug'ini yuboring\n"
               "3️⃣ Username va davomiylikni tanlang\n"
               "4️⃣ To'lovni amalga oshiring",
    "karta": "💳 Karta orqali to'lov:\n\n"
             "Karta ma'lumotlarini olish uchun @FragmentlyBot da /addkarta buyrug'ini yuboring.",
    "aloqa": "📞 Aloqa uchun:\n\n"
             "Telegram: @Fazliddin\n"
             "Bot: @FragmentlyBot",
    "yordam": "🆘 Yordam:\n\n"
              "• /start - Botni ishga tushirish\n"
              "• /help - Yordam olish\n"
              "• /faq - Ko'p so'raladigan savollar\n"
              "• /narx - TON narxi\n"
              "• /aloqa - Bog'lanish",
}

def get_faq_keyboard() -> InlineKeyboardMarkup:
    """FAQ tugmalari."""
    buttons = [
        [InlineKeyboardButton(text="💎 TON narx", callback_data="faq_narx")],
        [InlineKeyboardButton(text="⭐ Stars", callback_data="faq_stars")],
        [InlineKeyboardButton(text="👤 Premium", callback_data="faq_premium")],
        [InlineKeyboardButton(text="💳 Karta to'lov", callback_data="faq_karta")],
        [InlineKeyboardButton(text="📞 Aloqa", callback_data="faq_aloqa")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

# ----------------------- Handlers -----------------------
@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await message.answer(
        f"👋 Salom, <b>{message.from_user.full_name}</b>!\n\n"
        "Men savollaringizga javob beruvchi yordamchi botman.\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=get_faq_keyboard()
    )

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "🆘 <b>Yordam</b>\n\n"
        "Mavjud komandalar:\n"
        "• /start - Botni ishga tushirish\n"
        "• /help - Bu xabarni ko'rish\n"
        "• /faq - Ko'p so'raladigan savollar\n"
        "• /narx - TON narxi\n"
        "• /aloqa - Bog'lanish\n\n"
        "Savolingizni bemalol yozib qoldiring, men javob berishga harakat qilaman!"
    )

@router.message(Command("faq"))
async def cmd_faq(message: Message) -> None:
    await message.answer(
        "❓ <b>Ko'p so'raladigan savollar</b>\n\n"
        "Quyidagi mavzularda ma'lumot olishingiz mumkin:",
        reply_markup=get_faq_keyboard()
    )

@router.message(Command("narx"))
async def cmd_narx(message: Message) -> None:
    await message.answer(
        "💎 <b>TON narxi</b>\n\n"
        "Joriy kursni aniq bilish uchun @FragmentlyBot dan foydalaning.\n\n"
        "• /ton - TON kursi va hisoblash\n"
        "• /rate - Kursni sozlash"
    )

@router.message(Command("aloqa"))
async def cmd_aloqa(message: Message) -> None:
    await message.answer(
        "📞 <b>Aloqa</b>\n\n"
        "• Telegram: @Fazliddin\n"
        "• Asosiy bot: @FragmentlyBot\n\n"
        "Savollaringiz bo'lsa bemalol yozing! ✅"
    )

@router.message(F.text)
async def handle_text(message: Message) -> None:
    """Oddiy matnli xabarlarni qayta ishlash."""
    text = (message.text or "").lower().strip()
    
    # FAQ kalit so'zlarni tekshirish
    for key, response in FAQ_RESPONSES.items():
        if key in text:
            await message.answer(response)
            return
    
    # Default javob
    await message.answer(
        "🤔 Savolingizni tushunmadim.\n\n"
        "Quyidagi komandalardan foydalaning:\n"
        "• /help - Yordam olish\n"
        "• /faq - Ko'p so'raladigan savollar\n"
        "• /aloqa - Bog'lanish\n\n"
        "Yoki sizga qanday yordam berishim mumkin?"
    )

# ----------------------- Callback Handlers -----------------------
from aiogram.types import CallbackQuery

@router.callback_query(F.data.startswith("faq_"))
async def handle_faq_callback(callback: CallbackQuery) -> None:
    key = callback.data.replace("faq_", "")
    response = FAQ_RESPONSES.get(key, "Bu bo'lim hali tayyor emas.")
    await callback.message.edit_text(response, reply_markup=get_faq_keyboard())
    await callback.answer()

# ----------------------- Asosiy -----------------------
async def main() -> None:
    log.info("Chat Bot ishga tushmoqda...")
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("Chat Bot to'xtatildi.")
