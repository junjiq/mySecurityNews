#!/usr/bin/env python3
"""SE News Fetcher v4 - サーバーサイドのみで完結"""

import json, time, hashlib, os
import requests, feedparser
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

DATA_PATH = Path("data/news.json")
MAX_PER   = 25
TIMEOUT   = 15

BLOCKED = {
    'medium.com','wsj.com','nytimes.com','ft.com',
    'bloomberg.com','forbes.com','wired.com',
    'technologyreview.com','businessinsider.com',
    'theatlantic.com','economist.com','hbr.org','fastcompany.com',
}

def is_blocked(url):
    try:
        d = urlparse(url).hostname or ''
        return any(b in d for b in BLOCKED)
    except: return False

HEADERS = {"User-Agent": "SE-News-Bot/4.0"}
GH_TOKEN = os.environ.get('GITHUB_TOKEN','')
GH_HEADERS = {**HEADERS, **({"Authorization": f"token {GH_TOKEN}"} if GH_TOKEN else {})}

def now(): return datetime.now(timezone.utc).isoformat()

def safe_get(url, headers=None, params=None, retries=2):
    for i in range(retries+1):
        try:
            r = requests.get(url, headers=headers or HEADERS,
                             params=params, timeout=TIMEOUT)
            r.raise_for_status()
            return r
        except Exception as e:
            if i == retries: print(f"  [WARN] {url[:60]}: {e}")
            else: time.sleep(1)
    return None

def load_existing():
    if DATA_PATH.exists():
        try: return json.loads(DATA_PATH.read_text(encoding='utf-8'))
        except: pass
    return {"items":[], "updated_at":""}

SEV_KW = {
    'critical': ['rce','remote code execution','critical','zero-day','0day','ransomware','緊急'],
    'high':     ['exploit','vulnerability','cve','privilege escalation','bypass','脆弱性'],
    'medium':   ['patch','update','advisory','warning','threat','malware','phishing'],
}
def classify_sev(title, tags, source):
    if source == 'jpcert':
        t = title.lower()
        if any(k in t for k in SEV_KW['critical']): return 'critical'
        return 'high' if 'アラート' in ' '.join(tags) or '脆弱' in title else 'info'
    t = (title+' '+' '.join(tags)).lower()
    for sev, kws in SEV_KW.items():
        if any(k in t for k in kws): return sev
    return None

# ── Fetchers ────────────────────────────────────────────────
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
            "id":f"hn-{d['id']}", "source":"hn",
            "title":d.get('title',''), "url":d['url'],
            "score":d.get('score'), "comments":d.get('descendants',0),
            "author":d.get('by',''), "tags":[],
            "date":datetime.fromtimestamp(d['time'],tz=timezone.utc).isoformat(),
        })
        time.sleep(0.04)
    print(f"  → {len(items)}")
    return items

def fetch_github():
    print("[GitHub] Fetching...")
    items = []
    r = safe_get("https://gh-trending-api.herokuapp.com/repositories?since=daily")
    if r:
        try:
            for repo in r.json()[:MAX_PER]:
                items.append({
                    "id":f"gh-{repo.get('author','')}-{repo.get('name','')}",
                    "source":"github",
                    "title":f"{repo.get('author','')}/{repo.get('name','')} — {repo.get('description') or ''}",
                    "url":repo.get("url",""),
                    "score":None, "stars":str(repo.get("stars","")),
                    "author":repo.get("author",""),
                    "tags":[repo["language"]] if repo.get("language") else [],
                    "date":now(),
                })
        except: pass
    if not items:
        feed = feedparser.parse("https://github.com/trending.atom")
        for e in feed.entries[:MAX_PER]:
            items.append({
                "id":f"gh-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
                "source":"github", "title":e.get("title",""),
                "url":e.get("link",""), "score":None, "author":e.get("author",""),
                "tags":[], "date":now(),
            })
    print(f"  → {len(items)}")
    return items

def fetch_zenn():
    print("[Zenn] Fetching...")
    feed = feedparser.parse("https://zenn.dev/feed")
    result = []
    for e in feed.entries[:MAX_PER]:
        url = e.get("link","")
        if is_blocked(url): continue
        result.append({
            "id":f"zenn-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
            "source":"zennqiita", "sub_source":"Zenn",
            "title":e.get("title",""), "url":url,
            "score":None, "author":e.get("author","Zenn"),
            "tags":["Zenn"], "date":e.get("published",now()),
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
            "id":f"qiita-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
            "source":"zennqiita", "sub_source":"Qiita",
            "title":e.get("title",""), "url":url,
            "score":None, "author":e.get("author","Qiita"),
            "tags":["Qiita"], "date":e.get("updated",now()),
        })
    print(f"  → {len(result)}")
    return result

def fetch_jpcert():
    print("[JPCERT] Fetching...")
    items = []
    for feed_url, label, sev in [
        ("https://www.jpcert.or.jp/feed/news.rdf",    "ニュース", "info"),
        ("https://www.jpcert.or.jp/feed/alerts.rdf",  "アラート","high"),
        ("https://www.jpcert.or.jp/feed/vulnotes.rdf","脆弱性",  "medium"),
    ]:
        try:
            feed = feedparser.parse(feed_url)
            for e in feed.entries[:10]:
                items.append({
                    "id":f"jpcert-{label[0]}-{hashlib.md5(e.get('id','').encode()).hexdigest()[:8]}",
                    "source":"jpcert",
                    "title":e.get("title","").strip(), "url":e.get("link","").strip(),
                    "score":None, "author":"JPCERT/CC",
                    "tags":["JPCERT",label,"セキュリティ"],
                    "severity":sev, "date":e.get("published",now()),
                })
        except Exception as ex: print(f"  [WARN] {feed_url}: {ex}")
    print(f"  → {len(items)}")
    return items

def fetch_devto():
    print("[dev.to] Fetching...")
    r = safe_get("https://dev.to/api/articles",
                 params={"per_page":MAX_PER,"tag":"security,devops,programming,pentest"})
    if not r: return []
    result = []
    for a in r.json():
        if is_blocked(a.get("url","")): continue
        result.append({
            "id":f"devto-{a['id']}", "source":"devto",
            "title":a.get("title",""), "url":a.get("url",""),
            "score":a.get("positive_reactions_count"),
            "comments":a.get("comments_count",0),
            "author":a.get("user",{}).get("name",""),
            "tags":a.get("tag_list",[])[:3],
            "date":a.get("published_at",now()),
        })
    print(f"  → {len(result)}")
    return result

def fetch_tech_sources():
    print("[Tech Sources] Fetching...")
    items = []
    sources = [
        ("https://www.anthropic.com/rss.xml", "Tech Blog", ["Tech","AI"]),
        ("https://status.hetzner.com/history.rss", "Infra Status", ["Infra","VPS"]),
    ]
    for url, author, tags in sources:
        try:
            feed = feedparser.parse(url)
            for e in feed.entries[:8]:
                link = e.get("link","")
                if is_blocked(link): continue
                items.append({
                    "id":f"tech-{hashlib.md5(link.encode()).hexdigest()[:10]}",
                    "source":"project", "proj_category":"Tech",
                    "title":e.get("title",""), "url":link,
                    "score":None, "author":author, "tags":tags,
                    "date":e.get("published",now()),
                })
        except: pass

    # Tool releases
    tools = [
        ("fortra/impacket","Impacket"),
        ("projectdiscovery/nuclei","Nuclei"),
        ("BloodHoundAD/BloodHound","BloodHound"),
        ("chroma-core/chroma","ChromaDB"),
        ("Pennyw0rth/NetExec","NetExec"),
    ]
    for repo, label in tools:
        r = safe_get(f"https://api.github.com/repos/{repo}/releases",
                     headers=GH_HEADERS, params={"per_page":2})
        if not r: continue
        try:
            for rel in r.json()[:1]:
                items.append({
                    "id":f"ghrel-{repo.replace('/','_')}-{rel['id']}",
                    "source":"project", "proj_category":"Tools",
                    "title":f"{label} {rel['tag_name']} — {rel.get('name','') or '新リリース'}",
                    "url":rel["html_url"],
                    "score":None, "author":label,
                    "tags":[label,"Release"],
                    "date":rel.get("published_at",now()),
                })
        except: pass
        time.sleep(0.2)

    # CTF
    r = safe_get("https://dev.to/api/articles?tag=hackthebox&per_page=10")
    if r:
        for a in r.json():
            items.append({
                "id":f"ctf-{a['id']}", "source":"project", "proj_category":"CTF",
                "title":a.get("title",""), "url":a.get("url",""),
                "score":a.get("positive_reactions_count"),
                "author":"CTF Platform", "tags":["CTF","Security"],
                "date":a.get("published_at",now()),
            })

    print(f"  → {len(items)}")
    return items

def fetch_security_sources():
    print("[Security] Fetching...")
    items = []
    # Exploit-DB
    try:
        feed = feedparser.parse("https://www.exploit-db.com/rss.xml")
        for e in feed.entries[:15]:
            items.append({
                "id":f"edb-{hashlib.md5(e.get('id','').encode()).hexdigest()[:10]}",
                "source":"msf", "title":e.get("title",""), "url":e.get("link",""),
                "score":None, "author":"Exploit-DB",
                "tags":["Exploit-DB","CVE","PoC"],
                "severity":"high", "date":e.get("published",now()),
            })
    except: pass
    # NVD
    try:
        r = safe_get("https://services.nvd.nist.gov/rest/json/cves/2.0",
                     params={"resultsPerPage":20,"sortBy":"published"})
        if r:
            for v in r.json().get("vulnerabilities",[]):
                cve = v.get("cve",{})
                cid = cve.get("id","")
                cvss = (cve.get("metrics",{}).get("cvssMetricV31",[{}])[0]
                        .get("cvssData",{}).get("baseScore",0))
                if cvss < 5.0: continue
                sev = "critical" if cvss>=9 else "high" if cvss>=7 else "medium"
                desc = next((d["value"] for d in cve.get("descriptions",[]) if d["lang"]=="en"),"")
                items.append({
                    "id":f"nvd-{cid}", "source":"msf",
                    "title":f"{cid} CVSS {cvss:.1f} — {desc[:100]}",
                    "url":f"https://nvd.nist.gov/vuln/detail/{cid}",
                    "score":cvss, "author":"NVD/NIST",
                    "tags":[cid,f"CVSS:{cvss:.1f}"],
                    "severity":sev, "date":cve.get("published",now()),
                })
    except: pass
    print(f"  → {len(items)}")
    return items

# ── Main ────────────────────────────────────────────────────
def main():
    print(f"\n=== Fetch @ {now()} ===\n")
    existing = load_existing()
    existing_ids = {i["id"] for i in existing.get("items",[])}

    fetchers = [fetch_hn, fetch_github, fetch_zenn, fetch_qiita,
                fetch_jpcert, fetch_devto, fetch_tech_sources, fetch_security_sources]
    new_items = []
    for fn in fetchers:
        try: new_items.extend(fn())
        except Exception as e: print(f"  [ERROR] {fn.__name__}: {e}")

    seen = set()
    merged = []
    for item in new_items:
        if item["id"] in seen: continue
        seen.add(item["id"])
        if "severity" not in item:
            sev = classify_sev(item.get("title",""), item.get("tags",[]), item.get("source",""))
            if sev: item["severity"] = sev
        merged.append(item)

    for item in existing.get("items",[]):
        if item["id"] not in seen and len(merged) < 500:
            seen.add(item["id"])
            merged.append(item)

    def parse_dt(i):
        try: return datetime.fromisoformat(str(i["date"]).replace("Z","+00:00"))
        except: return datetime.min.replace(tzinfo=timezone.utc)

    merged.sort(key=parse_dt, reverse=True)

    output = {"updated_at":now(), "count":len(merged), "items":merged}
    DATA_PATH.parent.mkdir(exist_ok=True)
    DATA_PATH.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n=== Done: {len(merged)} items ===\n")

if __name__ == "__main__":
    main()
