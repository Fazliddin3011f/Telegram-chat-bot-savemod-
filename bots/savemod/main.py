"""SaveMod-style userbot — Telethon asosida.

Funksiyalar:
  - Kelgan xabarlarni keshlash (PM, ixtiyoriy: guruhlar ham)
  - O'chirilgan xabar haqida bildirishnoma yuborish (eski matn + jo'natuvchi)
  - Tahrirlangan xabarni "eski → yangi" ko'rinishida ko'rsatish
  - Self-destruct (TTL) rasm/video/ovozni yo'qolishidan oldin saqlash

Birinchi ishga tushganda telefon raqami uchun SMS kod so'raydi.
"""
from __future__ import annotations

import asyncio
import html
import logging
import os
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import (
    MessageMediaPhoto,
    MessageMediaDocument,
    PeerUser,
    PeerChat,
    PeerChannel,
    Channel,
    User,
)

from db import Cache


# ----------------------- Konfiguratsiya -----------------------
load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "").strip()
PHONE = os.getenv("PHONE", "").strip()
TARGET_RAW = os.getenv("TARGET", "me").strip()
MONITOR_GROUPS = os.getenv("MONITOR_GROUPS", "false").lower() in ("1", "true", "yes")
MONITOR_CHANNELS = os.getenv("MONITOR_CHANNELS", "false").lower() in ("1", "true", "yes")
CACHE_HOURS = int(os.getenv("CACHE_HOURS", "48"))
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID", "").strip()
AUTO_REPLY = os.getenv("AUTO_REPLY", "false").lower() in ("1", "true", "yes")
AUTO_REPLY_GROUPS = os.getenv("AUTO_REPLY_GROUPS", "false").lower() in ("1", "true", "yes")
TON_MARKUP_PERCENT = float(os.getenv("TON_MARKUP_PERCENT", "20").strip() or 20)
TON_MANUAL_RATE_UZS = os.getenv("TON_MANUAL_RATE_UZS", "").strip()

if not API_ID or not API_HASH:
    raise SystemExit("API_ID / API_HASH .env faylida ko'rsatilmagan")
# PHONE bo'sh bo'lsa - Telethon terminalda interaktiv so'raydi

MEDIA_DIR = Path("media")
MEDIA_DIR.mkdir(exist_ok=True)
KARTA_FILE = Path(__file__).resolve().parent.parent / "karta.txt"
TON_RATE_CACHE_SECONDS = 300
ton_rate_cache: dict[str, float | str] = {}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
log = logging.getLogger("savemod")
# Telethon'ning batafsil log'ini kamaytirish
logging.getLogger("telethon").setLevel(logging.WARNING)


client = TelegramClient("savemod.session", API_ID, API_HASH)
cache = Cache("cache.db")

# TARGET ni keyinroq, login bo'lgandan keyin resolvе qilamiz
target_entity = None
TON_AMOUNT_RE = re.compile(r"(?P<amount>\d+(?:[.,]\d+)?)\s*(?:ton|тон)\b", re.IGNORECASE)


# ----------------------- Yordamchi -----------------------
def _fmt_user(name: str | None, username: str | None, user_id: int | None) -> str:
    """SaveMod Mirror stilida: '<ism> (https://t.me/username)' yoki '<ism>' + id."""
    safe_name = html.escape(name) if name else "Noma'lum"
    if username:
        return f'<a href="https://t.me/{username}">{safe_name}</a>'
    if user_id:
        return f'<a href="tg://user?id={user_id}">{safe_name}</a>'
    return safe_name


async def _get_sender_info(message) -> tuple[int | None, str | None, str | None]:
    sender = await message.get_sender()
    if sender is None:
        return None, None, None
    if isinstance(sender, User):
        name_parts = [sender.first_name or "", sender.last_name or ""]
        name = " ".join(p for p in name_parts if p).strip() or None
        return sender.id, name, sender.username
    name = getattr(sender, "title", None) or getattr(sender, "first_name", None)
    return getattr(sender, "id", None), name, getattr(sender, "username", None)


def _is_private_peer(message) -> bool:
    return isinstance(message.peer_id, PeerUser)


def _is_channel(message) -> bool:
    return isinstance(message.peer_id, PeerChannel)


def _media_kind(message) -> str | None:
    if not message.media:
        return None
    if isinstance(message.media, MessageMediaPhoto):
        return "photo"
    if isinstance(message.media, MessageMediaDocument):
        doc = message.media.document
        if doc and doc.mime_type:
            if doc.mime_type.startswith("video"):
                return "video"
            if doc.mime_type.startswith("audio") or "voice" in (doc.mime_type or ""):
                return "voice"
        return "document"
    return "media"


def _ttl_seconds(message) -> int | None:
    """Self-destruct media: ttl_seconds qiymatini qaytaradi (yoki None)."""
    media = message.media
    if not media:
        return None
    ttl = getattr(media, "ttl_seconds", None)
    if ttl:
        return ttl
    # Yangi formatda ttl_period
    return getattr(message, "ttl_period", None)


def _fmt_uzs(value: float) -> str:
    return f"{round(value):,}".replace(",", " ") + " so'm"


def _extract_ton_amount(text: str) -> float | None:
    match = TON_AMOUNT_RE.search(text or "")
    if not match:
        return None
    try:
        amount = float(match.group("amount").replace(",", "."))
    except ValueError:
        return None
    return amount if amount > 0 else None


def _get_ton_rate_uzs_sync() -> tuple[float | None, str]:
    if TON_MANUAL_RATE_UZS:
        try:
            return float(TON_MANUAL_RATE_UZS.replace(",", ".")), "ruchnoy"
        except ValueError:
            pass
    import json
    now = time.time()
    cached_rate = ton_rate_cache.get("rate")
    cached_source = ton_rate_cache.get("source")
    cached_at = float(ton_rate_cache.get("time") or 0)
    if cached_rate and cached_source and now - cached_at < TON_RATE_CACHE_SECONDS:
        return float(cached_rate), str(cached_source)
    usd_uzs_raw = os.getenv("USD_UZS_RATE", "12700").strip() or "12700"
    try:
        usd_uzs = float(usd_uzs_raw)
    except ValueError:
        usd_uzs = 12700.0
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        query = urllib.parse.urlencode(
            {"ids": "the-open-network", "vs_currencies": "uzs,usd"}
        )
        url = f"https://api.coingecko.com/api/v3/simple/price?{query}"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
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
        url = "https://api.binance.com/api/v3/ticker/price?symbol=TONUSDT"
        req = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            usd = float(json.loads(resp.read().decode("utf-8")).get("price") or 0)
        if usd > 0:
            return usd * usd_uzs, "real"
    except Exception as e:
        log.warning("Binance TON kursi xatolik: %s", e)
    return None, "xato"


async def _get_ton_rate_uzs() -> tuple[float | None, str]:
    return await asyncio.to_thread(_get_ton_rate_uzs_sync)


def _ton_sales_reply(amount: float, rate: float, source: str) -> str:
    user_rate = rate * (1 + TON_MARKUP_PERCENT / 100)
    total = amount * user_rate
    return (
        "Assalomu alaykum ✅\n\n"
        f"💎 <b>{amount:g} ton</b> bor\n"
        f"💰 Sizga kurs: <b>{_fmt_uzs(user_rate)}</b>\n\n"
        f"🧾 Jami: <b>{_fmt_uzs(total)}</b>\n\n"
        "Olish uchun wallet manzilingizni va to'lov chekini yuboring."
    )


FORM_TON = """📋 <b>TON forma</b>

👤 Ism:
📱 Telefon:
💎 Miqdor:
💰 Kurs:
💳 To'lov turi:
🔗 Wallet:

Izoh:"""


FORM_USDT = """📋 <b>USDT forma</b>

👤 Ism:
📱 Telefon:
💵 Miqdor:
💰 Kurs:
🌐 Tarmoq: TRC20 / BEP20
🔗 Wallet:

Izoh:"""


# ----------------------- Event'lar -----------------------
@client.on(events.NewMessage(outgoing=True, pattern=r"^\.formton$"))
async def cmd_form_ton(event):
    await event.respond(FORM_TON, parse_mode="html")
    try:
        await event.delete()
    except Exception:
        pass


@client.on(events.NewMessage(outgoing=True, pattern=r"^\.formusdt$"))
async def cmd_form_usdt(event):
    await event.respond(FORM_USDT, parse_mode="html")
    try:
        await event.delete()
    except Exception:
        pass


@client.on(events.NewMessage(outgoing=True, pattern=r"^\.ton(?:\s+(\d+(?:[.,]\d+)?))?$"))
async def cmd_ton_rate(event):
    match = event.pattern_match
    amount_str = match.group(1) if match else None
    amount = 1.0
    if amount_str:
        try:
            amount = float(amount_str.replace(",", "."))
        except ValueError:
            amount = 1.0
    rate, source = await _get_ton_rate_uzs()
    if rate is None:
        await event.edit("⚠️ Hozir TON kursini olishda xatolik bo'ldi.")
        return
    await event.edit(_ton_sales_reply(amount, rate, source), parse_mode="html")


@client.on(events.NewMessage(outgoing=True, pattern=r"^\.id$"))
async def cmd_get_id(event):
    chat_id = event.chat_id
    chat = await event.get_chat()
    title = getattr(chat, "title", "Shaxsiy chat")
    text = (
        f"📌 <b>Chat ma'lumotlari:</b>\n\n"
        f"📝 Nomi: <b>{title}</b>\n"
        f"🆔 ID: <code>{chat_id}</code>\n\n"
        f"💡 Ushbu ID ni <code>.env</code> dagi <code>OWNER_CHAT_ID</code> "
        f"qatoriga qo'yishingiz mumkin."
    )
    await event.respond(text, parse_mode="html")
    try:
        await event.delete()
    except Exception:
        pass


@client.on(events.NewMessage(incoming=True))
async def on_new_message(event):
    """Kelgan xabarni keshlash. Self-destruct media bo'lsa - darhol yuklab olish."""
    msg = event.message
    is_pm = _is_private_peer(msg)
    is_channel = _is_channel(msg)

    if not is_pm and not MONITOR_GROUPS and not (is_channel and MONITOR_CHANNELS):
        return

    sender_id, sender_name, sender_username = await _get_sender_info(msg)
    media_type = _media_kind(msg)
    media_path: str | None = None
    ttl = _ttl_seconds(msg)

    # Self-destruct media: darhol yuklab olamiz
    if ttl and msg.media:
        try:
            fname = MEDIA_DIR / f"ttl_{int(time.time())}_{msg.id}"
            media_path = await msg.download_media(file=str(fname))
            log.info("TTL media saqlandi: %s (ttl=%ss)", media_path, ttl)
            await _send_ttl_alert(msg, sender_id, sender_name, sender_username, media_path, ttl)
        except Exception as e:
            log.warning("TTL media yuklab olishda xatolik: %s", e)

    cache.save(
        chat_id=event.chat_id,
        msg_id=msg.id,
        sender_id=sender_id,
        sender_name=sender_name,
        sender_username=sender_username,
        text=msg.message or "",
        has_media=bool(msg.media),
        media_path=media_path,
        media_type=media_type,
        is_private=is_pm,
        is_channel=is_channel,
    )
    log.info(
        "📥 Keshlandi: chat=%s msg=%s pm=%s channel=%s from=%s text=%r",
        event.chat_id, msg.id, is_pm, is_channel, sender_name, (msg.message or "")[:40],
    )

    # AI auto-reply vaqtincha o'chirilgan
    return


@client.on(events.MessageEdited(incoming=True))
async def on_message_edited(event):
    """Tahrirlangan xabar: eski va yangi matn."""
    msg = event.message
    is_pm = _is_private_peer(msg)
    is_channel = _is_channel(msg)
    if not is_pm and not MONITOR_GROUPS and not (is_channel and MONITOR_CHANNELS):
        return

    old = cache.get(event.chat_id, msg.id)
    new_text = msg.message or ""
    old_text = (old.get("text") if old else None) or "<i>matn yo'q</i>"

    if old and old.get("text") == new_text:
        # haqiqiy o'zgarish yo'q (masalan, faqat media yangilandi)
        return

    if old:
        sender_id = old.get("sender_id")
        sender_name = old.get("sender_name")
        sender_username = old.get("sender_username")
    else:
        sender_id, sender_name, sender_username = await _get_sender_info(msg)

    user_str = _fmt_user(sender_name, sender_username, sender_id)
    text = (
        f"✏️ {user_str} сообщение изменил.\n"
        f"<blockquote>{html.escape(str(old_text))}</blockquote>\n"
        f"⇩⇩⇩\n"
        f"<blockquote>{html.escape(new_text)}</blockquote>"
    )
    await _send_to_target(text)

    # Keshdagi matnni yangilaymiz
    cache.update_text(event.chat_id, msg.id, new_text)


@client.on(events.MessageDeleted())
async def on_message_deleted(event):
    """O'chirilgan xabar(lar): keshdan eski matn va sender'ni topib yuborish."""
    chat_id = event.chat_id  # PM uchun None bo'lishi mumkin
    log.info("🗑 Delete event: chat=%s ids=%s", chat_id, event.deleted_ids)
    for msg_id in event.deleted_ids:
        rec = None
        if chat_id is not None:
            rec = cache.get(chat_id, msg_id)
        if rec is None:
            # chat_id bilan topilmadi - msg_id bo'yicha qidiramiz
            candidates = cache.find_by_msg_id(msg_id)
            # Eng so'nggi qaydni olamiz
            rec = candidates[0] if candidates else None
        if rec is None:
            continue

        is_pm = bool(rec.get("is_private"))
        is_channel = bool(rec.get("is_channel"))
        if not is_pm and not MONITOR_GROUPS and not (is_channel and MONITOR_CHANNELS):
            continue

        user_str = _fmt_user(
            rec.get("sender_name"), rec.get("sender_username"), rec.get("sender_id")
        )
        body = rec.get("text") or ""
        media_note = ""
        if rec.get("has_media"):
            mtype = rec.get("media_type") or "media"
            media_ru = {
                "photo": "Фото",
                "video": "Видео",
                "voice": "Голосовое сообщение",
                "document": "Файл",
                "media": "Медиа",
            }.get(mtype, "Медиа")
            header = f"🗑 Это {media_ru.lower()} было удалено"
        else:
            header = "🗑 Это сообщение было удалено"

        text = f"{header}\n\n{user_str}"
        if body:
            text += f"\n<blockquote>{html.escape(str(body))}</blockquote>"
        await _send_to_target(text)

        # Agar saqlangan media bo'lsa - uni ham yuborib qo'yamiz
        media_path = rec.get("media_path")
        if media_path and Path(media_path).exists():
            await _send_file_to_target(media_path, "↑ saqlangan media")

        cache.delete(rec["chat_id"], msg_id)


# ----------------------- Yordamchi yuboruvchi -----------------------
def _send_via_bot_sync(html_text: str) -> bool:
    """Bot API orqali xabar yuborish (HTTP). Agar BOT_TOKEN bo'lmasa - False."""
    if not BOT_TOKEN or not OWNER_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = urllib.parse.urlencode(
            {
                "chat_id": OWNER_CHAT_ID,
                "text": html_text,
                "parse_mode": "HTML",
                "disable_web_page_preview": "true",
            }
        ).encode()
        req = urllib.request.Request(url, data=data, method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            resp.read()
        return True
    except Exception as e:
        log.warning("Bot API orqali yuborishda xatolik: %s", e)
        return False


def _send_file_via_bot_sync(file_path: str, caption: str = "") -> bool:
    if not BOT_TOKEN or not OWNER_CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        boundary = "----SaveModBoundary"
        file_name = Path(file_path).name
        file_bytes = Path(file_path).read_bytes()
        fields = {
            "chat_id": OWNER_CHAT_ID,
            "caption": caption,
            "parse_mode": "HTML",
        }

        body = bytearray()
        for key, value in fields.items():
            body.extend(f"--{boundary}\r\n".encode())
            body.extend(
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode()
            )
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="document"; filename="{file_name}"\r\n'.encode()
        )
        body.extend(b"Content-Type: application/octet-stream\r\n\r\n")
        body.extend(file_bytes)
        body.extend(f"\r\n--{boundary}--\r\n".encode())

        req = urllib.request.Request(url, data=bytes(body), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=60) as resp:
            resp.read()
        return True
    except Exception as e:
        log.warning("Bot API orqali media yuborishda xatolik: %s", e)
        return False


async def _send_to_target(html_text: str) -> None:
    # 1-variant: bot orqali
    if BOT_TOKEN and OWNER_CHAT_ID:
        ok = await asyncio.to_thread(_send_via_bot_sync, html_text)
        if ok:
            return
    # 2-variant: userbot o'zi yuboradi
    try:
        await client.send_message(target_entity, html_text, parse_mode="html", link_preview=False)
    except Exception as e:
        log.warning("Bildirishnoma yuborishda xatolik: %s", e)


async def _send_file_to_target(file_path: str, caption: str = "") -> None:
    if BOT_TOKEN and OWNER_CHAT_ID:
        ok = await asyncio.to_thread(_send_file_via_bot_sync, file_path, caption)
        if ok:
            return
    try:
        await client.send_file(target_entity, file_path, caption=caption, parse_mode="html")
    except Exception as e:
        log.warning("Media yuborishda xatolik: %s", e)


async def _send_ttl_alert(msg, sender_id, sender_name, sender_username, media_path, ttl):
    user_str = _fmt_user(sender_name, sender_username, sender_id)
    caption = (
        f"🔥 Самоуничтожающееся медиа сохранено\n\n"
        f"{user_str}"
    )
    if msg.message:
        caption += f"\n{html.escape(msg.message)}"
    await _send_file_to_target(media_path, caption)


# ----------------------- Fon vazifalari -----------------------
async def cleanup_loop():
    """Har soatda eski keshni tozalash."""
    while True:
        try:
            removed = cache.prune(CACHE_HOURS)
            if removed:
                log.info("Keshdan %d ta eski xabar o'chirildi", removed)
        except Exception as e:
            log.warning("Cleanup xatolik: %s", e)
        await asyncio.sleep(3600)


# ----------------------- Asosiy -----------------------
async def main():
    global target_entity

    log.info("Userbot ishga tushmoqda...")
    # PHONE bo'lmasa, Telethon terminalda so'raydi
    await client.start(phone=(lambda: PHONE or input("Telefon raqam (+998...): ")))

    me = await client.get_me()
    log.info("Login: %s (id=%s)", me.first_name, me.id)

    try:
        target_entity = await client.get_entity(TARGET_RAW)
    except Exception:
        try:
            target_entity = await client.get_entity(int(TARGET_RAW))
        except Exception as e:
            # Dialoglar nomi bo'yicha qidirib ko'ramiz (agar plain string bo'lsa)
            found = False
            if not TARGET_RAW.startswith("-") and not TARGET_RAW.isdigit():
                try:
                    async for dialog in client.iter_dialogs():
                        if dialog.name and dialog.name.strip().lower() == TARGET_RAW.strip().lower():
                            target_entity = dialog.entity
                            found = True
                            log.info("TARGET dialog nomi bo'yicha topildi: %s (id=%s)", dialog.name, dialog.id)
                            break
                except Exception as ex:
                    log.warning("Dialoglarni qidirishda xato: %s", ex)
            if not found:
                log.warning("TARGET resolve qilinmadi (%s) - 'me' ga o'tkazildi", e)
                target_entity = "me"

    target_label = (
        target_entity.username
        if hasattr(target_entity, "username") and target_entity.username
        else str(target_entity)
    )
    channel = "Bot API" if (BOT_TOKEN and OWNER_CHAT_ID) else f"Userbot → {target_label}"
    log.info(
        "Kanal=%s, Groups=%s, Channels=%s, Cache=%dh",
        channel,
        MONITOR_GROUPS,
        MONITOR_CHANNELS,
        CACHE_HOURS,
    )

    asyncio.create_task(cleanup_loop())
    await client.run_until_disconnected()


if __name__ == "__main__":
    try:
        client.loop.run_until_complete(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("To'xtatildi.")
