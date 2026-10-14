#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K线导演·每日数据囤档（haos/Lucy 引擎逆向复刻原料）

【v2.0 2026-10-10 用户拍板】网站一旦停服，信号标注即永久断供。本任务每天把
全池标的的「信号快照（lucy/haos强/haos弱/AI分析摘要）+ 近3根日K」上传 GitHub
仓库 archive/YYYY-MM-DD.json，为将来数据驱动的引擎逆向复刻囤积带标注样本。

设计：
  · 复用 kx_client（同池口径 futures/EQUITY、排除名单空）
  · 多行缩进 JSON（AI 可直读，人可审计），不压缩（一年 ~22MB，仓库零压力）
  · 上传 Contents API base64（同天重跑自动取 sha 覆盖）
  · stdout 一行摘要（云端任务报告引用）
"""
from __future__ import annotations

import base64
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kx_client import KxClient  # noqa: E402

__version__ = "2.0"

GH_API = "https://api.github.com/repos/Llng125256/kx-combo/contents"
BARS_N = 3          # 每标的囤最近 3 根日K（防当天未收盘缺失）
KLINE_LIMIT = 300   # ★ 实测上游 limit<300 时 haos/lucy 信号字段返回空，必须 300
WORKERS = 16


def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    print(f"[archive] 包代码版本 v{__version__}")
    tok = os.environ.get("KX_GH_TOKEN", "")
    if not tok:
        print("[archive] FATAL: 缺环境变量 KX_GH_TOKEN")
        return 1
    cli = KxClient(signal_age_days=16)
    now = time.time()

    pool = sorted({it["symbol"] for it in
                   (cli.get_signals("futures", "1d", 1, 500).get("items") or [])
                   if (it.get("underlying_type") or "") == "EQUITY" and it.get("symbol")})
    if not pool:
        print("[archive] FATAL: 标的池为空")
        return 1

    def one(sym: str) -> dict:
        try:
            d = cli.get_kline(sym, "futures", "1d", BARS_N)
            sig = d.get("signals") or {}
            h = d.get("haos") or {}
            ai = d.get("ai_analysis") or {}
            bars = [{"t": b.get("time"), "o": b.get("open"), "h": b.get("high"),
                     "l": b.get("low"), "c": b.get("close"), "v": b.get("volume")}
                    for b in (d.get("bars") or []) if isinstance(b, dict)]
            dates = lambda items: sorted({x.get("time", "")[:10] for x in items
                                          if isinstance(x, dict) and x.get("time")})
            return {"sym": sym, "name": d.get("name"),
                    "lucy": dates(sig.get("buy") or []),
                    "haos_s": dates(h.get("strong_buy") or []),
                    "haos_w": dates(h.get("weak_buy") or []),
                    "ai": {k: ai.get(k) for k in
                           ("date", "up_probability", "down_probability", "trend")},
                    "bars": bars}
        except Exception as e:  # noqa: BLE001
            return {"sym": sym, "err": str(e)[:80]}

    with ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(one, pool))
    ok_rows = [r for r in rows if "err" not in r]
    if not ok_rows:
        print("[archive] FATAL: 全部标的拉取失败")
        return 1

    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = {"v": 1, "day": day, "ts": int(now), "pool": len(pool),
               "ok": len(ok_rows), "rows": rows}
    body = json.dumps(payload, ensure_ascii=False, indent=1)
    fname = f"archive/{day}.json"

    hdr = {"Authorization": f"Bearer {tok}"}
    try:
        g = requests.get(f"{GH_API}/{fname}", headers=hdr, timeout=15)
        data = {"message": f"archive {day}",
                "content": base64.b64encode(body.encode()).decode()}
        if g.status_code == 200 and g.json().get("sha"):
            data["sha"] = g.json()["sha"]        # 同天重跑 → 覆盖
        p = requests.put(f"{GH_API}/{fname}", headers=hdr, json=data, timeout=30)
        if p.status_code not in (200, 201):
            print(f"[archive] 上传失败 HTTP {p.status_code}: {str(p.text)[:120]}")
            return 1
    except Exception as e:  # noqa: BLE001
        print(f"[archive] 上传异常: {e}")
        return 1

    nlucy = sum(len(r.get("lucy") or []) for r in ok_rows)
    nhaos = sum(len(r.get("haos_s") or []) + len(r.get("haos_w") or []) for r in ok_rows)
    print(f"[archive] {day} 囤档 OK: 标的 {len(ok_rows)}/{len(pool)} "
          f"信号 lucy {nlucy} 条 / haos {nhaos} 条 → {fname} "
          f"{len(body.encode()) // 1024}KB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
