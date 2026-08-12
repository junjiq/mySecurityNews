/**
 * 汎用ユーティリティ。
 */

/**
 * 一意な ID を生成する。
 *
 * @return {string}
 */
function newId() {
  return Utilities.getUuid();
}

/**
 * 現在時刻を ISO 8601 文字列で返す。
 *
 * @return {string}
 */
function nowIso() {
  return Utilities.formatDate(new Date(), Session.getScriptTimeZone(), "yyyy-MM-dd'T'HH:mm:ssXXX");
}

/**
 * 値を安全に文字列化する。null / undefined は空文字にする。
 *
 * @param {*} value 任意の値
 * @return {string}
 */
function toStr(value) {
  if (value === null || value === undefined) return '';
  if (value instanceof Date) {
    return Utilities.formatDate(value, Session.getScriptTimeZone(), "yyyy-MM-dd'T'HH:mm:ssXXX");
  }
  return String(value);
}

/** withLock の入れ子の深さ。同一実行内での二重ロックを避けるために使う。 */
var __lockDepth = 0;

/**
 * 排他ロックを取得して処理を実行する。
 * 同時書き込みによるデータ破損を防ぐために書き込み系の処理で使う。
 * 入れ子で呼ばれた場合は既に取得済みのロックをそのまま使う。
 *
 * @param {function(): *} fn ロック内で実行する処理
 * @param {number=} timeoutMs ロック待ち時間（既定 20 秒）
 * @return {*} fn の戻り値
 */
function withLock(fn, timeoutMs) {
  if (__lockDepth > 0) {
    __lockDepth++;
    try {
      return fn();
    } finally {
      __lockDepth--;
    }
  }

  var lock = LockService.getScriptLock();
  if (!lock.tryLock(timeoutMs || 20000)) {
    throw new Error('他の処理が実行中です。しばらくしてからもう一度お試しください。');
  }
  __lockDepth++;
  try {
    return fn();
  } finally {
    __lockDepth--;
    lock.releaseLock();
  }
}

/**
 * logs シートに 1 行追記する。シートが無ければ作成する。
 *
 * @param {string} level 'INFO' | 'WARN' | 'ERROR'
 * @param {string} message メッセージ
 * @param {*=} detail 追加情報（JSON 化して保存）
 */
function appendLog(level, message, detail) {
  try {
    var ss = getSpreadsheet();
    var sheet = ss.getSheetByName(LOG_SHEET_NAME);
    if (!sheet) {
      sheet = ss.insertSheet(LOG_SHEET_NAME);
      sheet.appendRow(['timestamp', 'level', 'user', 'message', 'detail']);
      sheet.setFrozenRows(1);
    }
    sheet.appendRow([
      nowIso(),
      level,
      currentUserEmail(),
      message,
      detail === undefined ? '' : JSON.stringify(detail)
    ]);
  } catch (err) {
    // ログ書き込み失敗で本処理を止めない
    console.error('appendLog failed: ' + err);
  }
}

/**
 * 実行ユーザーのメールアドレス。取得できない場合は空文字。
 *
 * @return {string}
 */
function currentUserEmail() {
  try {
    return Session.getActiveUser().getEmail() || '';
  } catch (err) {
    return '';
  }
}
