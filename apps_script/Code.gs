/**
 * Environmental Science Diagnostic — class results collector.
 *
 * Paste this into the Apps Script editor of a Google Sheet
 * (Extensions -> Apps Script), then deploy it as a Web app
 * ("Execute as: Me", "Who has access: Anyone").  See GOOGLE_SHEET_SETUP.md
 * for the full click-by-click walkthrough.
 *
 * The test PostS each student's results here (one row per submission).
 * The class analyzer reads them back with a JSONP GET, so no student ever
 * copies or pastes a code.
 */

var SHEET_NAME = 'Responses';

function doPost(e) {
  var lock = LockService.getScriptLock();
  lock.waitLock(30000); // avoid two submissions writing at once
  try {
    var data = JSON.parse(e.postData.contents);
    var sheet = getSheet_();
    sheet.appendRow([
      new Date(),
      data.f || '',                 // form (A = pre, B = post)
      data.n || '',                 // student name
      data.c || '',                 // class / period
      data.i || '',                 // student id (optional)
      JSON.stringify(data.a || {})  // answers: {itemId: selectedIndex, ...} (-1 = blank)
    ]);
    return json_({ ok: true });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  var sheet = getSheet_();
  var values = sheet.getDataRange().getValues();
  var rows = [];
  for (var i = 1; i < values.length; i++) { // row 0 is the header
    var r = values[i];
    if (!r[1] && !r[2]) continue;            // skip blank rows
    rows.push({ ts: r[0], f: r[1], n: r[2], c: r[3], i: r[4], a: safeParse_(r[5]) });
  }
  var payload = JSON.stringify({ ok: true, count: rows.length, rows: rows });
  var cb = e && e.parameter && e.parameter.callback;
  if (cb) {
    // JSONP: lets the analyzer read cross-origin without a CORS error.
    return ContentService.createTextOutput(cb + '(' + payload + ')')
      .setMimeType(ContentService.MimeType.JAVASCRIPT);
  }
  return ContentService.createTextOutput(payload)
    .setMimeType(ContentService.MimeType.JSON);
}

function getSheet_() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sh = ss.getSheetByName(SHEET_NAME);
  if (!sh) {
    sh = ss.insertSheet(SHEET_NAME);
    sh.appendRow(['Timestamp', 'Form', 'Name', 'Class', 'StudentID', 'Answers']);
    sh.setFrozenRows(1);
  }
  return sh;
}

function json_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

function safeParse_(s) {
  try { return JSON.parse(s); } catch (e) { return {}; }
}
