/**
 * スプレッドシートを 1 テーブルとして読み書きするデータアクセス層。
 *
 * 1 行 = 1 レコード、1 行目 = ヘッダー。ヘッダー名でオブジェクトに
 * 変換するので、列の並び替えに強い。
 */

/**
 * データシートを取得する。無ければヘッダー付きで作成する。
 *
 * @param {string=} name シート名（既定は SHEET_NAME）
 * @param {Array<string>=} headers ヘッダー（既定は HEADERS）
 * @return {GoogleAppsScript.Spreadsheet.Sheet}
 */
function getOrCreateSheet(name, headers) {
  var sheetName = name || SHEET_NAME;
  var cols = headers || HEADERS;
  var ss = getSpreadsheet();
  var sheet = ss.getSheetByName(sheetName);

  if (!sheet) {
    sheet = ss.insertSheet(sheetName);
  }
  if (sheet.getLastRow() === 0) {
    sheet.getRange(1, 1, 1, cols.length).setValues([cols]);
    sheet.setFrozenRows(1);
    sheet.getRange(1, 1, 1, cols.length).setFontWeight('bold');
  }
  return sheet;
}

/**
 * ヘッダー行を読み、列名 -> 列インデックス(0 始まり) のマップを返す。
 *
 * @param {GoogleAppsScript.Spreadsheet.Sheet} sheet シート
 * @return {{headers: Array<string>, index: Object<string, number>}}
 */
function readHeaders(sheet) {
  var lastCol = Math.max(sheet.getLastColumn(), 1);
  var headers = sheet.getRange(1, 1, 1, lastCol).getValues()[0].map(toStr);
  var index = {};
  headers.forEach(function (h, i) {
    if (h) index[h] = i;
  });
  return { headers: headers, index: index };
}

/**
 * 全レコードをオブジェクトの配列で返す。
 *
 * @param {string=} sheetName シート名
 * @return {Array<Object>}
 */
function findAll(sheetName) {
  var sheet = getOrCreateSheet(sheetName);
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return [];

  var meta = readHeaders(sheet);
  var values = sheet.getRange(2, 1, lastRow - 1, meta.headers.length).getValues();

  return values
    .map(function (row, i) {
      var record = { _row: i + 2 };
      meta.headers.forEach(function (h, c) {
        if (h) record[h] = toStr(row[c]);
      });
      return record;
    })
    .filter(function (record) {
      // id が空の行はゴミ行として無視する
      return record.id !== '';
    });
}

/**
 * id でレコードを 1 件取得する。見つからなければ null。
 *
 * @param {string} id レコード ID
 * @param {string=} sheetName シート名
 * @return {Object|null}
 */
function findById(id, sheetName) {
  var found = findAll(sheetName).filter(function (record) {
    return record.id === id;
  });
  return found.length ? found[0] : null;
}

/**
 * レコードを 1 件追加する。
 *
 * @param {Object} data 保存する値（id/createdAt/updatedAt は自動付与）
 * @param {string=} sheetName シート名
 * @return {Object} 追加されたレコード
 */
function insert(data, sheetName) {
  return withLock(function () {
    var sheet = getOrCreateSheet(sheetName);
    var meta = readHeaders(sheet);
    var timestamp = nowIso();

    var record = {};
    meta.headers.forEach(function (h) {
      if (h) record[h] = toStr(data[h]);
    });
    record.id = data.id ? toStr(data.id) : newId();
    record.createdAt = timestamp;
    record.updatedAt = timestamp;

    var row = meta.headers.map(function (h) {
      return h ? record[h] : '';
    });
    sheet.appendRow(row);

    record._row = sheet.getLastRow();
    return record;
  });
}

/**
 * レコードを 1 件更新する。渡されたキーのみ上書きする。
 *
 * @param {string} id レコード ID
 * @param {Object} data 更新する値
 * @param {string=} sheetName シート名
 * @return {Object} 更新後のレコード
 */
function update(id, data, sheetName) {
  return withLock(function () {
    var sheet = getOrCreateSheet(sheetName);
    var current = findById(id, sheetName);
    if (!current) throw new Error('レコードが見つかりません: ' + id);

    var meta = readHeaders(sheet);
    var merged = {};
    meta.headers.forEach(function (h) {
      if (!h) return;
      merged[h] = Object.prototype.hasOwnProperty.call(data, h) ? toStr(data[h]) : current[h];
    });
    merged.id = current.id;
    merged.createdAt = current.createdAt;
    merged.updatedAt = nowIso();

    var row = meta.headers.map(function (h) {
      return h ? merged[h] : '';
    });
    sheet.getRange(current._row, 1, 1, meta.headers.length).setValues([row]);

    merged._row = current._row;
    return merged;
  });
}

/**
 * レコードを 1 件削除する。
 *
 * @param {string} id レコード ID
 * @param {string=} sheetName シート名
 * @return {boolean} 削除できたら true
 */
function remove(id, sheetName) {
  return withLock(function () {
    var sheet = getOrCreateSheet(sheetName);
    var current = findById(id, sheetName);
    if (!current) return false;
    sheet.deleteRow(current._row);
    return true;
  });
}

/**
 * items / logs シートを初期化する。既存データは消さない。
 * スプレッドシートのメニューから実行する想定。
 */
function setupSheets() {
  var sheet = getOrCreateSheet(SHEET_NAME, HEADERS);

  // status 列に入力規則（プルダウン）を付ける
  var meta = readHeaders(sheet);
  if (meta.index.status !== undefined) {
    var rule = SpreadsheetApp.newDataValidation()
      .requireValueInList(STATUSES, true)
      .setAllowInvalid(false)
      .build();
    sheet.getRange(2, meta.index.status + 1, sheet.getMaxRows() - 1, 1).setDataValidation(rule);
  }
  sheet.autoResizeColumns(1, meta.headers.length);

  appendLog('INFO', 'setupSheets 実行');

  // メニューから呼ばれたときだけトーストを出す
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  if (ss) ss.toast('シートを初期化しました', APP_TITLE, 5);
}
