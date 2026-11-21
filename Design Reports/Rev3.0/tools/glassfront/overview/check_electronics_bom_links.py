"""Best-effort link check for electronics_bom.json -> electronics_bom_linkcheck.json (same folder).

One plain GET per distinct URL with a generic browser User-Agent, no cookies, no other headers that identify
anyone, at least 1.2 s between requests, the whole run capped at about 9 minutes. Nothing is parsed except a
check that the bought part number appears somewhere on the returned page (to catch "soft 404" pages that answer
200); prices are not read. 403/429 (and 503 from a bot wall) count as "blocked", not as dead links.

Run:  python check_electronics_bom_links.py
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
BOM = os.path.join(HERE, "electronics_bom.json")
OUT = os.path.join(HERE, "electronics_bom_linkcheck.json")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
GAP_S, TIMEOUT_S, BUDGET_S = 1.2, 25, 540
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def norm(s):
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


bom = json.load(open(BOM, encoding="utf-8"))
lines = [ln for g in bom["groups"] for ln in g["lines"]] + bom["not_in_component_total"]
by_url = {}
for ln in lines:
    if ln.get("url"):
        by_url.setdefault(ln["url"], []).append(ln)

opener = urllib.request.build_opener()          # no cookie processor: cookies are neither stored nor sent
results = {}
t0 = time.time()
for i, url in enumerate(by_url):
    if time.time() - t0 > BUDGET_S:
        results[url] = {"result": "not checked (time box)", "http_status": None}
        continue
    if i:
        time.sleep(GAP_S)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,application/xhtml+xml",
                                               "Accept-Language": "en"})
    rec = {"http_status": None, "final_url": None, "result": None, "mpn_on_page": None, "page_title": None, "detail": ""}
    try:
        with opener.open(req, timeout=TIMEOUT_S) as r:
            rec["http_status"] = r.status
            rec["final_url"] = r.geturl()
            body = r.read(3_000_000).decode("utf-8", "replace")
        # Özdisan answers 200 with an empty shell for unknown product ids, so the part number is looked for in the
        # page's <title> and <h1> only (the URL itself is echoed elsewhere in the HTML and would always match).
        t = re.search(r"<title[^>]*>(.*?)</title>", body, re.S | re.I)
        h = re.search(r"<h1[^>]*>(.*?)</h1>", body, re.S | re.I)
        head_txt = " ".join(re.sub(r"<[^>]+>", " ", m.group(1)) for m in (t, h) if m)
        rec["page_title"] = re.sub(r"\s+", " ", t.group(1)).strip()[:120] if t else None
        page = norm(head_txt)
        mpns = [norm(ln.get("mpn")) for ln in by_url[url] if ln.get("mpn")]
        if mpns:
            # a search link only has to show the base part number it searches for
            q = re.search(r"[?&](?:search|s)=([^&]+)", url)
            keys = [norm(q.group(1))] if q else mpns
            rec["mpn_on_page"] = any(k and k in page for k in keys)
        moved_off = ("/p/" in url and rec["final_url"] and "/p/" not in rec["final_url"])
        if moved_off:
            rec["result"], rec["detail"] = "dead", "product link redirects away from the product page"
        elif rec["mpn_on_page"] is False:
            rec["result"], rec["detail"] = "suspect", "HTTP 200 but the page title / heading does not name the part (possible empty page)"
        else:
            rec["result"] = "ok"
    except urllib.error.HTTPError as e:
        rec["http_status"] = e.code
        rec["final_url"] = e.geturl() if hasattr(e, "geturl") else None
        if e.code in (401, 403, 429) or (e.code == 503 and "cloudflare" in str(e.headers.get("Server", "")).lower()):
            rec["result"] = "blocked"
        elif e.code in (404, 410):
            rec["result"] = "dead"
        else:
            rec["result"] = "error"
        rec["detail"] = "HTTP %d %s" % (e.code, e.reason)
    except Exception as e:                                   # timeouts, DNS, TLS
        rec["result"], rec["detail"] = "error", "%s: %s" % (type(e).__name__, e)
    results[url] = rec
    print("%3d %-8s %s %s" % (i + 1, rec["http_status"], rec["result"], url))

tally = {}
for rec in results.values():
    tally[rec["result"]] = tally.get(rec["result"], 0) + 1
out = {
    "checked": datetime.datetime.now().isoformat(timespec="seconds"),
    "method": "one GET per distinct URL, generic browser User-Agent, no cookies, >= %.1f s apart, %d s timeout; "
              "403/429 = blocked (bot wall, not a dead link); 404/410 or a product link that redirects off the "
              "product page = dead; 'mpn_on_page' = the bought part number appears in the page's <title> or <h1> "
              "(Özdisan answers 200 with an empty page for unknown product ids, so status 200 alone proves nothing); "
              "200 without the part number = suspect" % (GAP_S, TIMEOUT_S),
    "user_agent": UA,
    "distinct_urls": len(by_url),
    "tally": tally,
    "urls": [dict(url=u, refs=[ln["refs"] for ln in by_url[u]], **results[u]) for u in by_url],
    "lines": [{"refs": ln["refs"], "url": ln.get("url"),
               "http_status": results[ln["url"]]["http_status"] if ln.get("url") else None,
               "result": results[ln["url"]]["result"] if ln.get("url") else "no link"} for ln in lines],
}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
    f.write("\n")
print("tally", tally, "->", OUT)
