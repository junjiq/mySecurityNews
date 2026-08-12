/**
 * GAS エディタから手動で実行する簡易テスト。
 * `runAllTests` を実行し、実行ログ（Ctrl+Enter）で結果を確認する。
 *
 * テストデータは実行後に削除されるが、本番シートでは実行しないこと。
 */

/**
 * 全テストを実行する。
 */
function runAllTests() {
  var tests = [
    testValidateItem_,
    testCrud_,
    testListFilter_
  ];

  var passed = 0;
  var failed = 0;

  tests.forEach(function (test) {
    try {
      test();
      passed++;
      console.log('PASS: ' + test.name);
    } catch (err) {
      failed++;
      console.error('FAIL: ' + test.name + ' -> ' + (err && err.message ? err.message : err));
    }
  });

  console.log('---- ' + passed + ' passed / ' + failed + ' failed ----');
}

/**
 * 条件が偽なら例外を投げる。
 *
 * @param {boolean} condition 条件
 * @param {string} message 失敗時のメッセージ
 */
function assert_(condition, message) {
  if (!condition) throw new Error(message || 'assertion failed');
}

/**
 * 2 値が等しくなければ例外を投げる。
 *
 * @param {*} actual 実測値
 * @param {*} expected 期待値
 * @param {string=} message メッセージ
 */
function assertEquals_(actual, expected, message) {
  assert_(actual === expected, (message || 'not equal') + ': expected=' + expected + ' actual=' + actual);
}

/**
 * fn が例外を投げることを確認する。
 *
 * @param {function(): *} fn 実行する処理
 * @param {string=} message メッセージ
 */
function assertThrows_(fn, message) {
  var thrown = false;
  try {
    fn();
  } catch (err) {
    thrown = true;
  }
  assert_(thrown, message || '例外が発生しませんでした');
}

/** 入力検証のテスト。 */
function testValidateItem_() {
  var normalized = validateItem({ title: '  テスト  ', status: 'doing' });
  assertEquals_(normalized.title, 'テスト', 'title がトリムされる');
  assertEquals_(normalized.status, 'doing', 'status がそのまま通る');
  assertEquals_(validateItem({ title: 'x' }).status, STATUSES[0], 'status 未指定なら既定値');

  assertThrows_(function () {
    validateItem({ title: '   ' });
  }, 'タイトル必須のエラー');

  assertThrows_(function () {
    validateItem({ title: 'x', status: 'unknown' });
  }, '不正な status のエラー');
}

/** 追加・更新・削除のテスト。 */
function testCrud_() {
  var created = apiCreateItem({ title: '__test__ CRUD', category: 'test', status: 'todo' });
  assert_(created.ok, '作成に成功する: ' + created.error);
  var id = created.data.id;
  assert_(!!id, 'id が採番される');

  var updated = apiUpdateItem(id, { title: '__test__ CRUD 更新', status: 'done' });
  assert_(updated.ok, '更新に成功する: ' + updated.error);
  assertEquals_(updated.data.status, 'done', 'status が更新される');
  assertEquals_(updated.data.createdAt, created.data.createdAt, 'createdAt は保持される');

  var deleted = apiDeleteItem(id);
  assert_(deleted.ok, '削除に成功する: ' + deleted.error);
  assertEquals_(findById(id), null, '削除後は取得できない');

  var missing = apiDeleteItem(id);
  assert_(!missing.ok, '存在しない id の削除は失敗する');
}

/** 一覧の絞り込みのテスト。 */
function testListFilter_() {
  var created = apiCreateItem({ title: '__test__ フィルタ対象', category: 'zzz-filter', status: 'doing' });
  assert_(created.ok, '作成に成功する: ' + created.error);
  var id = created.data.id;

  try {
    var byKeyword = apiListItems({ keyword: 'zzz-filter' });
    assert_(byKeyword.ok, '一覧取得に成功する');
    assertEquals_(byKeyword.data.length, 1, 'キーワードで 1 件に絞られる');
    assert_(byKeyword.data[0]._row === undefined, '内部用の _row は返さない');

    var byStatus = apiListItems({ keyword: 'zzz-filter', status: 'done' });
    assertEquals_(byStatus.data.length, 0, 'status が一致しなければ 0 件');
  } finally {
    apiDeleteItem(id);
  }
}
