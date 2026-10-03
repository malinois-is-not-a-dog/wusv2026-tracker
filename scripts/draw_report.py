"""抽選結果が初めて取り込まれたときの確認レポート（GitHub Issue 本文）を作る。
異常があれば先頭に ⚠️ を付ける。"""
import json, sys, collections
d = json.load(open("data.json")); S = d.get("sched", {})
main = [p for p in d["parts"] if not p["res"]]
by = {p["cat"]: p for p in d["parts"]}
prob = []
miss = [p["cat"] for p in main if p["cat"] not in S]
if miss: prob.append(f"出番表に無い本戦選手 {len(miss)}名: {', '.join(miss[:20])}")
nofull = [c for c, e in S.items() if not all(k in e for k in "ABC") and not e.get("x")]
if nofull: prob.append(f"A/B/C の日時が欠けている選手 {len(nofull)}名: {', '.join(nofull[:20])}")
nos = collections.Counter(e.get("no") for e in S.values())
dup = [n for n, k in nos.items() if n and k > 1]
if dup: prob.append(f"抽選番号の重複: {dup[:10]}")
L = []
L.append(("⚠️ 確認が必要な点があります" if prob else "✅ 自動チェックはすべて正常") + "\n")
L.append(f"- 出番表に載った選手: {len(S)} / 本戦 {len(main)}")
L.append(f"- スタジアム枠を反映: {sum(len(e.get('std', [])) for e in S.values())}")
L.append(f"- 棄権（取り消し線）: {sum(1 for e in S.values() if e.get('x'))}")
for x in prob: L.append(f"- ⚠️ {x}")
L.append("\n| 選手 | 抽選 | A 追及 | B 服従 | C 防衛 |\n|---|---|---|---|---|")
for c in ["JP-01", "JP-02", "TW-01"]:
    e = S.get(c, {}); p = by.get(c, {})
    L.append(f"| {c} {p.get('h','')} | #{e.get('no','-')} | {e.get('A','-')} | {e.get('B','-')} | {e.get('C','-')} |")
L.append("\nサイト: https://malinois-is-not-a-dog.github.io/wusv2026-tracker/#sched")
L.append("公式: https://wusv2026.fci.systems/shedule1.php")
open("draw_report.md", "w").write("\n".join(L))
print("\n".join(L))
sys.exit(0)
