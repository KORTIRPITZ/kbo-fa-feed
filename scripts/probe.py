"""디시 수집 점검용(임시)."""
import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import collect
cfg = json.load(open(os.path.join(collect.ROOT, "config.json"), encoding="utf-8"))
for g in cfg["dcinside"]:
    for kw in g["keywords"]:
        rows = list(collect.dcinside(g["id"], kw, g["name"]))
        print(g["id"], kw, len(rows))
        for r in rows[:6]:
            print("  ", r["published"], "|", r["title"][:50], "|", r["url"][-60:], "| relevant:", collect.relevant(r, cfg["players"], cfg["must_words"]))
