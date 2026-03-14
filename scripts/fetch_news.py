#!/usr/bin/env python3
"""
SE News Fetcher v3
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
通常ソース: HN / GitHub / Zenn / Qiita / JPCERT / dev.to
プロジェクト専用: Anthropic / Hetzner / HTB / Tool Releases
MITRE/MSF: ATT&CK / Exploit-DB / NVD
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
セキュリティ対策:
  - ペイウォール/広告ドメインを自動除外
  - GitHub Token 使用時はレート制限回避
  - タイムアウト・リトライ設定
  - 外部サービスのAPIキーは一切使用しない
"""

import json, time, hashlib, os, sys
import requests, feedparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH   = Path("data/news.json")
MAX_PER     = 20
TIMEOUT     = 15
RETRIES     = 2

# ── ペイウォール・広告ドメイン ブロックリスト ───────────────
BLOCKED = {
    'medium.com', 'wsj.com', 'nytimes.com', 'ft.com',
    'bloomberg.com', 'forbes.com', 'wired.com',
    'technologyreview.com', 'businessinsider.com',
    'theatlantic.com', 'economist.com', 'hbr.org',
    'fastcompany.com', 'inc.com', 'entrepreneur.com',
}

def is_blocked(url: str) -> bool:
    try:
        d = urlparse(url).hostname or ''
        return any(b in d for b in BLOCKED)
    except:
        return False

# ── ヘッダー（Bot識別） ──────────────────────────────────────
HEADERS = {"User-Agent": "SE-News-Bot/3.0 (educational aggregator)"}

# ── GitHub Token（オプション・レート制限回避用） ──────────────
GH_TOKEN = os.environ.get('GITHUB_TOKEN', '')
GH_HEADERS = {**HEADERS, **({"Authorization": f"token {GH_TOKEN}"} if GH_TOKEN else {})}

def now():
    return datetime.now(timezone.utc).isoformat()

def safe_get(url, headers=None, params=None, retries=RETRIES):
    for attempt in range(retries + 1):
        try:
            r = requests.get(url, headers=headers or HEADERS,
                             params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as e:
            if attempt == retries:
                print(f"  [WARN] {url[:70]}: {e}")
                return None
            time.sleep(1)
    return None

def load_existing():
    if DATA_PATH.exists():
        try:
            return json.loads(DATA_PATH.read_text(encoding='utf-8'))
        except:
            pass
    return {"items": [], "updated_at": ""}

# ── セキュリティ重要度分類 ──────────────────────────────────
SEV_KW = {
    'critical': ['rce', 'remote code execution', 'critical', 'zero-day', '0day', 'ransomware', '緊急'],
    'high':     ['exploit', 'vulnerability', 'cve', 'privilege escalation', 'bypass', '脆弱性'],
    'medium':   ['patch', 'update', 'advisory', 'warning', 'threat', 'malware', 'phishing'],
}
def classify_sev(title, tags, source):
    if source in ('jpcert',):
        t = title.lower()
        if any(k in t for k in SEV_KW['critical']): return 'critical'
        return 'high' if 'アラート' in ' '.join(tags) else 'info'
    t = (title + ' ' + ' '.join(tags)).lower()
    for sev, kws in SEV_KW.items():
        if any(k in t for k in kws): return sev
    return None

# ════════════════════════════════════════════════════════════
#  通常ソース
# ════════════════════════════════════════════════════════════

def fetch_hn():
    print("[HN] Fetching...")
    r = safe_get("https://hacker-news.firebaseio.com/v0/topstories.json")
    if not r: return []
    items = []
    for id_ in r.json()[:MAX_PER]:
        r2 = safe_get(f"https://hacker-news.firebaseio.com/v0/item/{id_}.json")
        if not r2: continue
        d = r2.json()
        if not d or not d.get('url') or is_blocked(d['url']): continue
        items.append({
            "id": f"hn-{d['id']}", "source": "hn",
            "title": d.get('title',''), "url": d['url'],
            "score": d.get('score'), "comments": d.get('descendants',0),
            "author": d.get('by',''), "tags": [],
            "date": datetime.fromtimestamp(d['time'], tz=timezone.utc).isoformat(),
        })
        time.sleep(0.04)
    print(f"  → {len(items)}")
    return items

def fetch_github_trending():
    print("[GitHub Trending] Fetching...")
    items = []
    # unofficial API
    r = safe_get("https://gh-trending-api.herokuapp.com/repositories?since=daily")
    if r:
        try:
            for repo in r.json()[:MAX_PER]:
                items.append({
                    "id": f"gh-{repo.get('author','')}-{repo.get('name','')}",
                    "source": "github",
                    "title": f"{repo.get('author','')}/{repo.get('name','')} — {repo.get('description') or ''}",
                    "url": repo.get("url",""),
                    "score": None, "stars": str(repo.get("stars","")),
                    "author": repo.get("author",""),
                    "tags": [repo["language"]] if repo.get("language") else [],
                    "date": now(),
                })
        except: pass
    if not items:
        feed = feedparser.parse("https://github.com/trending.atom")
        for e in feed.entries[:MAX_PER]:
            items.append({
                "id": f"gh-fallback-{e.get('id','')[-12:]}",
                "source": "github",
                "title": e.get("title",""), "url": e.get("link",""),
                "score": None, "author": e.get("author",""),
                "tags": [], "date": now(),
            })
    print(f"  → {len(items)}")
    return items

def fetch_zenn():
    print("[Zenn] Fetching...")
    feed = feedparser.parse("https://zenn.dev/feed")
    items = [e for e in feed.entries if not is_blocked(e.get('link',''))]
    result = []
    for e in items[:MAX_PER]:
        result.append({
            "id": f"zenn-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
            "source": "zennqiita", "sub_source": "Zenn",
            "title": e.get("title",""), "url": e.get("link",""),
            "score": None, "author": e.get("author","Zenn"),
            "tags": ["Zenn"], "date": e.get("published", now()),
        })
    print(f"  → {len(result)}")
    return result

def fetch_qiita():
    print("[Qiita] Fetching...")
    feed = feedparser.parse("https://qiita.com/popular-items/feed.atom")
    result = []
    for e in feed.entries[:MAX_PER]:
        url = e.get("link","")
        if is_blocked(url): continue
        result.append({
            "id": f"qiita-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
            "source": "zennqiita", "sub_source": "Qiita",
            "title": e.get("title",""), "url": url,
            "score": None, "author": e.get("author","Qiita"),
            "tags": ["Qiita"], "date": e.get("updated", now()),
        })
    print(f"  → {len(result)}")
    return result

def fetch_jpcert():
    print("[JPCERT] Fetching...")
    items = []
    for feed_url, label, sev in [
        ("https://www.jpcert.or.jp/feed/news.rdf",    "ニュース",  "info"),
        ("https://www.jpcert.or.jp/feed/alerts.rdf",  "アラート",  "high"),
        ("https://www.jpcert.or.jp/feed/vulnotes.rdf","脆弱性",   "medium"),
    ]:
        try:
            feed = feedparser.parse(feed_url)
            for e in feed.entries[:10]:
                items.append({
                    "id": f"jpcert-{label[0]}-{hashlib.md5(e.get('id','').encode()).hexdigest()[:8]}",
                    "source": "jpcert",
                    "title": e.get("title","").strip(),
                    "url": e.get("link","").strip(),
                    "score": None, "author": "JPCERT/CC",
                    "tags": ["JPCERT", label, "セキュリティ"],
                    "severity": sev,
                    "date": e.get("published", now()),
                })
        except Exception as ex:
            print(f"  [WARN] {feed_url}: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_devto():
    print("[dev.to] Fetching...")
    r = safe_get("https://dev.to/api/articles",
                 params={"per_page": MAX_PER, "tag": "security,devops,programming,pentest"})
    if not r: return []
    result = []
    for a in r.json():
        if is_blocked(a.get("url","")): continue
        result.append({
            "id": f"devto-{a['id']}", "source": "devto",
            "title": a.get("title",""), "url": a.get("url",""),
            "score": a.get("positive_reactions_count"),
            "comments": a.get("comments_count",0),
            "author": a.get("user",{}).get("name",""),
            "tags": a.get("tag_list",[])[:3],
            "date": a.get("published_at", now()),
        })
    print(f"  → {len(result)}")
    return result

# ════════════════════════════════════════════════════════════
#  プロジェクト専用ソース
# ════════════════════════════════════════════════════════════

def fetch_anthropic():
    """Tech blog RSS"""
    print("[Anthropic] Fetching...")
    items = []
    try:
        feed = feedparser.parse("https://www.anthropic.com/rss.xml")
        for e in feed.entries[:8]:
            url = e.get("link","")
            if is_blocked(url): continue
            items.append({
                "id": f"techblog-{hashlib.md5(url.encode()).hexdigest()[:10]}",
                "source": "project", "proj_category": "Tech",
                "title": e.get("title",""), "url": url,
                "score": None, "author": "Tech Blog",
                "tags": ["Tech", "AI"],
                "date": e.get("published", now()),
            })
    except Exception as ex:
        print(f"  [WARN] Anthropic: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_hetzner_status():
    """Infrastructure status RSS"""
    print("[Infra] Fetching...")
    items = []
    try:
        feed = feedparser.parse("https://status.hetzner.com/history.rss")
        for e in feed.entries[:5]:
            items.append({
                "id": f"infra-{hashlib.md5(e.get('id','').encode()).hexdigest()[:8]}",
                "source": "project", "proj_category": "Infra",
                "title": e.get("title",""),
                "url": e.get("link","https://status.hetzner.com"),
                "score": None, "author": "Infra Status",
                "tags": ["Infra", "VPS"],
                "date": e.get("published", now()),
            })
    except Exception as ex:
        print(f"  [WARN] Hetzner: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_tool_releases():
    """Tool release monitoring"""
    print("[Tool Releases] Fetching...")
    TOOLS = [
        ("fortra/impacket",             "Impacket",     ["Impacket","AD","Windows"]),
        ("projectdiscovery/nuclei",      "Nuclei",       ["Nuclei","Scanner"]),
        ("BloodHoundAD/BloodHound",      "BloodHound",   ["BloodHound","AD"]),
        ("chroma-core/chroma",           "ChromaDB",     ["ChromaDB","Database"]),
        ("pwndbg/pwndbg",                "pwndbg",       ["pwndbg","GDB","Pwn"]),
        ("RustScan/RustScan",            "RustScan",     ["RustScan","Scanner"]),
        ("Pennyw0rth/NetExec",           "NetExec",      ["NetExec","CrackMapExec","AD"]),
        ("anthonybudd/impacket",         "impacket-fork",["Impacket"]),
    ]
    items = []
    for repo, label, tags in TOOLS:
        r = safe_get(f"https://api.github.com/repos/{repo}/releases",
                     headers=GH_HEADERS, params={"per_page": 2})
        if not r: continue
        try:
            releases = r.json()
            if not isinstance(releases, list): continue
            for rel in releases[:1]:  # 最新1件
                items.append({
                    "id": f"ghrel-{repo.replace('/','_')}-{rel['id']}",
                    "source": "project", "proj_category": "Tools",
                    "title": f"[{label}] {rel['tag_name']} — {rel.get('name','') or '新リリース'}",
                    "url": rel["html_url"],
                    "score": None, "author": label,
                    "tags": tags + ["Release"],
                    "date": rel.get("published_at", now()),
                })
        except: pass
        time.sleep(0.2)
    print(f"  → {len(items)}")
    return items

def fetch_htb():
    """CTF platform RSS"""
    print("[HTB] Fetching...")
    items = []
    try:
        # HTB公式RSSが不安定な場合はdev.toのhtbタグで補完
        r = safe_get("https://dev.to/api/articles?tag=hackthebox&per_page=10")
        if r:
            for a in r.json():
                items.append({
                    "id": f"htb-dt-{a['id']}", "source": "project",
                    "proj_category": "CTF",
                    "title": a.get("title",""), "url": a.get("url",""),
                    "score": a.get("positive_reactions_count"),
                    "author": a.get("user",{}).get("name",""),
                    "tags": ["CTF","Security"],
                    "date": a.get("published_at", now()),
                })
    except Exception as ex:
        print(f"  [WARN] HTB: {ex}")
    print(f"  → {len(items)}")
    return items

# ════════════════════════════════════════════════════════════
#  MITRE ATT&CK / MSF / CVE
# ════════════════════════════════════════════════════════════

def fetch_exploit_db():
    """Exploit database RSS"""
    print("[Exploit-DB] Fetching...")
    items = []
    try:
        feed = feedparser.parse("https://www.exploit-db.com/rss.xml")
        for e in feed.entries[:15]:
            items.append({
                "id": f"edb-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
                "source": "msf",
                "title": e.get("title",""), "url": e.get("link",""),
                "score": None, "author": "Exploit-DB",
                "tags": ["Exploit-DB","CVE","PoC"],
                "severity": "high",
                "date": e.get("published", now()),
            })
    except Exception as ex:
        print(f"  [WARN] Exploit-DB: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_nvd():
    """NVD latest CVEs"""
    print("[NVD] Fetching...")
    items = []
    try:
        r = safe_get(
            "https://services.nvd.nist.gov/rest/json/cves/2.0",
            params={"resultsPerPage": 20, "sortBy": "published"}
        )
        if not r: return []
        for v in r.json().get("vulnerabilities",[]):
            cve = v.get("cve",{})
            cid = cve.get("id","")
            cvss = (cve.get("metrics",{}).get("cvssMetricV31",[{}])[0]
                    .get("cvssData",{}).get("baseScore", 0))
            if cvss < 5.0: continue  # 低スコアは除外
            sev = ("critical" if cvss>=9 else "high" if cvss>=7
                   else "medium" if cvss>=4 else "low")
            desc = next((d["value"] for d in cve.get("descriptions",[]) if d["lang"]=="en"), "")
            items.append({
                "id": f"nvd-{cid}",
                "source": "msf",
                "title": f"[{cid}] CVSS {cvss:.1f} — {desc[:120]}",
                "url": f"https://nvd.nist.gov/vuln/detail/{cid}",
                "score": cvss, "author": "NVD/NIST",
                "tags": [cid, f"CVSS:{cvss:.1f}", sev.upper()],
                "severity": sev,
                "date": cve.get("published", now()),
            })
    except Exception as ex:
        print(f"  [WARN] NVD: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_mitre_blog():
    """Framework updates"""
    print("[MITRE] Fetching...")
    items = []
    # ATT&CK GitHub Releases（フレームワーク更新）
    r = safe_get("https://api.github.com/repos/mitre-attack/attack-stix-data/releases",
                 headers=GH_HEADERS, params={"per_page": 3})
    if r:
        try:
            for rel in r.json()[:3]:
                items.append({
                    "id": f"mitre-rel-{rel['id']}", "source": "mitre",
                    "title": f"[ATT&CK] {rel['tag_name']} — {rel.get('name','フレームワーク更新')}",
                    "url": rel["html_url"],
                    "score": None, "author": "MITRE ATT&CK",
                    "tags": ["ATT&CK","MITRE","TTP","Framework"],
                    "date": rel.get("published_at", now()),
                })
        except: pass
    print(f"  → {len(items)}")
    return items

# ════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════
def main():
    print(f"\n{'='*55}")
    print(f"  SE News v3 Fetch @ {now()}")
    print(f"{'='*55}\n")

    existing = load_existing()
    existing_ids = {i["id"] for i in existing.get("items",[])}

    fetchers = [
        fetch_hn, fetch_github_trending,
        fetch_zenn, fetch_qiita, fetch_jpcert, fetch_devto,
        fetch_anthropic, fetch_hetzner_status, fetch_tool_releases, fetch_htb,
        fetch_exploit_db, fetch_nvd, fetch_mitre_blog,
    ]

    new_items = []
    for fn in fetchers:
        try:
            new_items.extend(fn())
        except Exception as e:
            print(f"  [ERROR] {fn.__name__}: {e}")

    # 重複除去 & severity付与
    seen = set()
    merged = []
    for item in new_items:
        if item["id"] in seen: continue
        seen.add(item["id"])
        if "severity" not in item:
            sev = classify_sev(item.get("title",""), item.get("tags",[]), item.get("source",""))
            if sev: item["severity"] = sev
        merged.append(item)

    # 既存を保持（最大400件）
    for item in existing.get("items",[]):
        if item["id"] not in seen and len(merged) < 400:
            seen.add(item["id"])
            merged.append(item)

    def parse_dt(i):
        try: return datetime.fromisoformat(str(i["date"]).replace("Z","+00:00"))
        except: return datetime.min.replace(tzinfo=timezone.utc)

    merged.sort(key=parse_dt, reverse=True)

    output = {"updated_at": now(), "count": len(merged), "items": merged}
    DATA_PATH.parent.mkdir(exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n{'='*55}")
    print(f"  Done: {len(merged)} items → {DATA_PATH}")
    print(f"{'='*55}\n")

if __name__ == "__main__":
    main()
