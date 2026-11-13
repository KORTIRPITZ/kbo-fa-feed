#!/usr/bin/env python3
"""KBO FA 소식 수집기.

GitHub Actions에서 5분마다 실행된다.
- 구글 뉴스 RSS (키 필요 없음)
- 네이버 검색 API: 뉴스·카페·블로그 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET 시크릿이 있을 때만)
결과는 docs/data/news.json 에 쌓이고, docs/index.html 이 그것을 보여 준다.
표준 라이브러리만 쓴다(설치할 패키지 없음).
"""
import email.utils
import html
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG = os.path.join(ROOT, "config.json")
OUT = os.path.join(ROOT, "docs", "data", "news.json")
KST = timezone(timedelta(hours=9))
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/130.0 Safari/537.36")
TIMEOUT = 20


def load_config():
    with open(CONFIG, encoding="utf-8") as f:
        return json.load(f)


def get(url, headers=None, tries=2):
    h = {"User-Agent": UA, "Accept-Language": "ko-KR,ko;q=0.9", **(headers or {})}
    for n in range(tries):
        try:
            req = urllib.request.Request(url, headers=h)
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.read()
        except Exception:
            if n == tries - 1:
                raise
            time.sleep(3)


def clean(text):
    text = html.unescape(re.sub(r"<[^>]+>", "", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def to_iso(dt):
    return dt.astimezone(KST).isoformat(timespec="minutes") if dt else None


def parse_rfc822(s):
    try:
        return email.utils.parsedate_to_datetime(s)
    except (TypeError, ValueError):
        return None


# ---------------- 수집원 ----------------

def google_news(query):
    url = "https://news.google.com/rss/search?" + urllib.parse.urlencode(
        {"q": query + " when:7d", "hl": "ko", "gl": "KR", "ceid": "KR:ko"})
    root = ET.fromstring(get(url))
    for it in root.iter("item"):
        title = clean(it.findtext("title"))
        src_el = it.find("source")
        source = clean(src_el.text) if src_el is not None else ""
        # 구글 뉴스 제목은 "제목 - 매체" 형태
        if source and title.endswith(" - " + source):
            title = title[: -len(source) - 3]
        yield {
            "title": title,
            "url": it.findtext("link") or "",
            "source": source or "구글 뉴스",
            "kind": "기사",
            "published": to_iso(parse_rfc822(it.findtext("pubDate"))),
            "summary": "",
            "via": "google_news",
        }


def bing_news(query):
    url = "https://www.bing.com/news/search?" + urllib.parse.urlencode(
        {"q": query, "format": "rss", "setlang": "ko-KR", "cc": "KR", "qft": 'sortbydate="1"'})
    root = ET.fromstring(get(url))
    for it in root.iter("item"):
        link = it.findtext("link") or ""
        real = urllib.parse.parse_qs(urllib.parse.urlparse(link).query).get("url", [link])[0]
        src = ""
        for child in it:
            if child.tag.lower().endswith("source"):
                src = clean(child.text)
        yield {
            "title": clean(it.findtext("title")),
            "url": real,
            "source": src or urllib.parse.urlparse(real).netloc.replace("www.", ""),
            "kind": "기사",
            "published": to_iso(parse_rfc822(it.findtext("pubDate"))),
            "summary": clean(it.findtext("description"))[:140],
            "via": "bing_news",
        }


DC_ROW = re.compile(r'<tr[^>]*class="ub-content[^"]*"[^>]*>(.*?)</tr>', re.S)
DC_LINK = re.compile(r'<td class="gall_tit[^"]*"[^>]*>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', re.S)
DC_DATE = re.compile(r'<td class="gall_date"[^>]*title="([0-9: -]+)"')


def dcinside(gallery, keyword, gallery_name, minor=False):
    """디시인사이드 갤러리 제목 검색 결과 1쪽(제목·링크·시각만)."""
    base = "https://gall.dcinside.com/" + ("mgallery/" if minor else "")
    url = base + "board/lists/?" + urllib.parse.urlencode(
        {"id": gallery, "s_type": "search_subject", "s_keyword": keyword})
    page = get(url).decode("utf-8", "replace")
    for row in DC_ROW.findall(page):
        if 'data-type="icon_notice"' in row or "icon_ad" in row:
            continue
        m = DC_LINK.search(row)
        if not m:
            continue
        href, title = m.group(1), clean(m.group(2))
        if "id=" + gallery not in href or not title:
            continue
        link = urllib.parse.urljoin("https://gall.dcinside.com/", html.unescape(href))
        link = re.sub(r"&page=\d+|&s_type=[^&]*|&s_keyword=[^&]*", "", link)
        d = DC_DATE.search(row)
        pub = None
        if d:
            try:
                pub = to_iso(datetime.strptime(d.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=KST))
            except ValueError:
                pass
        yield {"title": title, "url": link, "source": "디시 " + gallery_name, "kind": "커뮤니티",
               "published": pub, "summary": "", "via": "dcinside"}


def naver(kind_path, query, cid, secret):
    url = f"https://openapi.naver.com/v1/search/{kind_path}.json?" + urllib.parse.urlencode(
        {"query": query, "display": 30, "sort": "date"})
    data = json.loads(get(url, {"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": secret}))
    for it in data.get("items", []):
        if kind_path == "news":
            pub = to_iso(parse_rfc822(it.get("pubDate")))
            link = it.get("originallink") or it.get("link")
            src = urllib.parse.urlparse(link).netloc.replace("www.", "")
            kind = "기사"
        elif kind_path == "blog":
            d = it.get("postdate") or ""
            pub = f"{d[:4]}-{d[4:6]}-{d[6:8]}T00:00+09:00" if len(d) == 8 else None
            link, src, kind = it.get("link"), it.get("bloggername") or "네이버 블로그", "블로그"
        else:  # cafearticle
            pub, link, src, kind = None, it.get("link"), it.get("cafename") or "네이버 카페", "커뮤니티"
        yield {
            "title": clean(it.get("title")),
            "url": link or "",
            "source": src,
            "kind": kind,
            "published": pub,
            "summary": clean(it.get("description"))[:140],
            "via": "naver_" + kind_path,
        }


# ---------------- 정리 ----------------

def tag(item, players, teams):
    text = item["title"] + " " + item.get("summary", "")
    item["players"] = [p["name"] for p in players if p["name"] in text]
    item["teams"] = sorted({p["team"] for p in players if p["name"] in item["players"]}
                           | {t for t in teams if t in text})
    return item


COMM_WORDS = ["fa", "에이전트", "해외", "메이저", "미국", "mlb", "npb", "포스팅", "계약", "잔류", "이적",
              "몸값", "억", "다년", "협상", "보상", "영입", "오퍼", "관심"]


def relevant(item, players, must_words):
    text = item["title"] + " " + item.get("summary", "")
    if item.get("kind") == "커뮤니티":
        low = text.lower()
        return any(p["name"] in text for p in players) and any(w in low for w in COMM_WORDS)
    has_player = any(p["name"] in text for p in players)
    has_word = any(w in text for w in must_words)
    return has_player and has_word or ("FA" in text and ("KBO" in text or "프로야구" in text))


def main():
    cfg = load_config()
    players, teams = cfg["players"], cfg["teams"]
    must = cfg["must_words"]
    cid, secret = os.environ.get("NAVER_CLIENT_ID"), os.environ.get("NAVER_CLIENT_SECRET")

    queries = list(cfg["market_queries"]) + [f'"{p["name"]}" FA' for p in players]
    found, errors = [], []
    for q in queries:
        for name, fn in (("google", google_news), ("bing", bing_news)):
            try:
                found.extend(fn(q))
            except Exception as e:  # 한 검색이 실패해도 나머지는 계속
                errors.append(f"{name} {q}: {e}")
            time.sleep(1)
        if cid and secret:
            for path in ("news", "cafearticle", "blog"):
                try:
                    found.extend(naver(path, q, cid, secret))
                except Exception as e:
                    errors.append(f"naver {path} {q}: {e}")

    for g in cfg.get("dcinside", []):
        for kw in g["keywords"]:
            try:
                found.extend(dcinside(g["id"], kw, g["name"], g.get("minor", False)))
            except Exception as e:
                errors.append(f"dcinside {g['id']} {kw}: {e}")
            time.sleep(2)

    try:
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        old = {"items": []}

    now = datetime.now(KST)
    by_url = {it["url"]: it for it in old.get("items", []) if it.get("url")}
    added = 0
    for it in found:
        if not it["url"] or not it["title"] or not relevant(it, players, must):
            continue
        if it["url"] in by_url:
            continue
        it["collected"] = to_iso(now)
        by_url[it["url"]] = tag(it, players, teams)
        added += 1

    # 같은 제목(매체만 다른 중복)은 하나만 남김
    items, seen_titles = [], set()
    def sort_key(x):
        return x.get("published") or x.get("collected") or ""
    for it in sorted(by_url.values(), key=sort_key, reverse=True):
        key = re.sub(r"\W", "", it["title"])[:40]
        if key in seen_titles:
            continue
        seen_titles.add(key)
        items.append(it)
    items = items[: cfg.get("max_items", 800)]

    status = {"checked": to_iso(now), "added": added, "found": len(found), "errors": len(errors),
              "sample_errors": errors[:5]}
    with open(os.path.join(ROOT, "docs", "data", "status.json"), "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=1)
    if added == 0 and old.get("items"):
        # 새 글이 없으면 파일을 건드리지 않음 → 커밋도 생기지 않음
        print(f"no new items (errors {len(errors)})")
        if errors:
            print("\n".join(errors[:10]), file=sys.stderr)
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump({"updated": to_iso(now), "count": len(items), "added": added,
                   "naver": bool(cid and secret), "errors": errors[:20], "items": items},
                  f, ensure_ascii=False, indent=1)
    print(f"added {added}, total {len(items)}, errors {len(errors)}")
    if errors:
        print("\n".join(errors[:10]), file=sys.stderr)


if __name__ == "__main__":
    main()
