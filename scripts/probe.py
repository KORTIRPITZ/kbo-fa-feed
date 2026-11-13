"""커뮤니티 수집 가능 여부 점검용(임시)."""
import urllib.request, urllib.robotparser, urllib.parse, re
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
SITES = {
  "mlbpark": ("https://mlbpark.donga.com", "/mp/b.php?" + urllib.parse.urlencode({"b": "bullpen", "select": "sj", "query": "FA"})),
  "ruliweb": ("https://bbs.ruliweb.com", "/sports/board/300009?" + urllib.parse.urlencode({"search_type": "subject", "search_key": "FA"})),
  "dcinside": ("https://gall.dcinside.com", "/board/lists/?" + urllib.parse.urlencode({"id": "baseball_new11", "s_type": "search_subject", "s_keyword": "FA"})),
  "fmkorea": ("https://www.fmkorea.com", "/index.php?mid=baseball&search_target=title&search_keyword=FA"),
}
def get(u):
    r = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=20)
    return r.status, r.read().decode("utf-8", "replace")
for name, (base, path) in SITES.items():
    print("=" * 20, name)
    try:
        st, robots = get(base + "/robots.txt")
        print("robots status", st); print(robots[:600])
        rp = urllib.robotparser.RobotFileParser(); rp.parse(robots.splitlines())
        print("can_fetch generic:", rp.can_fetch("*", base + path))
    except Exception as e:
        print("robots error", e)
    try:
        st, html = get(base + path)
        print("page status", st, "len", len(html))
        links = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{4,80})</a>', html)
        for h, t in [l for l in links if "FA" in l[1]][:8]:
            print("  ", t.strip(), "|", h[:120])
        i = html.find("FA"); print("snippet:", re.sub(r"\s+", " ", html[max(0, i-600):i+300]))
    except Exception as e:
        print("page error", e)
