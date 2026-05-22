# Telegram Stars & TON Bot

Assalomu alaykum! Bu bot orqali Telegram Stars, TON va Premium sotib olish mumkin.

## Nima qiladi?

- **Stars sotish** - Telegram Stars avtomatik yuborish
- **TON kurs** - Real vaqt narxlari
- **Payment** - HUMO Card to'lovlarni kuzatish
- **Monitoring** - Xabarlar va media saqlash

## O'rnatish

1. Python 3.8+ o'rnatish
2. `pip install -r requirements.txt`
3. `.env.example` ni `.env` ga ko'chirish va tokenlarni kiritish
4. `python bot.py` bilan ishga tushirish

## Google Sheets

Buyurtmalar avtomatik Google Sheets ga yoziladi:
- `.env` da `APPS_SCRIPT_URL` ni sozlash
- Apps Script kodini `bots/savemod/apps_script.gs` dan olish

## Tuzilma

```
bots/
├── bot.py           - Asosiy bot
├── fragmently.py    - Fragmently API
└── savemod/
    ├── main.py      - Monitoring
    ├── chatbot.py   - FAQ bot
    ├── payment_monitor.py  - Avto to'lov
    └── apps_script.gs     - Google Sheets
```

## Eslatma

Bu loyiha shaxsiy foydalanish uchun. Agar botdan foydalanmoqchi bo'lsangiz, o'zingiz server'ingizda ishga tushiring.

## Bog'lanish

Telegram: [@WaSaVi](https://t.me/WaSaVi)

---

*Loyiha 2024-2025 yil davomida ishlab chiqildi.*
