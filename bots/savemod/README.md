# SaveMod Userbot

Shaxsiy Telegram **userbot** — o'chirilgan / tahrirlangan xabarlarni
"Saved Messages"ga (yoki tanlangan chatga) yuboradi va self-destruct
media'larni saqlab qoladi.

> ⚠️ Bu **bot emas**, balki userbot — sizning shaxsiy akkauntingiz
> nomidan ishlaydi. Boshqaruv `my.telegram.org` orqali olinadigan
> API_ID/API_HASH va sizning telefoningiz orqali.

## Imkoniyatlar

- 🗑 **O'chirilgan xabar** — eski matn + jo'natuvchi haqida ma'lumot
- ✏️ **Tahrirlangan xabar** — "eski → yangi" solishtirish
- 🔥 **Self-destruct media** — yo'qolishidan oldin yuklab olib saqlash
- 👥 Ixtiyoriy: guruh xabarlarini ham kuzatish (`MONITOR_GROUPS=true`)
- 🧹 Avtomatik kesh tozalash (default: 48 soat)
- 🚫 Reklama yo'q

## Talablar

- Python **3.10+**
- API_ID + API_HASH — <https://my.telegram.org> dan olinadi (bepul)
- Sizning telefon raqamingiz (Telegram akkaunt)

## 1-bosqich: API_ID va API_HASH olish

1. <https://my.telegram.org> ga kiring (telefon raqamingiz bilan)
2. **API development tools** bo'limini oching
3. **Create new application** bosing
4. Forma to'ldiring:
   - **App title:** SaveMod
   - **Short name:** savemod
   - **Platform:** Desktop
   - **URL:** bo'sh qoldiring
5. Chiqqan **api_id** (raqam) va **api_hash** (uzun matn) ni nusxalang

## 2-bosqich: O'rnatish

```powershell
# savemod papkasiga kiring
cd savemod

# Kutubxonalarni o'rnating
pip install -r requirements.txt

# .env yarating
copy .env.example .env
# .env ni ochib API_ID, API_HASH, PHONE qiymatlarini yozing
```

## 3-bosqich: Birinchi ishga tushirish

```powershell
python main.py
```

Birinchi marta:
1. Terminalda **SMS kod** so'raladi — Telegram'dan kelgan kodni kiriting
2. 2FA parolingiz bo'lsa — uni ham kiriting
3. `savemod.session` fayli yaratiladi — keyingi ishga tushirishlarda kod kerak bo'lmaydi

Login muvaffaqiyatli bo'lsa, "Saved Messages" ga
✅ *SaveMod userbot ishga tushdi* xabari keladi.

## Sozlamalar (`.env`)

| O'zgaruvchi | Tavsif | Default |
|-------------|--------|---------|
| `API_ID` | my.telegram.org dan | majburiy |
| `API_HASH` | my.telegram.org dan | majburiy |
| `PHONE` | +998... formatda | majburiy |
| `TARGET` | bildirishnomalar qaerga (`me`, `@username` yoki `-100...`) | `me` |
| `MONITOR_GROUPS` | guruhlarni kuzatish (`true`/`false`) | `false` |
| `CACHE_HOURS` | kesh saqlash muddati | `48` |

## Foydali maslahatlar

- **Faqat shaxsiy kanal**ga jo'natmoqchi bo'lsangiz: yangi xususiy kanal yarating,
  `TARGET` ga uning ID sini (`-100xxxxxxxxxx`) yozing. Kanalga avval o'zingiz a'zo bo'ling.
- Bot **doimo ishlab turishi** kerak — kompyuter o'chsa, hech narsani saqlamaydi.
  Doimiy ishlash uchun VPS ga joylashtiring.
- `cache.db` va `media/` papkalari **shaxsiy** — backupga ham olmang, hech kimga bermang.

## Xavfsizlik

- `savemod.session` fayli = sizning akkauntingizga to'liq kirish. **Hech kimga bermang.**
- `cryptg` kutubxonasi shifrlash uchun kerak — pip o'rnatadi.
- Telegram TOS bo'yicha userbotlar rasman ruxsat etilmagan, ammo shaxsiy foydalanish
  uchun keng tarqalgan. Spam yoki suiiste'mol qilmang.

## Fayllar

- `main.py` — userbot (Telethon)
- `db.py` — SQLite kesh
- `requirements.txt` — kutubxonalar
- `.env.example` — sozlamalar namunasi
- `savemod.session` — Telegram login (avtomatik yaratiladi, **maxfiy**)
- `cache.db` — xabarlar keshi (avtomatik)
- `media/` — saqlangan TTL media'lar
