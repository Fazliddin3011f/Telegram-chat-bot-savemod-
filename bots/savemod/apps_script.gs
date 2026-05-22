/**
 * Telegram Bot - Google Sheets Integratsiya
 * Bu kod Google Apps Script ichida ishlaydi
 * 
 * URL: https://script.google.com/macros/s/YOUR_SCRIPT_ID/exec
 */

// ============================================
// CONSTANTS
// ============================================
const SPREADSHEET = SpreadsheetApp.getActiveSpreadsheet();
const SHEET_ORDERS = 'Buyurtmalar';
const SHEET_STATS = 'Statistika';
const SECRET_TOKEN = 'your_secret_token_here'; // Xavfsizlik uchun

// ============================================
// MAIN WEBHOOK HANDLER
// ============================================

/**
 * POST so'rovlarini qabul qilish
 */
function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    
    // Xavfsizlik tekshiruvi
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
      case 'updateOrderByIdOrUsername':
        result = updateOrderByIdOrUsername(data.order_id, data.username, data.updates);
        break;
      case 'findByUsername':
        result = findOrderByUsername(data.username);
        break;
      case 'getStats':
        result = getStats();
        break;
      case 'getDailyReport':
        result = getDailyReport();
        break;
      default:
        result = {success: false, error: 'Unknown action: ' + action};
    }
    
    return jsonResponse(result);
    
  } catch (error) {
    return jsonResponse({success: false, error: error.toString()});
  }
}

/**
 * GET so'rovlarini qabul qilish (tekshirish uchun)
 */
function doGet(e) {
  return jsonResponse({
    success: true, 
    message: 'Telegram Bot Google Sheets API ishladi!',
    time: new Date().toISOString()
  });
}

// ============================================
// ORDER FUNCTIONS
// ============================================

/**
 * Yangi buyurtma qo'shish
 */
function addOrder(order) {
  var sheet = getOrCreateSheet(SHEET_ORDERS);
  
  // Sheet ni formatlash (birinchi marta)
  if (sheet.getLastRow() === 0) {
    formatOrdersSheet(sheet);
  }
  
  var now = new Date();
  var formattedDate = Utilities.formatDate(now, 'Asia/Tashkent', 'dd.MM.yyyy HH:mm');
  
  var row = [
    order.order_id,
    formattedDate,
    order.username,
    '@' + order.username,
    order.order_type || 'Stars',
    order.amount,
    order.price_uzs,
    order.status || 'Kutilmoqda',
    order.stars_sent ? 'Ha' : "Yo'q",
    order.note || ''
  ];
  
  sheet.appendRow(row);
  
  // Yangi qatorni formatlash
  var lastRow = sheet.getLastRow();
  formatNewRow(sheet, lastRow);
  
  // Statistikani yangilash
  updateStats();
  
  return {
    success: true, 
    message: 'Order #' + order.order_id + ' added',
    row: lastRow
  };
}

/**
 * To'lov holatini yangilash
 */
function updatePayment(order_id, status, stars_sent) {
  var sheet = getOrCreateSheet(SHEET_ORDERS);
  var data = sheet.getDataRange().getValues();
  
  for (var i = 1; i < data.length; i++) {
    if (data[i][0] == order_id) {
      // Status yangilash (H ustun - index 7)
      sheet.getRange(i + 1, 8).setValue(status);
      
      // Stars yuborilganini yangilash (I ustun - index 8)
      sheet.getRange(i + 1, 9).setValue(stars_sent ? 'Ha' : "Yo'q");
      
      // Sana yangilash
      var now = new Date();
      var formattedDate = Utilities.formatDate(now, 'Asia/Tashkent', 'dd.MM.yyyy HH:mm');
      sheet.getRange(i + 1, 2).setValue(formattedDate + ' (yangilandi)');
      
      // Rang formatlash
      formatStatusRow(sheet, i + 1, status);
      
      // Statistikani yangilash
      updateStats();
      
      return {
        success: true, 
        message: 'Order #' + order_id + ' updated to ' + status
      };
    }
  }
  
  return {success: false, error: 'Order #' + order_id + ' not found'};
}

/**
 * Username bo'yicha buyurtma topish
 * Username o'zgarsa ham ID bilan topadi
 */
function findOrderByUsername(username) {
  var sheet = getOrCreateSheet(SHEET_ORDERS);
  var data = sheet.getDataRange().getValues();
  
  // Username ni tozalash (@ ni olib tashlash)
  var cleanUsername = username.replace('@', '').toLowerCase();
  
  for (var i = data.length - 1; i > 0; i--) {  // Oxiridan boshlab qidirish (eng yangi)
    var rowUsername = (data[i][3] || '').toString().replace('@', '').toLowerCase(); // Username ustuni (index 3)
    var rowId = data[i][0];
    
    if (rowUsername === cleanUsername) {
      return {
        found: true,
        row: i + 1,
        order: {
          id: rowId,
          date: data[i][1],
          client: data[i][2],
          username: data[i][3],
          type: data[i][4],
          amount: data[i][5],
          price: data[i][6],
          status: data[i][7],
          stars_sent: data[i][8],
          note: data[i][9]
        }
      };
    }
  }
  
  return {found: false, error: 'Username @' + username + ' not found'};
}

/**
 * ID va Username bo'yicha yangilash
 * Username o'zgarsa ham ID bilan topib yangilaydi
 */
function updateOrderByIdOrUsername(order_id, username, updates) {
  var sheet = getOrCreateSheet(SHEET_ORDERS);
  var data = sheet.getDataRange().getValues();
  var foundRow = -1;
  
  // Avval ID bo'yicha qidirish
  if (order_id) {
    for (var i = 1; i < data.length; i++) {
      if (data[i][0] == order_id) {
        foundRow = i + 1;
        break;
      }
    }
  }
  
  // ID topilmasa, username bo'yicha qidirish
  if (foundRow === -1 && username) {
    var result = findOrderByUsername(username);
    if (result.found) {
      foundRow = result.row;
    }
  }
  
  if (foundRow === -1) {
    return {success: false, error: 'Order not found by ID or username'};
  }
  
  // Yangilash
  if (updates.status) {
    sheet.getRange(foundRow, 8).setValue(updates.status);
    formatStatusRow(sheet, foundRow, updates.status);
  }
  
  if (updates.stars_sent !== undefined) {
    sheet.getRange(foundRow, 9).setValue(updates.stars_sent ? 'Ha' : "Yo'q");
  }
  
  if (updates.username) {
    sheet.getRange(foundRow, 4).setValue('@' + updates.username.replace('@', ''));
  }
  
  // Sana yangilash
  var now = new Date();
  var formattedDate = Utilities.formatDate(now, 'Asia/Tashkent', 'dd.MM.yyyy HH:mm');
  sheet.getRange(foundRow, 2).setValue(formattedDate + ' (yangilandi)');
  
  // Statistikani yangilash
  updateStats();
  
  return {
    success: true,
    message: 'Order updated successfully',
    row: foundRow
  };
}

// ============================================
// STATISTICS
// ============================================

/**
 * Statistikani hisoblash va yangilash
 */
function updateStats() {
  var sheet = getOrCreateSheet(SHEET_STATS);
  var ordersSheet = getOrCreateSheet(SHEET_ORDERS);
  
  var orders = ordersSheet.getDataRange().getValues();
  
  var totalOrders = orders.length - 1; // Header o'tkazib yuborish
  var paidOrders = 0;
  var pendingOrders = 0;
  var totalRevenue = 0;
  var totalStars = 0;
  
  for (var i = 1; i < orders.length; i++) {
    var status = orders[i][7]; // H ustun
    var price = parseFloat(orders[i][6]) || 0; // G ustun
    var stars = parseInt(orders[i][5]) || 0; // F ustun
    
    if (status === "To'langan") {
      paidOrders++;
      totalRevenue += price;
      totalStars += stars;
    } else if (status === 'Kutilmoqda') {
      pendingOrders++;
    }
  }
  
  // Statistika ma'lumotlari
  var statsData = [
    ['📊 UMUMIY STATISTIKA', ''],
    ['', ''],
    ['Ko\'rsatkich', 'Qiymat'],
    ['Jami buyurtmalar', totalOrders],
    ['To\'langan buyurtmalar', paidOrders],
    ['Kutilayotgan buyurtmalar', pendingOrders],
    ['', ''],
    ['💰 MOLIYAVIY', ''],
    ['Jami tushum (UZS)', totalRevenue],
    ['Kutilayotgan summa', ''], // Formula bilan
    ['', ''],
    ['⭐ STARS', ''],
    ['Jami stars sotildi', totalStars],
    ['', ''],
    ['📅 BUGUN', ''],
    ['Bugungi buyurtmalar', getTodayOrders(orders)],
    ['Bugungi tushum', getTodayRevenue(orders)]
  ];
  
  // Tozalash va yozish
  sheet.clear();
  for (var i = 0; i < statsData.length; i++) {
    sheet.getRange(i + 1, 1, 1, 2).setValues([statsData[i]]);
  }
  
  // Formatlash
  formatStatsSheet(sheet);
}

function getTodayOrders(orders) {
  var today = Utilities.formatDate(new Date(), 'Asia/Tashkent', 'dd.MM.yyyy');
  var count = 0;
  for (var i = 1; i < orders.length; i++) {
    if (orders[i][1].toString().startsWith(today)) {
      count++;
    }
  }
  return count;
}

function getTodayRevenue(orders) {
  var today = Utilities.formatDate(new Date(), 'Asia/Tashkent', 'dd.MM.yyyy');
  var revenue = 0;
  for (var i = 1; i < orders.length; i++) {
    if (orders[i][1].toString().startsWith(today) && orders[i][7] === "To'langan") {
      revenue += parseFloat(orders[i][6]) || 0;
    }
  }
  return revenue;
}

// ============================================
// FORMATTING
// ============================================

/**
 * Buyurtmalar sheet formatlash
 */
function formatOrdersSheet(sheet) {
  // Header
  var headers = ['ID', 'Sana', 'Mijoz', 'Username', 'Turi', 'Miqdor', 'Narx (UZS)', 'To\'lov holati', 'Stars yuborildi', 'Izoh'];
  sheet.getRange(1, 1, 1, headers.length).setValues([headers]);
  
  // Header rang - moviy
  sheet.getRange(1, 1, 1, headers.length)
    .setBackground('#2196F3')
    .setFontColor('#FFFFFF')
    .setFontWeight('bold')
    .setHorizontalAlignment('center');
  
  // Ustun kengliklari
  sheet.setColumnWidth(1, 50);   // ID
  sheet.setColumnWidth(2, 120);  // Sana
  sheet.setColumnWidth(3, 150);  // Mijoz
  sheet.setColumnWidth(4, 120);  // Username
  sheet.setColumnWidth(5, 80);   // Turi
  sheet.setColumnWidth(6, 80);   // Miqdor
  sheet.setColumnWidth(7, 100);  // Narx
  sheet.setColumnWidth(8, 120);  // Holat
  sheet.setColumnWidth(9, 120);  // Stars
  sheet.setColumnWidth(10, 200); // Izoh
  
  // Freeze header
  sheet.setFrozenRows(1);
}

/**
 * Yangi qatorni formatlash
 */
function formatNewRow(sheet, row) {
  // Juft/toq rang
  var bgColor = (row % 2 === 0) ? '#F5F5F5' : '#FFFFFF';
  sheet.getRange(row, 1, 1, 10).setBackground(bgColor);
  
  // Border
  var borderStyle = SpreadsheetApp.BorderStyle.SOLID;
  var borderColor = '#DDDDDD';
  sheet.getRange(row, 1, 1, 10).setBorder(
    true, true, true, true, null, null, 
    borderColor, borderStyle
  );
  
  // Markazga tekislash
  sheet.getRange(row, 1, 1, 10).setHorizontalAlignment('center');
  
  // Status rang
  var status = sheet.getRange(row, 8).getValue();
  formatStatusRow(sheet, row, status);
}

/**
 * Status bo'yicha rang qo'yish
 */
function formatStatusRow(sheet, row, status) {
  var statusCell = sheet.getRange(row, 8);
  
  if (status === "To'langan") {
    statusCell.setBackground('#C8E6C9').setFontColor('#2E7D32'); // Yashil
  } else if (status === 'Kutilmoqda') {
    statusCell.setBackground('#FFE082').setFontColor('#F57F17'); // Sariq
  } else if (status === 'Bekor qilindi') {
    statusCell.setBackground('#FFCDD2').setFontColor('#C62828'); // Qizil
  }
}

/**
 * Statistika sheet formatlash
 */
function formatStatsSheet(sheet) {
  // Sarlavha
  sheet.getRange(1, 1).setFontWeight('bold').setFontSize(14).setBackground('#2196F3').setFontColor('#FFFFFF');
  
  // Kategoriya sarlavhalari
  var categoryRows = [8, 12, 15]; // Moliyaviy, Stars, Bugun
  for (var i = 0; i < categoryRows.length; i++) {
    sheet.getRange(categoryRows[i], 1)
      .setFontWeight('bold')
      .setBackground('#E3F2FD');
  }
  
  // Ustun kengliklari
  sheet.setColumnWidth(1, 200);
  sheet.setColumnWidth(2, 150);
}

// ============================================
// HELPER FUNCTIONS
// ============================================

/**
 * Sheet olish yoki yaratish
 */
function getOrCreateSheet(name) {
  var sheet = SPREADSHEET.getSheetByName(name);
  if (!sheet) {
    sheet = SPREADSHEET.insertSheet(name);
  }
  return sheet;
}

/**
 * JSON javob qaytarish
 */
function jsonResponse(data) {
  return ContentService
    .createTextOutput(JSON.stringify(data))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Test funksiya
 */
function testAddOrder() {
  var result = addOrder({
    order_id: 1,
    username: 'test_user',
    order_type: 'Stars',
    amount: 1000,
    price_uzs: 120000,
    status: 'Kutilmoqda',
    note: 'Test order'
  });
  Logger.log(result);
}
