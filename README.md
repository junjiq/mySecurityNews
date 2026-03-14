# SE NEWS // INTEL TERMINAL

SEエンジニア向けニュースアグリゲーター。
複数の技術情報ソースを自動収集し、ダークターミナル風UIで閲覧できます。

---

## 収集ソース

| ソース | 内容 |
|--------|------|
| Hacker News | 技術系ホットトピック |
| GitHub Trending | 注目リポジトリ |
| Zenn / Qiita | 日本語技術記事 |
| JPCERT/CC | セキュリティ情報 |
| dev.to | 英語技術記事 |
| その他 | セキュリティ・インフラ・ツール関連 |

---

## セットアップ手順

### Step 1: リポジトリを作成

```
GitHub.com → New repository
公開設定: Public
```

### Step 2: ファイルをプッシュ

```bash
git init
git add .
git commit -m "init"
git remote add origin https://github.com/ユーザー名/リポジトリ名.git
git branch -M main
git push -u origin main
```

### Step 3: GitHub Pages を有効化

```
Settings → Pages
  Branch: main / (root) → Save
```

### Step 4: Actions を手動実行（初回）

```
Actions → "Fetch SE News" → Run workflow
```

約1〜2分でデータが取得され、サイトに表示されます。

---

## ファイル構成

```
├── .github/workflows/fetch.yml   # 自動収集スケジュール
├── data/news.json                # 収集データ
├── scripts/fetch_news.py         # 収集スクリプト
└── index.html                    # フロントエンド
```

---

## トラブルシューティング

- サイトが表示されない → Settings → Pages の設定を確認
- データが空 → Actions タブで Run workflow を手動実行
- 一部ソースが取得できない → 外部APIの一時障害。30分後に自動回復
