#!/usr/bin/env python3
"""WUSV 2026: 公式 fci.systems から出場者・成績・スタートリストを取得して data.json を作る"""
import re, html, json, datetime, urllib.request, urllib.parse, uuid, sys, os

EVENT = "WUSV2026"
BASE = "https://wusv2026.fci.systems"
API = "https://api.fci.systems"
UA = {"User-Agent": "Mozilla/5.0 (wusv2026-tracker)", "Origin": BASE, "Referer": BASE + "/results.php"}
DAYMAP = {"Monday": "2026-10-05", "Tuesday": "2026-10-06", "Wednesday": "2026-10-07",
          "Thursday": "2026-10-08", "Friday": "2026-10-09", "Saturday": "2026-10-10", "Sunday": "2026-10-11"}

def T(x):
    return re.sub(r"\s+", " ", html.unescape(re.sub("<[^>]+>", "", x)).replace("\xa0", " ")).strip()

def get(url):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

def post(url, fields):
    b = uuid.uuid4().hex
    body = "".join(f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n' for k, v in fields.items()) + f"--{b}--\r\n"
    req = urllib.request.Request(url, data=body.encode(), headers={**UA, "Content-Type": f"multipart/form-data; boundary={b}"})
    return urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")

def num(x):
    try: return int(x)
    except Exception: return None

def participants():
    h = get(BASE + "/participants.php")
    i = h.find("<tbody"); j = h.find("</tbody>", i)
    parts, leaders, names, code = [], {}, {}, None
    for r in re.findall(r"<tr>(.*?)</tr>", h[i:j], re.S):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
        m = re.search(r'flags/(\w+)\.png" alt="([^"]+)"', r)
        if m and len(tds) == 2:
            code = m.group(1); names[code] = m.group(2); continue
        c = [T(x) for x in tds]
        if len(c) < 6: continue
        if not c[1]:
            leaders.setdefault(code, [])
            n = c[2].replace("(Team Leader)", "").strip()
            if n not in leaders[code]: leaders[code].append(n)
            continue
        sx = "F" if "female" in tds[4] else ("M" if "male" in tds[4] else "")
        parts.append(dict(cc=code, cat=c[1], h=c[2].replace("(RES)", "").strip(), d=c[3], sx=sx, dob=c[5][:10], res="(RES)" in c[2]))
    return parts, leaders, names

def results():
    r = post(API + "/res_abc.php", {"zaw_id": EVENT, "lang": "en"})
    out = {}
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", r, re.S):
        c = [T(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if len(c) >= 12: out[c[2]] = c
    return out

def schedule(parts):
    """shedule1.php を読み、WUSV 2026 の出場者と一致する場合だけ採用する（別大会のリストを誤って取り込まない）"""
    try: s = get(BASE + "/shedule1.php")
    except Exception as e:
        print("schedule fetch failed:", e); return {}
    byc = {p["cat"]: p for p in parts}
    rows = re.findall(r"<tr>(<td nowrap class=\"text-center align-middle\">\d+\.</td>.*?)</tr>", s, re.S)
    sched, hit = {}, 0
    for r in rows:
        c = [T(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(c) < 6: continue
        cat, hd = c[1], c[2]
        if cat in byc and byc[cat]["h"] == hd: hit += 1
        e = {}
        for k, v in zip("ABC", c[3:6]):
            m = re.match(r"(\w+)\s+(\d{1,2}:\d{2})", v)
            if m and m.group(1) in DAYMAP: e[k] = f"{DAYMAP[m.group(1)]} {m.group(2)}"
        if e: sched[cat] = e
    ratio = hit / len(rows) if rows else 0
    print(f"schedule rows={len(rows)} match={hit} ({ratio:.0%})")
    return sched if ratio >= 0.8 else {}

def main():
    parts, leaders, names = participants()
    if len(parts) < 50: sys.exit("participants parse failed")
    res = results()
    for p in parts:
        c = res.get(p["cat"])
        p["st"] = num(c[1]) if c else None
        for k, ix in (("a", 6), ("b", 7), ("c", 8), ("t", 9)): p[k] = num(c[ix]) if c else None
        p["rt"] = c[10] if c else ""
    sched = schedule(parts)
    body = dict(countries=names, leaders=leaders, parts=parts, sched=sched)
    old = {}
    if os.path.exists("data.json"):
        try: old = json.load(open("data.json"))
        except Exception: pass
    now = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
    same = {k: old.get(k) for k in body} == body
    print("changed" if not same else "no change", len(parts), "scored:", sum(1 for p in parts if p["t"] is not None or p["a"] is not None))
    if same: return  # 変化なしならファイルを触らない（無駄なコミットを作らない）
    data = dict(updated=now, **body)
    json.dump(data, open("data.json", "w"), ensure_ascii=False, separators=(",", ":"))

if __name__ == "__main__":
    main()
