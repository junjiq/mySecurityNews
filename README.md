# SE NEWS // INTEL TERMINAL

SEエンジニア向けニュースアグリゲーター。
複数の技術情報ソースを自動収集し、ダークターミナル風UIで閲覧できます。

🔗 **[Live Demo](https://tokotokokame.github.io/sysnews-terminal/)**

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

## 機能

| タブ | 内容 |
|------|------|
| ◫ 月次まとめ | 月別アーカイブ・日次サマリー |
| ◈ フィード | 全ソースのリアルタイムフィード |
| ◎ 日次サマリー | 直近24時間のカテゴリ別まとめ |
| ⚑ セキュリティ | JPCERT・アドバイザリ・パッチ情報 |
| ↯ ペンテスト | Exploit・CVE・ツール・CTF情報 |
| ↑ トレンド | ホット記事・キーワードレーダー |

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
├── .github/workflows/
│   └── fetch_news.yml        # 自動収集スケジュール（毎時0分・30分）
├── data/
│   ├── news.json             # 収集データ（全ソース統合）
│   ├── summary.json          # 日次サマリーインデックス
│   ├── archive_index.json    # 月次アーカイブインデックス
│   └── daily/
│       └── YYYY-MM-DD.json   # 日次サマリー（過去30日分）
├── scripts/
│   ├── fetch_news.py         # ニュース収集スクリプト
│   ├── gen_summary.py        # 日次サマリー生成スクリプト
│   └── gen_archive.py        # 月次アーカイブ生成スクリプト
└── index.html                # フロントエンド（単一ファイル）
```

---

## 自動更新の仕組み

```
GitHub Actions（毎時0分・30分）
  ↓
fetch_news.py   → data/news.json 更新
gen_summary.py  → data/summary.json + data/daily/ 更新
gen_archive.py  → data/archive_index.json 更新
  ↓
git push → GitHub Pages 自動デプロイ
```

---

## 動作要件

- GitHub アカウント（無料プラン可）
- Public リポジトリ（GitHub Pages 使用のため）
- 外部APIキー不要（公開APIのみ使用）
