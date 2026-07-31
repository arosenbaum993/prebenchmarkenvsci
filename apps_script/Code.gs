// Environmental Science Benchmark -- Google Sheet logger (doPost)
// 1) In your Google Sheet: Extensions > Apps Script. Delete any code, paste this.
// 2) Deploy > New deployment > Web app.
//      Execute as: Me      Who has access: Anyone
// 3) Copy the /exec URL into the benchmark's Data tab (SHEET_ENDPOINT).
// The SECRET below must match the SECRET shown in the benchmark's Data tab.
var SECRET = "sev2606-arbench-2026";

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    if (data.secret !== SECRET) {
      return ContentService.createTextOutput(JSON.stringify({ok:false, error:"bad secret"}))
        .setMimeType(ContentService.MimeType.JSON);
    }
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var sh = ss.getSheetByName("Responses") || ss.insertSheet("Responses");
    if (sh.getLastRow() === 0) {
      sh.appendRow(["Timestamp","Name","Period","Form","Score","Total","Percent","Level",
                    "SEV1 %","SEV2 %","SEV3 %","SEV4 %","SEV5 %","Answers (JSON)"]);
    }
    var d = data.domains || {};
    function p(x){ return (x && typeof x.pct === "number") ? x.pct : ""; }
    sh.appendRow([data.ts || new Date(), data.name || "", data.period || "", data.form || "",
                  data.score || 0, data.total || 0, data.pct || 0, data.level || "",
                  p(d.SEV1), p(d.SEV2), p(d.SEV3), p(d.SEV4), p(d.SEV5),
                  JSON.stringify(data.answers || {})]);
    return ContentService.createTextOutput(JSON.stringify({ok:true}))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok:false, error:String(err)}))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

function doGet() {
  return ContentService.createTextOutput("Environmental Science benchmark endpoint is live.");
}
