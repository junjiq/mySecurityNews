/**
 * エントリポイント。Web アプリ／スプレッドシートのメニューを定義する。
 */

/**
 * Web アプリの GET ハンドラ。
 *
 * @param {GoogleAppsScript.Events.DoGet} e イベント
 * @return {GoogleAppsScript.HTML.HtmlOutput}
 */
function doGet(e) {
  var params = (e && e.parameter) || {};
  var page = allowedPage(params.page);

  return HtmlService.createTemplateFromFile('ui/' + page)
    .evaluate()
    .setTitle(APP_TITLE)
    .addMetaTag('viewport', 'width=device-width, initial-scale=1')
    .setXFrameOptionsMode(HtmlService.XFrameOptionsMode.ALLOWALL);
}

/**
 * 表示してよいページ名だけを通す。未知の値は index にフォールバックする。
 *
 * @param {string} page クエリパラメータの page
 * @return {string}
 */
function allowedPage(page) {
  var pages = ['index'];
  return pages.indexOf(toStr(page)) >= 0 ? page : 'index';
}

/**
 * HTML テンプレートから別の HTML ファイルを読み込む。
 * 使い方: <?!= include('ui/stylesheet'); ?>
 *
 * @param {string} filename 拡張子を除いたファイル名
 * @return {string}
 */
function include(filename) {
  return HtmlService.createHtmlOutputFromFile(filename).getContent();
}

/**
 * スプレッドシートを開いたときにカスタムメニューを追加する。
 */
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu(APP_TITLE)
    .addItem('サイドバーを開く', 'showSidebar')
    .addItem('ダイアログを開く', 'showDialog')
    .addSeparator()
    .addItem('シートを初期化する', 'setupSheets')
    .addToUi();
}

/**
 * サイドバーを表示する。
 */
function showSidebar() {
  var html = HtmlService.createTemplateFromFile('ui/sidebar')
    .evaluate()
    .setTitle(APP_TITLE);
  SpreadsheetApp.getUi().showSidebar(html);
}

/**
 * モーダルダイアログを表示する。
 */
function showDialog() {
  var html = HtmlService.createTemplateFromFile('ui/index')
    .evaluate()
    .setWidth(900)
    .setHeight(640);
  SpreadsheetApp.getUi().showModalDialog(html, APP_TITLE);
}
