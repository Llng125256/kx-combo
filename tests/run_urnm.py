#!/usr/bin/env python3
"""URNMUSDT 单标看护运行器（交班件指定跑法：import replica_monitor.analyse 单标执行）。

口径（交班快照 2026-10-12 18:00）：
- 券商止损 45.25（盘中触发单，用户自选口径）
- 引擎口径：日线收盘 < 45.25（含容差，有效止损线 ≈45.70 收盘确认）→ 破位离场
- 死锚出场 ≈49.1；30天硬顶至 11-08
"""
import json
import sys

sys.path.insert(0, "/tmp/kxhandover/pkg")

from kx_client import KxClient  # noqa: E402
import replica_monitor as rm    # noqa: E402

SYM = "URNMUSDT"
STOP_BROKER = 45.25   # 券商盘中触发止损（用户口径）
STOP_ENGINE = 45.70   # 引擎收盘确认止损线（含容差有效 ≈45.25）
DEAD_ANCHOR_EXIT = 49.1

cli = KxClient()
d = cli.get_kline(SYM, "futures", "1d", 300)
bars = d.get("bars") or []
if len(bars) < 40:
    print(json.dumps({"error": f"bars insufficient: {len(bars)}"}, ensure_ascii=False))
    sys.exit(1)

last = bars[-1]
last_date = str(last["time"])[:10]
last_close = float(last["close"])

sig, cands, tdays, lc, dset = rm.analyse(SYM, bars, None)

out = {
    "symbol": SYM,
    "engine_version": rm.__version__,
    "last_bar_date": last_date,
    "last_close": last_close,
    "bars_count": len(bars),
    "judgment": {
        "engine_stop_line": STOP_ENGINE,
        "close_below_engine_stop": last_close < STOP_ENGINE,
        "close_below_broker_stop": last_close < STOP_BROKER,
        "dead_anchor_exit": DEAD_ANCHOR_EXIT,
    },
    "latest_display_signal": None,
    "candidates_tail": [],
}
if sig is not None:
    out["latest_display_signal"] = {
        k: (v if not hasattr(v, "item") else v.item()) for k, v in sig.items()
    } if isinstance(sig, dict) else str(sig)

for c in list(cands)[-3:]:
    out["candidates_tail"].append(
        {k: (v if not hasattr(v, "item") else v.item()) for k, v in c.items()}
        if isinstance(c, dict) else str(c)
    )

print(json.dumps(out, ensure_ascii=False, indent=2, default=str))
