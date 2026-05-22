# Fragmently Telegram Bot

[Fragmently](https://www.fragmently.uz) API orqali Telegram **Stars** va **Premium**
obunalarini sotib olish uchun oddiy va qulay Telegram bot.

API hujjatlari: <https://www.fragmently.uz/docs>

## Imkoniyatlar

- ⭐ **Stars sotib olish** — istalgan `@username` ga (kamida 50 dona)
- 💎 **Premium sotib olish** — 3 / 6 / 12 oylik
- 💰 **Balans tekshirish** — TON hamyon manzili va balans
- 🧮 **Narx kalkulyatori** — Stars / Premium uchun TON narxi
- 🔒 **Whitelist** — `ALLOWED_USER_IDS` orqali botdan foydalanishni cheklash

Barcha xaridlar oldidan **tasdiqlash bosqichi** bor (xato xaridlar oldi olinadi).

## Talablar

- Python **3.10+**
- Telegram bot tokeni — [@BotFather](https://t.me/BotFather) dan
- Fragmently API tokeni — <https://www.fragmently.uz> dashboard'idan
- Fragmently hisobida **TON balans** to'ldirilgan bo'lishi shart

## O'rnatish

```powershell
# 1) Repozitoriyaga kirib, virtual muhit yarating
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2) Kutubxonalarni o'rnating
pip install -r requirements.txt

# 3) Tokenlarni sozlang
copy .env.example .env
# .env faylini ochib BOT_TOKEN va FRAGMENTLY_TOKEN qiymatlarini yozing
```

## Ishga tushirish

```powershell
python bot.py
```

Botga `/start` yuboring — bosh menyu ochiladi.

## Buyruqlar

| Buyruq    | Tavsif                       |
|-----------|------------------------------|
| `/start`  | Botni ishga tushirish, menyu |
| `/menu`   | Bosh menyuga qaytish         |
| `/cancel` | Joriy amalni bekor qilish    |

## Fayllar

- `bot.py` — Telegram bot (aiogram 3, FSM bilan ko'p bosqichli oqim)
- `fragmently.py` — Fragmently REST API uchun async klient (`httpx`)
- `.env.example` — atrof-muhit o'zgaruvchilari namunasi
- `requirements.txt` — Python kutubxonalari

## Xavfsizlik

- `.env` faylni hech qachon Git ga qo'shmang (`.gitignore` da bor).
- `FRAGMENTLY_TOKEN` ni hech kimga bermang — u sizning hamyoningiz bilan ishlaydi.
- Faqat ishonchli foydalanuvchilarga ruxsat bermoqchi bo'lsangiz, `.env` ichida
  `ALLOWED_USER_IDS=123456,789012` ko'rinishida ID larni yozing.

## Qo'llab-quvvatlash

- Fragmently support: <https://t.me/fragmently_support>
