"""MLB파크 검색엔진 경유 수집 실험(임시)."""
import os, sys, urllib.parse, urllib.robotparser, xml.etree.ElementTree as ET
sys.path.insert(0, os.path.dirname(__file__))
import collect
for base, paths in [("https://www.bing.com", ["/search?q=x&format=rss", "/news/search?q=x&format=rss"]),
                    ("https://news.google.com", ["/rss/search?q=x"]),
                    ("https://duckduckgo.com", ["/html/?q=x"])]:
    try:
        rp = urllib.robotparser.RobotFileParser(); rp.parse(collect.get(base + "/robots.txt").decode("utf-8", "replace").splitlines())
        for p in paths: print("robots", base + p, "->", rp.can_fetch("*", base + p))
    except Exception as e: print("robots err", base, e)
qs = ["site:mlbpark.donga.com 원태인 FA", "site:mlbpark.donga.com 구자욱 FA", "site:mlbpark.donga.com FA 계약", "site:mlbpark.donga.com 불펜 FA"]
for q in qs:
    url = "https://www.bing.com/search?" + urllib.parse.urlencode({"q": q, "format": "rss", "setlang": "ko-KR", "cc": "KR"})
    try:
        root = ET.fromstring(collect.get(url))
        items = list(root.iter("item"))
        print(q, "->", len(items))
        for it in items[:6]:
            print("   ", (it.findtext("pubDate") or "")[:16], "|", (it.findtext("title") or "")[:50], "|", (it.findtext("link") or "")[-55:])
    except Exception as e:
        print(q, "error", e)
