#!/usr/bin/env python3
"""
月別アーカイブ生成
毎月1日に前月分を data/archive/YYYY-MM.json として保存
"""

import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from collections import defaultdict, Counter

DATA_PATH   = Path("data/news.json")
ARCHIVE_DIR = Path("data/archive")
ARCHIVE_IDX = Path("data/archive_index.json")

def parse_dt(s):
    try: return datetime.fromisoformat(str(s).replace("Z","+00:00"))
    except: return datetime.min.replace(tzinfo=timezone.utc)

def main():
    if not DATA_PATH.exists():
        print("[Archive] news.json not found, skipping")
        return

    data  = json.loads(DATA_PATH.read_text(encoding='utf-8'))
    items = data.get("items", [])
    now   = datetime.now(timezone.utc)

    # 今月と先月の両方をアーカイブ対象にする
    months_to_archive = []
    # 先月
    first_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    last_month_end = first_of_month - timedelta(seconds=1)
    last_month_start = last_month_end.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    months_to_archive.append((
        last_month_start.strftime("%Y-%m"),
        last_month_start,
        first_of_month,
    ))
    # 今月（部分アーカイブ）
    months_to_archive.append((
        now.strftime("%Y-%m"),
        first_of_month,
        now,
    ))

    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)

    for month_str, start, end in months_to_archive:
        month_items = [
            i for i in items
            if start <= parse_dt(i.get("date","")) < end
        ]
        if not month_items:
            continue

        # ソース別集計
        source_counts = Counter(i.get("source","") for i in month_items)

        # 重要度別集計
        sev_counts = Counter(i.get("severity","") for i in month_items if i.get("severity"))

        # スコア上位記事 Top20
        top_articles = sorted(
            [i for i in month_items if i.get("score")],
            key=lambda x: -(x.get("score") or 0)
        )[:20]

        # セキュリティ重要記事
        security_items = sorted(
            [i for i in month_items if i.get("severity") in ("critical","high")],
            key=lambda x: parse_dt(x.get("date","")),
            reverse=True
        )[:30]

        archive = {
            "month":         month_str,
            "generated_at":  now.isoformat(),
            "total_articles": len(month_items),
            "source_counts": dict(source_counts.most_common()),
            "severity_counts": dict(sev_counts),
            "top_articles": [
                {
                    "title":  i.get("title",""),
                    "url":    i.get("url",""),
                    "score":  i.get("score"),
                    "source": i.get("source",""),
                    "date":   i.get("date",""),
                }
                for i in top_articles
            ],
            "security_highlights": [
                {
                    "title":    i.get("title",""),
                    "url":      i.get("url",""),
                    "severity": i.get("severity",""),
                    "source":   i.get("source",""),
                    "date":     i.get("date",""),
                }
                for i in security_items
            ],
        }

        out = ARCHIVE_DIR / f"{month_str}.json"
        out.write_text(json.dumps(archive, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"[Archive] {month_str}: {len(month_items)} articles → {out}")

    # アーカイブインデックス更新
    archive_files = sorted(ARCHIVE_DIR.glob("*.json"), reverse=True)
    index = []
    for f in archive_files:
        try:
            d = json.loads(f.read_text(encoding='utf-8'))
            index.append({
                "month":          d.get("month",""),
                "total_articles": d.get("total_articles",0),
                "file":           f"archive/{f.name}",
            })
        except: pass

    ARCHIVE_IDX.write_text(
        json.dumps({"updated_at": now.isoformat(), "months": index},
                   ensure_ascii=False, indent=2),
        encoding='utf-8'
    )
    print(f"[Archive] index: {len(index)} months")

if __name__ == "__main__":
    main()
