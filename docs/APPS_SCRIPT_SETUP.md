# 📊 Apps Script Integratsiya Qo'llanmasi

**Bepul va oson!** Google Sheets bilan Apps Script orqali ishlash.

## Nima qiladi?

- ✅ Yangi buyurtmalarni avto yozish
- ✅ To'lov holatini real-time yangilash  
- 📊 Avto statistika hisoblash
- 🎨 Chiroyli ranglar bilan formatlash

## Afzalliklari (Python gspread dan)

| Apps Script | Python gspread |
|-------------|----------------|
| ✅ **Bepul** | ❌ API limits |
| ✅ **No credentials** | ❌ credentials.json kerak |
| ✅ **Browser'da ishlaydi** | ⚠️ Server kerak |
| ✅ **Avto formatlash** | ❌ Qo'lda formatlash |

## O'rnatish (5 daqiqa)

### 1. Google Sheet yaratish

1. [sheets.new](https://sheets.new/) oching
2. Nom berish: `Telegram Bot Orders`
3. **Share** → `Anyone with the link` → `Editor`

### 2. Apps Script ochish

1. Sheet'da **Extensions** → **Apps Script**
2. Default kodni o'chirish:
```javascript
function myFunction() {
  // Bu kodni o'chiring
}
```

### 3. Kodni joylashtirish

```javascript
/**
 * Telegram Bot - Google Sheets Integratsiya
 */

const SPREADSHEET = SpreadsheetApp.getActiveSpreadsheet();
const SECRET_TOKEN = 'sizning_xavfsiz_tokeningiz';

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    if (data.token !== SECRET_TOKEN) {
      return jsonResponse({success: false, error: 'Invalid token'});
    }
    
    var action = data.action;
    var result;
    
    switch(action) {
      case 'addOrder':
        result = addOrder(data.order);
        break;
      case 'updatePayment':
        result = updatePayment(data.order_id, data.status, data.stars_sent);
        break;
      default:
        result = {success: false, error: 'Unknown action'};
    }
    
    return jsonResponse(result);
    
  } catch (error) {
    return jsonResponse({success: false, error: error.toString()});
  }
}

function addOrder(order) {
  var sheet = SPREADSHEET.getSheetByName('Buyurtmalar') || SPREADSHEET.insertSheet('Buyurtmalar');
  
  // Header (birinch marta)
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['ID', 'Sana', 'Mijoz', 'Miqdor', 'Narx', 'Holat']);
    sheet.getRange(1, 1, 1, 6).setBackground('#2196F3').setFontColor('#FFFFFF').setFontWeight('bold');
  }
  
  var now = Utilities.formatDate(new Date(), 'Asia/Tashkent', 'dd.MM.yyyy HH:mm');
  
  sheet.appendRow([
    order.order_id,
    now,
    '@' + order.username,
    order.amount,
    order.price_uzs,
    order.status
  ]);
  
  return {success: true, message: 'Order #' + order.order_id + ' added'};
}

function updatePayment(order_id, status, stars_sent) {
  var sheet = SPREADSHEET.getSheetByName('Buyurtmalar');
  var data = sheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] == order_id) {
      sheet.getRange(i + 1, 6).setValue(status);
      
      // Rang
      var color = (status === "To'langan") ? '#C8E6C9' : '#FFE082';
      sheet.getRange(i + 1, 6).setBackground(color);
      
      return {success: true, message: 'Order #' + order_id + ' updated'};
    }
  }
  
  return {success: false, error: 'Order not found'};
}

function jsonResponse(data) {
  return ContentService.createTextOutput(JSON.stringify(data)).setMimeType(ContentService.MimeType.JSON);
}
```

### 4. Deploy qilish

1. **Deploy** → **New deployment**
2. **Type**: Web app
3. **Description**: `Telegram Bot API`
4. **Execute as**: Me
5. **Who has access**: Anyone
6. **Deploy** tugmasini bosing

### 5. URL olish

Deploy'dan keyin URL beriladi:
```
https://script.google.com/macros/s/AKfycbz.../exec
                                    ^^^^^^^^^^^
                                    SCRIPT ID
```

### 6. .env sozlash

```env
APPS_SCRIPT_URL=https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
APPS_SCRIPT_TOKEN=sizning_xavfsiz_tokeningiz
```

### 7. Test qilish

```bash
cd bots/savemod
python -c "
import asyncio
from apps_script_client import test_sheets_connection
result = asyncio.run(test_sheets_connection())
print('✅ OK' if result else '❌ Xato')
"
```

## To'liq kod

Biz allaqachon tayyor kod yozdik:

📄 `bots/savemod/apps_script.gs` - To'liq Apps Script kodi

Bu kodni copy-paste qilib ishlatishingiz mumkin!

## Muammolar?

### "Invalid token"
`.env` dagi `APPS_SCRIPT_TOKEN` va Apps Script'dagi `SECRET_TOKEN` bir xil emas.

### "Order not found"
Yangilashdan oldin buyurtma qo'shilganiga ishonch hosil qiling.

### URL topilmadi
Deploy qilganingizda URL ni nusxalab oling.

## Qo'llab-quvvatlash

Apps Script bepul, lekin bir kunda 20,000 ta so'rov limiti bor (biz uchun yetarli!)
