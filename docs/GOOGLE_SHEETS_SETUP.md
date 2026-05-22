# 📊 Google Sheets Integratsiya Qo'llanmasi

## Nima qiladi?

- ✅ Yangi buyurtmalarni avto yozish
- ✅ To'lov holatini real-time yangilash
- 📊 Statistika va hisobotlar
- 🎨 Chiroyli formatlangan jadval

## O'rnatish (3 qadam)

### 1. Google Cloud Console sozlash

1. [Google Cloud Console](https://console.cloud.google.com/) ga kiring
2. Yangi project yaratish: **"New Project"**
3. Project nomi: `telegram-bot-sheets`

### 2. Google Sheets API yoqish

1. **APIs & Services** → **Library**
2. Qidirish: `Google Sheets API`
3. **Enable** tugmasini bosing
4. Qidirish: `Google Drive API`
5. **Enable** tugmasini bosing

### 3. Service Account yaratish

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **Service Account**
3. Service account name: `telegram-bot`
4. **Create and Continue** → **Done**
5. Service account'ni oching
6. **Keys** tab → **Add Key** → **Create New Key**
7. **JSON** format → **Create**
8. Fayl yuklanadi: `something.json`

### 4. Faylni joylashtirish

Yuklangan faylni:
```
bots/savemod/credentials.json
```
ga ko'chiring.

### 5. Google Sheet yaratish

1. [Google Sheets](https://sheets.new/) ga kiring
2. Yangi spreadsheet yaratish
3. URL dan **SHEET ID** ni oling:
   ```
   https://docs.google.com/spreadsheets/d/1ABC123xyz/edit#gid=0
                                   ^^^^^^^^^^^ SHEET ID
   ```

### 6. Access berish

1. `credentials.json` ni oching
2. `client_email` ni toping:
   ```json
   "client_email": "telegram-bot@project-id.iam.gserviceaccount.com"
   ```
3. Google Sheet oching
4. **Share** tugmasini bosing
5. Client email ni qo'shing
6. **Editor** huquqi bilan

### 7. .env sozlash

```env
GOOGLE_SHEETS_ID=1ABC123xyz  # Sizning sheet ID
```

## Ishga tushirish

```bash
cd "bots/savemod"
python payment_monitor.py
```

## Jadval strukturasi

### "Buyurtmalar" sheet

| ID | Sana | Mijoz | Username | Turi | Miqdor | Narx (UZS) | To'lov holati | Stars yuborildi | Izoh |
|----|------|-------|----------|------|--------|------------|---------------|-----------------|------|
| 1 | 22.05.2024 14:30 | @ali | @ali | Stars | 1000 | 120000 | To'langan | Ha | Telegram: @ali |

### "Statistika" sheet

Avto hisoblangan:
- Jami buyurtmalar
- To'langan/kutilayotgan
- Jami tushum (UZS)
- Jami stars sotildi

## Ranglar

| Rang | Ma'nosi |
|------|---------|
| 🟢 Yashil | To'langan |
| 🟡 Sariq | Kutilmoqda |
| 🔴 Qizil | Bekor qilindi |
| ⚪ Kulrang | Juft qatorlar |

## Muammolar?

### "credentials.json topilmadi"
Fayl to'g'ri joyga ko'chirilganini tekshiring: `bots/savemod/credentials.json`

### "403 Forbidden"
Service account email'ga Sheet'da **Editor** huquqi berilganini tekshiring.

### "Spreadsheet not found"
`GOOGLE_SHEETS_ID` to'g'ri ekanini tekshiring.
