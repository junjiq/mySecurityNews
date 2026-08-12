# gas — Google Apps Script + HTML + スプレッドシート プロジェクト環境

Google Apps Script（GAS）の V8 ランタイム、HTML Service の画面、Google スプレッドシートを
データストアとして組み合わせた、そのまま動かせるひな形です。
ローカルで編集して [clasp](https://github.com/google/clasp) で GAS に push する構成になっています。

## できること

- スプレッドシートを 1 テーブルとして扱う CRUD（追加 / 一覧 / 更新 / 削除）
- Web アプリ画面（`doGet`）、スプレッドシートのサイドバー、モーダルダイアログの 3 つの UI
- キーワード / ステータスでの絞り込み
- `google.script.run` を Promise でラップしたクライアント API
- 書き込み時の排他ロック（LockService）と `logs` シートへの操作ログ
- GAS エディタ上で実行できる簡易テスト（`runAllTests`）

## ディレクトリ構成

```
.
├── src/                      # clasp の rootDir。ここだけが GAS へ push される
│   ├── appsscript.json       # マニフェスト（タイムゾーン / スコープ / Web アプリ設定）
│   ├── Config.js             # アプリ設定・スプレッドシートの取得
│   ├── Utils.js              # ID 生成・日時整形・排他ロック・ログ
│   ├── SheetService.js       # シートへの読み書き（データアクセス層）
│   ├── Api.js                # クライアントから呼ぶ API 層（戻り値を {ok, data} に統一）
│   ├── Code.js               # doGet / onOpen / include などのエントリポイント
│   ├── Tests.js              # GAS エディタから実行する簡易テスト
│   └── ui/
│       ├── index.html        # Web アプリ本体（一覧 + フォーム）
│       ├── stylesheet.html   # CSS（include で読み込む）
│       ├── javascript.html   # クライアント JS（include で読み込む）
│       └── sidebar.html      # サイドバー用のクイック登録フォーム
├── .clasp.json.example       # scriptId を書いてリネームして使う
├── .claspignore
├── .eslintrc.json
├── .prettierrc.json
├── package.json
└── .github/workflows/deploy.yml  # 手動実行の clasp push ワークフロー
```

`src/ui/index.html` は GAS 上では `ui/index` というファイル名になります。
`include('ui/stylesheet')` のようにスラッシュ付きで参照してください。

## セットアップ

### 1. 依存パッケージのインストール

```bash
npm install
```

### 2. clasp にログイン

```bash
npx clasp login
```

初回のみ Apps Script API の有効化が必要です。
<https://script.google.com/home/usersettings> で「Google Apps Script API」を ON にしてください。

### 3. Apps Script プロジェクトを用意する

**A. スプレッドシートに紐づける（コンテナバインド / おすすめ）**

1. 新しい Google スプレッドシートを作成する
2. 「拡張機能 > Apps Script」を開く
3. 「プロジェクトの設定」に表示される **スクリプト ID** を控える

**B. 独立したプロジェクトにする（スタンドアロン）**

```bash
npx clasp create --type standalone --title "GAS Sheets App" --rootDir src
```

作成後、GAS エディタの「プロジェクトの設定 > スクリプト プロパティ」で
`SPREADSHEET_ID` に対象スプレッドシートの ID を設定してください。

### 4. .clasp.json を作る

```bash
cp .clasp.json.example .clasp.json
```

`scriptId` を手順 3 で控えた値に置き換えます。
`.clasp.json` は環境ごとに異なるため `.gitignore` 済みです。

### 5. push する

```bash
npm run push        # clasp push
npm run watch       # 保存のたびに自動 push
```

初回は `Manifest file has been updated. Do you want to push and overwrite?` と聞かれるので `y` を選びます。

### 6. 初期化して動かす

1. スプレッドシートを開き直すと、メニューに「GAS Sheets App」が追加される
2. 「シートを初期化する」を実行して `items` シートを作る
3. 「サイドバーを開く」または「ダイアログを開く」で UI を確認する

### 7. Web アプリとして公開する

GAS エディタの「デプロイ > 新しいデプロイ > ウェブアプリ」から公開します。
公開範囲は `src/appsscript.json` の `webapp.access` が既定値（`MYSELF`）です。
社内やチームに公開する場合は `DOMAIN`、誰でもアクセスさせる場合は `ANYONE` に変更してください。

CLI からも実行できます。

```bash
npx clasp deploy --description "初回リリース"
npx clasp deployments
```

## 開発の流れ

| コマンド | 内容 |
| --- | --- |
| `npm run push` | ローカルの `src/` を GAS へ反映 |
| `npm run watch` | ファイル保存のたびに自動 push |
| `npm run pull` | GAS 側の変更をローカルへ取り込む |
| `npm run open` | ブラウザで GAS エディタを開く |
| `npm run logs` | 実行ログをストリーミング表示 |
| `npm run lint` | ESLint で静的チェック |
| `npm run format` | Prettier で整形 |

### テスト

ローカル実行ではなく、GAS エディタ上で `runAllTests` を実行し、
実行ログ（`Ctrl` + `Enter`）で結果を確認します。テストは `__test__` で始まる
レコードを作って最後に削除しますが、本番シートでは実行しないでください。

## データ構造

`items` シート（1 行目がヘッダー、`HEADERS` の順に列が並びます）

| 列 | 内容 |
| --- | --- |
| `id` | UUID。自動採番 |
| `title` | タイトル（必須・200 文字以内） |
| `category` | カテゴリ（任意） |
| `status` | `todo` / `doing` / `done` |
| `note` | メモ（任意） |
| `createdAt` | 作成日時（ISO 8601） |
| `updatedAt` | 更新日時（ISO 8601） |

`logs` シートには操作ログが追記されます。

列を増やしたいときは `src/Config.js` の `HEADERS` に追加し、
`src/Api.js` の `validateItem` に検証を足してください。
読み書きはヘッダー名で行うため、列の並び替えには自動で追従します。

## サーバー API

クライアントからは `google.script.run` 経由で呼び出します。
すべて `{ ok: true, data: ... }` または `{ ok: false, error: '...' }` を返します。

| 関数 | 内容 |
| --- | --- |
| `apiGetBootstrap()` | 画面の初期表示に必要な情報（アプリ名 / ユーザー / ステータス一覧 / シート URL） |
| `apiListItems({keyword, status})` | 一覧取得（更新日時の降順） |
| `apiCreateItem(form)` | 1 件追加 |
| `apiUpdateItem(id, form)` | 1 件更新 |
| `apiDeleteItem(id)` | 1 件削除 |

`src/ui/javascript.html` の `call()` がこれを Promise に変換しているので、
クライアント側は `call('apiListItems', {keyword: 'foo'}).then(...)` と書けます。

## CI から自動デプロイする（任意）

`.github/workflows/deploy.yml` は手動実行（workflow_dispatch）の push ワークフローです。
使う場合はリポジトリの Secrets に次の 2 つを登録してください。

| Secret | 値 |
| --- | --- |
| `CLASPRC_JSON` | ローカルの `~/.clasprc.json` の中身をそのまま |
| `SCRIPT_ID` | Apps Script のスクリプト ID |

`~/.clasprc.json` には OAuth のリフレッシュトークンが含まれます。
リポジトリを必ずプライベートのままにし、ファイル自体はコミットしないでください。

## 注意点

- `.clasp.json` と `~/.clasprc.json` は認証情報・環境固有の値を含むためコミットしない
- スプレッドシート ID をコードに直書きせず、スクリプトプロパティ `SPREADSHEET_ID` を使う
- 画面へ値を差し込むときは `textContent` を使う（`innerHTML` は使わない）
- 書き込み処理は `withLock()` の中で行い、同時実行によるデータ破損を防ぐ
- 1 回の実行は 6 分で打ち切られる。大量データは分割処理かバッチ（時間主導トリガー）にする
