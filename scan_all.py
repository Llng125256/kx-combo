#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时全量扫描：165 EQUITY 全集（含排除标）按 v1.5 口径判定（用后可删）"""
import sys, time
sys.path.insert(0, "/workspace/kx-combo-v1")
import os
os.chdir("/workspace/kx-combo-v1")
import yaml
from kx_client import KxClient
from monitor_combo import extract_lucy, latest_date, judge_combo

cfg = yaml.safe_load(open("config.yaml"))
w = cfg["watch"]
excluded = set(w.get("exclude_symbols") or [])
cli = KxClient()

# 1) EQUITY 全集（signals API，不套排除名单）
sig = cli.get_signals(market="futures", period="1d", page=1, size=500)
items = sig.get("items") or []
pool = [it["symbol"] for it in items if (it.get("underlying_type") or "") == "EQUITY"]
pool = sorted(set(s for s in pool if s.endswith("USDT")))
print(f"EQUITY 全集: {len(pool)} 个（其中原排除名单 {len([s for s in pool if s in excluded])} 个本次照扫）\n")

# 2) v1.5 判定
now = time.time()
strong, weak, fail = [], [], []
detail = {}
for sym in pool:
    try:
        d = cli.get_kline(sym, "futures", "1d", 300)
    except Exception:
        fail.append(sym); continue
    if not (d.get("bars") or []):
        fail.append(sym); continue
    lucy = extract_lucy(d, now, w["max_signal_age_days"])
    hs = latest_date((d.get("haos") or {}).get("strong_buy"))
    hw = latest_date((d.get("haos") or {}).get("weak_buy"))
    combo = judge_combo(lucy, hs, hw, now, w)
    if combo:
        ent = {"lucy": lucy, "haos": hs if combo.startswith("haos强") else hw,
               "ex": "【原排除标】" if sym in excluded else ""}
        detail[sym] = (combo, ent)
        (strong if combo.startswith("haos强") else weak).append(sym)

print(f"扫描成功 {len(pool)-len(fail)}/{len(pool)}  失败 {len(fail)}: {fail}\n")
print("=== haos强+Lucy买入 ===")
for s in strong:
    e = detail[s][1]
    print(f"{e['ex']}{s[:-4]:<8} Lucy={e['lucy']}  haos强={e['haos']}")
print("\n=== haos弱+Lucy买入 ===")
for s in weak:
    e = detail[s][1]
    print(f"{e['ex']}{s[:-4]:<8} Lucy={e['lucy']}  haos弱={e['haos']}")
