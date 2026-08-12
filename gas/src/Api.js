/**
 * クライアント（HTML）から google.script.run で呼び出す API 層。
 *
 * 戻り値は必ず `{ ok: true, data: ... }` / `{ ok: false, error: '...' }`
 * の形にそろえる。google.script.run はプレーンなオブジェクトしか
 * 返せないため、Date やクラスインスタンスは渡さない。
 */

/**
 * 成功レスポンスを組み立てる。
 *
 * @param {*} data 返す値
 * @return {{ok: boolean, data: *}}
 */
function ok(data) {
  return { ok: true, data: data === undefined ? null : data };
}

/**
 * 失敗レスポンスを組み立てる。
 *
 * @param {Error|string} error エラー
 * @return {{ok: boolean, error: string}}
 */
function fail(error) {
  var message = error && error.message ? error.message : String(error);
  return { ok: false, error: message };
}

/**
 * API 本体を実行し、例外をレスポンスに変換する。
 *
 * @param {string} name API 名（ログ用）
 * @param {function(): *} fn 実処理
 * @return {{ok: boolean, data: *}|{ok: boolean, error: string}}
 */
function handle(name, fn) {
  try {
    return ok(fn());
  } catch (err) {
    appendLog('ERROR', name + ' で例外', { message: String(err && err.message ? err.message : err) });
    return fail(err);
  }
}

/**
 * クライアントへ返す前にレコードを整形する（内部用の _row を落とす）。
 *
 * @param {Object} record レコード
 * @return {Object}
 */
function sanitize(record) {
  var copy = {};
  Object.keys(record).forEach(function (key) {
    if (key.charAt(0) !== '_') copy[key] = record[key];
  });
  return copy;
}

/**
 * 画面の初期表示に必要な情報をまとめて返す。
 *
 * @return {{ok: boolean, data: Object}}
 */
function apiGetBootstrap() {
  return handle('apiGetBootstrap', function () {
    return {
      appTitle: APP_TITLE,
      user: currentUserEmail(),
      statuses: STATUSES,
      headers: HEADERS,
      spreadsheetUrl: getSpreadsheet().getUrl()
    };
  });
}

/**
 * レコード一覧を返す。
 *
 * @param {{keyword: string, status: string}=} filter 絞り込み条件
 * @return {{ok: boolean, data: Array<Object>}}
 */
function apiListItems(filter) {
  return handle('apiListItems', function () {
    var conditions = filter || {};
    var keyword = toStr(conditions.keyword).trim().toLowerCase();
    var status = toStr(conditions.status).trim();

    return findAll()
      .filter(function (record) {
        if (status && record.status !== status) return false;
        if (!keyword) return true;
        return HEADERS.some(function (h) {
          return toStr(record[h]).toLowerCase().indexOf(keyword) >= 0;
        });
      })
      .sort(function (a, b) {
        return a.updatedAt < b.updatedAt ? 1 : a.updatedAt > b.updatedAt ? -1 : 0;
      })
      .map(sanitize);
  });
}

/**
 * レコードを 1 件追加する。
 *
 * @param {Object} form 入力値
 * @return {{ok: boolean, data: Object}}
 */
function apiCreateItem(form) {
  return handle('apiCreateItem', function () {
    var input = validateItem(form);
    var record = insert(input);
    appendLog('INFO', 'レコード追加', { id: record.id });
    return sanitize(record);
  });
}

/**
 * レコードを 1 件更新する。
 *
 * @param {string} id レコード ID
 * @param {Object} form 入力値
 * @return {{ok: boolean, data: Object}}
 */
function apiUpdateItem(id, form) {
  return handle('apiUpdateItem', function () {
    if (!toStr(id)) throw new Error('id が指定されていません。');
    var input = validateItem(form);
    var record = update(id, input);
    appendLog('INFO', 'レコード更新', { id: id });
    return sanitize(record);
  });
}

/**
 * レコードを 1 件削除する。
 *
 * @param {string} id レコード ID
 * @return {{ok: boolean, data: {deleted: boolean}}}
 */
function apiDeleteItem(id) {
  return handle('apiDeleteItem', function () {
    if (!toStr(id)) throw new Error('id が指定されていません。');
    var deleted = remove(id);
    if (!deleted) throw new Error('レコードが見つかりません: ' + id);
    appendLog('INFO', 'レコード削除', { id: id });
    return { deleted: true };
  });
}

/**
 * 入力値を検証し、保存できる形に正規化する。
 *
 * @param {Object} form 入力値
 * @return {{title: string, category: string, status: string, note: string}}
 */
function validateItem(form) {
  var input = form || {};
  var title = toStr(input.title).trim();
  if (!title) throw new Error('タイトルは必須です。');
  if (title.length > 200) throw new Error('タイトルは 200 文字以内にしてください。');

  var status = toStr(input.status).trim() || STATUSES[0];
  if (STATUSES.indexOf(status) < 0) {
    throw new Error('status は次のいずれかにしてください: ' + STATUSES.join(', '));
  }

  return {
    title: title,
    category: toStr(input.category).trim(),
    status: status,
    note: toStr(input.note).trim()
  };
}
