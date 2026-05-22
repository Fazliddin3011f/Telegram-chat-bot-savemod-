"""Payment Monitor - HUMO Card to'lovlarni kuzatish va avto stars.

Funksiyalar:
  - HUMO Card bot xabarlarini pars qilish
  - Pul tushishini aniqlash
  - Avtomatik stars yuborish (Fragmently API orqali)
  - Buyurtma ma'lumotlarini saqlash
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx
from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import User

# Apps Script integratsiyasi (Google Sheets bilan webhook orqali)
try:
    from apps_script_client import add_order_to_sheets, update_order_payment
    APPS_SCRIPT_ENABLED = True
except ImportError:
    APPS_SCRIPT_ENABLED = False
    log = logging.getLogger("payment_monitor")
    log.warning("Apps Script moduli topilmadi!")

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
PHONE = os.getenv("PHONE", "").strip()

FRAGMENTLY_TOKEN = os.getenv("FRAGMENTLY_TOKEN", "").strip()
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "").strip()
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

HUMO_BOT_USERNAME = "HUMOCardbot"  # HUMO Card bot username

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("payment_monitor")

client = TelegramClient("payment_monitor.session", API_ID, API_HASH)

# DB - Buyurtmalar uchun
DB_FILE = Path("orders.db")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            stars_amount INTEGER NOT NULL,
            price_uzs REAL NOT NULL,
            payment_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            paid_at TIMESTAMP,
            stars_sent BOOLEAN DEFAULT FALSE
        )
    ''')
    conn.commit()
    conn.close()

async def add_order(username: str, stars_amount: int, price_uzs: float) -> int:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "INSERT INTO orders (username, stars_amount, price_uzs) VALUES (?, ?, ?)",
        (username, stars_amount, price_uzs)
    )
    order_id = c.lastrowid
    conn.commit()
    conn.close()
    
    # Apps Script (Google Sheets) ga ham qo'shish
    if APPS_SCRIPT_ENABLED:
        try:
            await add_order_to_sheets(
                order_id=order_id,
                username=username,
                order_type="Stars",
                amount=stars_amount,
                price_uzs=price_uzs,
                status="Kutilmoqda",
                note=f"Telegram: @{username}"
            )
            log.info(f"✅ Buyurtma #{order_id} Google Sheets (Apps Script) ga qo'shildi")
        except Exception as e:
            log.warning(f"⚠️ Apps Script ga yozish xatolik: {e}")
    
    return order_id

def find_pending_order(amount: float) -> dict | None:
    """Berilgan summaga yaqin pending order topish."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # 5% chetki bilan qidirish
    c.execute(
        """
        SELECT * FROM orders 
        WHERE payment_status = 'pending' 
        AND ABS(price_uzs - ?) < (price_uzs * 0.05)
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (amount,)
    )
    row = c.fetchone()
    conn.close()
    if row:
        return {
            "id": row[0],
            "username": row[1],
            "stars_amount": row[2],
            "price_uzs": row[3],
            "payment_status": row[4],
        }
    return None

def mark_order_paid(order_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET payment_status = 'paid', paid_at = CURRENT_TIMESTAMP WHERE id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()

async def mark_stars_sent(order_id: int):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "UPDATE orders SET stars_sent = TRUE WHERE id = ?",
        (order_id,)
    )
    conn.commit()
    conn.close()
    
    # Apps Script (Google Sheets) da ham yangilash
    if APPS_SCRIPT_ENABLED:
        try:
            await update_order_payment(order_id, "To'langan", stars_sent=True)
            log.info(f"✅ Buyurtma #{order_id} Google Sheets (Apps Script) da yangilandi")
        except Exception as e:
            log.warning(f"⚠️ Apps Script yangilash xatolik: {e}")

# ----------------------- HUMO Card Pars -----------------------
def parse_humo_message(text: str) -> dict | None:
    """HUMO Card xabaridan ma'lumot ajratib olish."""
    if not text:
        return None
    
    # Summa: 50,000.00 UZS yoki 50000 UZS
    amount_match = re.search(r'([\d\s,.]+)\s*UZS', text)
    if not amount_match:
        return None
    
    amount_str = amount_match.group(1).replace(" ", "").replace(",", "")
    try:
        amount = float(amount_str)
    except ValueError:
        return None
    
    # Kartadan keldi (pul tushdi)
    is_incoming = any(word in text.lower() for word in ['поступление', 'tushdi', 'postuplenie', 'зачисление'])
    # Kartadan ketdi (pul yechildi)  
    is_outgoing = any(word in text.lower() for word in ['списание', 'ketdi', 'snoshenie', 'оплата'])
    
    # Karta raqamini olish (oxirgi 4 raqam)
    card_match = re.search(r'\*?(\d{4})', text)
    card_last4 = card_match.group(1) if card_match else None
    
    return {
        "amount": amount,
        "is_incoming": is_incoming,
        "is_outgoing": is_outgoing,
        "card_last4": card_last4,
        "raw_text": text
    }

# ----------------------- Fragmently API -----------------------
async def send_stars_via_fragmently(username: str, amount: int) -> bool:
    """Fragmently API orqali stars yuborish."""
    if not FRAGMENTLY_TOKEN:
        log.error("FRAGMENTLY_TOKEN yo'q!")
        return False
    
    # @ ni olib tashlash
    username = username.lstrip("@")
    
    url = "https://fragment.ly/api/stars/buy"
    headers = {
        "Authorization": f"Bearer {FRAGMENTLY_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "username": username,
        "amount": amount
    }
    
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, headers=headers, json=payload, timeout=30)
            if resp.status_code == 200:
                log.info(f"✅ Stars yuborildi: @{username} - {amount} stars")
                return True
            else:
                log.error(f"❌ Stars yuborish xato: {resp.status_code} - {resp.text}")
                return False
    except Exception as e:
        log.error(f"❌ Stars yuborishda xatolik: {e}")
        return False

async def notify_owner(text: str):
    """Egasiga xabar yuborish."""
    if not OWNER_CHAT_ID or not BOT_TOKEN:
        return
    
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": OWNER_CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10)
    except Exception as e:
        log.warning(f"Xabar yuborishda xato: {e}")

# ----------------------- Event Handlers -----------------------
@client.on(events.NewMessage(incoming=True))
async def on_humo_message(event):
    """HUMO Card botdan xabar kelganda."""
    msg = event.message
    
    # Faqat HUMO Card botdan kelgan xabarlarni tekshirish
    sender = await event.get_sender()
    if not isinstance(sender, User):
        return
    
    sender_username = sender.username or ""
    if HUMO_BOT_USERNAME.lower() not in sender_username.lower():
        return  # HUMO bot emas
    
    text = msg.message or ""
    log.info(f"📨 HUMO xabar: {text[:100]}...")
    
    # Xabarni pars qilish
    data = parse_humo_message(text)
    if not data:
        return
    
    if not data["is_incoming"]:
        log.info("💸 Pul ketdi (outgoing), skip")
        return
    
    amount = data["amount"]
    log.info(f"💰 Pul tushdi: {amount:,.0f} UZS")
    
    # Bu summa uchun pending order borligini tekshirish
    order = find_pending_order(amount)
    
    if order:
        log.info(f"✅ Buyurtma topildi: #{order['id']} - @{order['username']} - {order['stars_amount']} stars")
        
        # Orderni paid qilib belgilash
        mark_order_paid(order['id'])
        
        # Ownerga xabar
        await notify_owner(
            f"💰 <b>Yangi to'lov!</b>\n\n"
            f"Summa: <b>{amount:,.0f} UZS</b>\n"
            f"Buyurtma: #{order['id']}\n"
            f"Mijoz: @{order['username']}\n"
            f"Stars: {order['stars_amount']}\n\n"
            f"Avto yuborilmoqda..."
        )
        
        # Stars yuborish
        success = await send_stars_via_fragmently(order['username'], order['stars_amount'])
        
        if success:
            await mark_stars_sent(order['id'])
            await notify_owner(
                f"✅ <b>Stars yuborildi!</b>\n\n"
                f"Mijoz: @{order['username']}\n"
                f"Miqdor: {order['stars_amount']} stars\n"
                f"Buyurtma: #{order['id']}"
            )
        else:
            await notify_owner(
                f"❌ <b>Stars yuborishda xatolik!</b>\n\n"
                f"Mijoz: @{order['username']}\n"
                f"Buyurtma: #{order['id']}\n\n"
                f"Qo'lda tekshiring!"
            )
    else:
        log.info(f"⚠️ Bu summa uchun buyurtma topilmadi: {amount:,.0f} UZS")
        await notify_owner(
            f"⚠️ <b>Noma'lum to'lov</b>\n\n"
            f"Summa: <b>{amount:,.0f} UZS</b>\n"
            f"Bu summa uchun buyurtma topilmadi.\n\n"
            f"Qo'lda tekshiring!"
        )

# ----------------------- Manual Order Creation -----------------------
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.order\s+@?(\w+)\s+(\d+)\s+(\d+(?:\.\d+)?)$"))
async def cmd_create_order(event):
    """.order @username stars_amount price_uzs"""
    match = event.pattern_match
    username = match.group(1)
    stars = int(match.group(2))
    price = float(match.group(3))
    
    order_id = await add_order(username, stars, price)
    
    await event.edit(
        f"✅ <b>Buyurtma yaratildi!</b>\n\n"
        f"ID: #{order_id}\n"
        f"Mijoz: @{username}\n"
        f"Stars: {stars}\n"
        f"Narx: {price:,.0f} UZS\n\n"
        f"Mijoz pul tashashini kutyapmiz..."
    )

@client.on(events.NewMessage(outgoing=True, pattern=r"^\.orders$"))
async def cmd_list_orders(event):
    """Barcha pending buyurtmalarni ko'rish."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT id, username, stars_amount, price_uzs, created_at FROM orders "
        "WHERE payment_status = 'pending' ORDER BY created_at DESC"
    )
    rows = c.fetchall()
    conn.close()
    
    if not rows:
        await event.edit("📭 <b>Pending buyurtmalar yo'q</b>")
        return
    
    text = "📋 <b>Pending buyurtmalar:</b>\n\n"
    for row in rows:
        order_id, username, stars, price, created = row
        text += f"#{order_id} | @{username} | {stars}⭐ | {price:,.0f} UZS\n"
    
    await event.edit(text)

# ----------------------- Asosiy -----------------------
async def main():
    init_db()
    log.info("Payment Monitor ishga tushmoqda...")
    
    await client.start(phone=(lambda: PHONE or input("Telefon raqam (+998...): ")))
    
    me = await client.get_me()
    log.info(f"Login: {me.first_name} (id={me.id})")
    
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("To'xtatildi.")
