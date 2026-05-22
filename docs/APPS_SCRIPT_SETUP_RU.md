# 📊 Apps Script Инструкция (Русский язык)

## Настройка Google Sheets (Русский интерфейс)

### 1. Создать таблицу

1. Откройте [sheets.new](https://sheets.new/)
2. Название: `Telegram Bot Orders`
3. **Открыть доступ** (справа вверху кнопка) → `Все, у кого есть ссылка` → `Редактор`

### 2. Открыть Apps Script

В вашем скриншоте уже открыт Apps Script! ✅

**Путь:** `Расширения` → `Apps Script`

Или на русском интерфейсе:
- **Расширения** (меню сверху)
- **Сценарии Apps**

### 3. Вставить код

В редакторе Apps Script (где сейчас `myFunction`):

**Удалить старый код:**
```javascript
function myFunction() {
  // УДАЛИТЬ ВСЁ ЭТО
}
```

**Вставить новый код** из файла `bots/savemod/apps_script.gs`:

```javascript
/**
 * Telegram Bot - Google Sheets
 */

const SPREADSHEET = SpreadsheetApp.getActiveSpreadsheet();
const SECRET_TOKEN = 'vash_sekretnyy_token';  // Измените!

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    if (data.token !== SECRET_TOKEN) {
      return jsonResponse({success: false, error: 'Invalid token'});
    }
    
    var action = data.action;
    
    if (action === 'addOrder') {
      return jsonResponse(addOrder(data.order));
    }
    else if (action === 'updatePayment') {
      return jsonResponse(updatePayment(data.order_id, data.status));
    }
    else {
      return jsonResponse({success: false, error: 'Unknown action'});
    }
    
  } catch (error) {
    return jsonResponse({success: false, error: error.toString()});
  }
}

function addOrder(order) {
  var sheet = SPREADSHEET.getSheetByName('Заказы') || 
              SPREADSHEET.insertSheet('Заказы');
  
  // Заголовки (первый раз)
  if (sheet.getLastRow() === 0) {
    sheet.appendRow(['ID', 'Дата', 'Клиент', 'Количество', 'Цена', 'Статус']);
    sheet.getRange(1, 1, 1, 6)
      .setBackground('#2196F3')
      .setFontColor('#FFFFFF')
      .setFontWeight('bold');
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
  
  // Цвет статуса
  var lastRow = sheet.getLastRow();
  var statusCell = sheet.getRange(lastRow, 6);
  if (order.status === 'Оплачен') {
    statusCell.setBackground('#C8E6C9');  // Зелёный
  } else {
    statusCell.setBackground('#FFE082');  // Жёлтый
  }
  
  return {success: true, message: 'Order #' + order.order_id + ' added'};
}

function updatePayment(order_id, status) {
  var sheet = SPREADSHEET.getSheetByName('Заказы');
  var data = sheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] == order_id) {
      var statusCell = sheet.getRange(i + 1, 6);
      statusCell.setValue(status);
      
      // Цвет
      if (status === 'Оплачен') {
        statusCell.setBackground('#C8E6C9');  // Зелёный
      } else if (status === 'Отменен') {
        statusCell.setBackground('#FFCDD2');  // Красный
      }
      
      return {success: true, message: 'Order #' + order_id + ' updated'};
    }
  }
  
  return {success: false, error: 'Order not found'};
}

function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

// Тест
function doGet(e) {
  return jsonResponse({
    success: true, 
    message: 'API работает!',
    time: new Date().toISOString()
  });
}
```

### 4. Сохранить

Нажмите **Сохранить** (дискетка ⭐️ или Ctrl+S)

Название проекта: `Telegram Bot`

### 5. Развернуть (Deploy)

1. Нажмите **Развернуть** (справа вверху синяя кнопка)
2. **Новое развертывание** (или "Создать развертывание")
3. **Тип**: Веб-приложение
4. **Описание**: `Telegram Bot API`
5. **Выполнить как**: Я
6. **Кто имеет доступ**: Все
7. **Развернуть**

### 6. Получить URL

После развертывания появится URL:
```
https://script.google.com/macros/s/AKfycbzXXXXXX/exec
                                    ^^^^^^^^^^^^^^^^
                                    ВАШ SCRIPT ID
```

**Скопируйте этот URL!**

### 7. Настроить .env

Откройте файл `config/.env`:

```env
APPS_SCRIPT_URL=https://script.google.com/macros/s/ВАШ_SCRIPT_ID/exec
APPS_SCRIPT_TOKEN=vash_sekretnyy_token
```

### 8. Проверить

Откройте URL в браузере. Должно показать:
```json
{"success": true, "message": "API работает!"}
```

## Результат

В таблице Google Sheets автоматически появится лист `Заказы`:

| ID | Дата | Клиент | Количество | Цена | Статус |
|----|------|--------|------------|------|--------|
| 1 | 22.05.2024 14:30 | @ali | 1000 | 120000 | Оплачен 🟢 |
| 2 | 22.05.2024 15:45 | @bob | 500 | 60000 | Ожидает 🟡 |

## Важно!

- 🟢 **Зелёный** = Оплачен
- 🟡 **Жёлтый** = Ожидает
- 🔴 **Красный** = Отменен

## Проблемы?

**"Нет разрешения"** → Проверьте, что дали доступ "Все, у кого есть ссылка"

**URL не работает** → Проверьте, что нажали "Развернуть", а не просто сохранили

**Ошибка токена** → Токен в .env и в коде должен совпадать
