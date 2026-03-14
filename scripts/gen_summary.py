#!/usr/bin/env python3
"""
日次サマリー生成
AI不使用・スコア上位記事をカテゴリ別に自動抽出
毎日 data/daily/YYYY-MM-DD.json を生成
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict

DATA_PATH    = Path("data/news.json")
DAILY_DIR    = Path("data/daily")
SUMMARY_PATH = Path("data/summary.json")

CATEGORY_MAP = {
    'hn':        'テクノロジー',
    'github':    'OSS・ツール',
    'zennqiita': '日本語技術記事',
    'jpcert':    'セキュリティ',
    'devto':     '英語技術記事',
    'project':   '注目リリース',
    'msf':       'CVE・脆弱性',
    'mitre':     'ATT&CK',
}

SEV_ORDER = {'critical':0,'high':1,'medium':2,'low':3,'info':4}

def parse_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z","+00:00"))
    except: return datetime.min.replace(tzinfo=timezone.utc)

def main():
    if not DATA_PATH.exists():
        print("[Summary] news.json not found, skipping")
        return

    data = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    items = data.get("items", [])
    now = datetime.now(timezone.utc)
    today_str = now.strftime("%Y-%m-%d")

    # 直近24時間の記事を対象
    cutoff = now - timedelta(hours=24)
    recent = [i for i in items if parse_dt(i.get("date","")) >= cutoff]

    # カテゴリ別に分類
    by_cat = defaultdict(list)
    for item in recent:
        cat = CATEGORY_MAP.get(item.get("source",""), 'その他')
        by_cat[cat].append(item)

    # 各カテゴリのトップ記事を抽出
    summary_cats = []
    cat_order = ['テクノロジー','OSS・ツール','日本語技術記事','セキュリティ',
                 'CVE・脆弱性','英語技術記事','注目リリース','ATT&CK','その他']

    for cat in cat_order:
        items_in_cat = by_cat.get(cat, [])
        if not items_in_cat:
            continue

        # セキュリティ・CVEはseverity順、他はscore順
        if cat in ('セキュリティ','CVE・脆弱性'):
            sorted_items = sorted(
                items_in_cat,
                key=lambda x: (SEV_ORDER.get(x.get('severity','info'), 4), -parse_dt(x.get('date','')).timestamp())
            )
        else:
            sorted_items = sorted(
                items_in_cat,
                key=lambda x: (-(x.get('score') or 0), -parse_dt(x.get('date','')).timestamp())
            )

        top = sorted_items[:5]
        summary_cats.append({
            "category": cat,
            "count": len(items_in_cat),
            "top_items": [
                {
                    "title": i.get("title",""),
                    "url":   i.get("url",""),
                    "score": i.get("score"),
                    "source": i.get("source",""),
                    "severity": i.get("severity"),
                    "date":  i.get("date",""),
                }
                for i in top
            ]
        })

    # セキュリティ重要記事（Critical/High）を別途抽出
    urgent = [
        i for i in recent
        if i.get("severity") in ("critical","high")
    ]
    urgent.sort(key=lambda x: SEV_ORDER.get(x.get('severity','info'),4))

    daily_summary = {
        "date":          today_str,
        "generated_at":  now.isoformat(),
        "total_articles": len(recent),
        "urgent_count":  len(urgent),
        "urgent_items": [
            {
                "title":    i.get("title",""),
                "url":      i.get("url",""),
                "severity": i.get("severity",""),
                "source":   i.get("source",""),
                "date":     i.get("date",""),
            }
            for i in urgent[:10]
        ],
        "categories": summary_cats,
    }

    # data/daily/YYYY-MM-DD.json に保存
    DAILY_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DAILY_DIR / f"{today_str}.json"
    out_path.write_text(json.dumps(daily_summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[Summary] {today_str}: {len(recent)} articles → {out_path}")

    # data/summary.json（最新サマリーへの参照）を更新
    # 過去30日分のサマリーインデックスを生成
    daily_files = sorted(DAILY_DIR.glob("*.json"), reverse=True)
    index = []
    for f in daily_files[:30]:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            index.append({
                "date":          d.get("date",""),
                "total_articles": d.get("total_articles",0),
                "urgent_count":  d.get("urgent_count",0),
                "file":          f"daily/{f.name}",
            })
        except: pass

    summary_index = {
        "updated_at": now.isoformat(),
        "latest":     f"daily/{today_str}.json",
        "days":       index,
    }
    SUMMARY_PATH.write_text(json.dumps(summary_index, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"[Summary] index updated: {len(index)} days")

if __name__ == "__main__":
    main()
