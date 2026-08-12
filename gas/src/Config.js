/**
 * アプリ全体の設定。
 *
 * スプレッドシートIDはコードに直接書かず、スクリプトプロパティ
 * `SPREADSHEET_ID` に保存する（コンテナバインドの場合は不要）。
 */

/** アプリ名。Web アプリのタイトルやメニュー名に使う。 */
var APP_TITLE = 'GAS Sheets App';

/** データを保存するシート名。 */
var SHEET_NAME = 'items';

/** ログを保存するシート名。 */
var LOG_SHEET_NAME = 'logs';

/** items シートのヘッダー定義。順序がそのまま列順になる。 */
var HEADERS = ['id', 'title', 'category', 'status', 'note', 'createdAt', 'updatedAt'];

/** status 列に入れられる値。 */
var STATUSES = ['todo', 'doing', 'done'];

/**
 * 対象のスプレッドシートを返す。
 *
 * コンテナバインドのスクリプトならバインド先を、スタンドアロンなら
 * スクリプトプロパティ `SPREADSHEET_ID` のシートを開く。
 *
 * @return {GoogleAppsScript.Spreadsheet.Spreadsheet}
 */
function getSpreadsheet() {
  var active = SpreadsheetApp.getActiveSpreadsheet();
  if (active) return active;

  var id = PropertiesService.getScriptProperties().getProperty('SPREADSHEET_ID');
  if (!id) {
    throw new Error(
      'スクリプトプロパティ SPREADSHEET_ID が未設定です。' +
        'GAS エディタの「プロジェクトの設定 > スクリプト プロパティ」で設定してください。'
    );
  }
  return SpreadsheetApp.openById(id);
}

/**
 * スクリプトプロパティを取得する。
 *
 * @param {string} key キー
 * @param {string=} defaultValue 未設定時に返す値
 * @return {string|null}
 */
function getProperty(key, defaultValue) {
  var value = PropertiesService.getScriptProperties().getProperty(key);
  return value === null || value === '' ? (defaultValue === undefined ? null : defaultValue) : value;
}
