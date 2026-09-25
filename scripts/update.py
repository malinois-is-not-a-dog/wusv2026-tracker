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

# 棄権・失格・中止などの表記（大会ごとに違う表記・言語を吸収）
STATUS = [
    ("W", r"withdr|zur(ü|ue)ckgez|retir|\bwd\b|\bret\b|forfeit|verzicht"),
    ("D", r"disq|\bdis\b|\bdq\b|\bdsq\b|ausschluss|\bdisk"),
    ("T", r"termin|abbruch|abgebr|abandon|abort|\babb\b|\babr\b|\bterm\b|stopped|break off"),
    ("N", r"absent|not present|no show|nicht angetr|\bn\.?a\.?\b|\bdns\b|n\.?\s?b\.?"),
]
def status_code(text):
    t = (text or "").strip().lower()
    if not t: return None
    for code, pat in STATUS:
        if re.search(pat, t): return code
    return None

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
    """抽選後の公式スタートリストを各選手に結び付ける。
    shedule1.php: 抽選番号・A/B/C の日時（全体の出番表）
    shedule2.php: スタジアム (B/C) の日別出番表。最終日などで順番が変わることがあるので、こちらを優先
    どちらも WUSV 2026 の出場者と8割以上一致したときだけ採用（別大会のリストを誤って取り込まない）"""
    byc = {p["cat"]: p for p in parts}
    out = {}
    try: s = get(BASE + "/shedule1.php")
    except Exception as e:
        print("schedule fetch failed:", e); return {}
    s = re.sub(r"<!--.*?-->", "", s, flags=re.S)
    rows = re.findall(r"<tr>(<td nowrap class=\"text-center align-middle\">\d+\.</td>.*?)</tr>", s, re.S)
    hit = 0
    for r in rows:
        c = [T(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)]
        if len(c) < 6: continue
        cat = c[1]
        if cat in byc and byc[cat]["h"] == c[2]: hit += 1
        e = {"no": num(c[0].rstrip("."))}
        if "<del>" in r: e["x"] = 1  # 取り消し線 = 棄権・出場取り消し
        for k, v in zip("ABC", c[3:6]):
            m = re.match(r"(\w+)\s+(\d{1,2}:\d{2})", v)
            if m and m.group(1) in DAYMAP: e[k] = f"{DAYMAP[m.group(1)]} {m.group(2)}"
        out[cat] = e
    ratio = hit / len(rows) if rows else 0
    print(f"shedule1 rows={len(rows)} match={hit} ({ratio:.0%})")
    if ratio < 0.8: return {}
    try:
        s2 = re.sub(r"<!--.*?-->", "", get(BASE + "/shedule2.php"), flags=re.S)
        n2 = 0
        for sec in re.split(r'<div class="card-header"><h3>', s2)[1:]:
            day = DAYMAP.get(sec.split("<", 1)[0].strip())
            if not day: continue
            for part, rest in re.findall(r'<tr><td nowrap class="text-center align-middle">([ABC])</td>(.*?)</tr>', sec, re.S):
                c = [T(x) for x in re.findall(r"<td[^>]*>(.*?)</td>", rest, re.S)]
                if len(c) >= 3 and c[2] in out and re.match(r"\d{1,2}:\d{2}$", c[0]):
                    out[c[2]][part] = f"{day} {c[0]}"; out[c[2]].setdefault("std", []).append(part); n2 += 1
        print(f"shedule2 stadium slots applied={n2}")
    except Exception as e:
        print("stadium list skipped:", e)
    return out

def validate(parts, res):
    """公式の形式が変わったら失敗させる → GitHubから所有者にメールが届く。data.json は上書きしない"""
    errs = []
    if len(parts) < 100: errs.append(f"participants too few: {len(parts)}")
    main_cats = {p["cat"] for p in parts if not p["res"]}
    hit = len(main_cats & set(res))
    if hit < 0.8 * len(main_cats): errs.append(f"results rows match only {hit}/{len(main_cats)} entries")
    for cat, c in res.items():
        a, b, cc, t = (num(c[i]) for i in (6, 7, 8, 9))
        for k, v in (("A", a), ("B", b), ("C", cc)):
            if v is not None and not 0 <= v <= 100: errs.append(f"{cat} {k}={v} out of range")
        if None not in (a, b, cc, t) and a + b + cc != t: errs.append(f"{cat} total {t} != {a}+{b}+{cc}")
    if errs:
        print("VALIDATION FAILED:"); [print(" -", e) for e in errs[:30]]
        sys.exit(1)

def main():
    parts, leaders, names = participants()
    res = results()
    validate(parts, res)
    for p in parts:
        c = res.get(p["cat"])
        p["st"] = num(c[1]) if c else None  # Start No.（抽選番号）
        for k, ix in (("a", 6), ("b", 7), ("c", 8), ("t", 9)):
            v = c[ix] if c else ""
            p[k] = num(v)
            if p[k] is None and v and v not in ("-", "—"):
                p[k + "x"] = v  # 数字でない表記（DIS / Abbruch / 0* など）はそのまま保持
        p["rt"] = c[10] if c else ""
        p["pl"] = c[11] if c and c[11] not in ("-", "") else ""
        # 状態：評価欄 → 各科目欄 → 総合欄 の順で判定
        code = status_code(p["rt"])
        for k in ("ax", "bx", "cx", "tx"):
            code = code or status_code(p.get(k, ""))
        if code: p["ss"] = code
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
