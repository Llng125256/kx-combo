#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""组合信号监控 单元测试（纯函数层，无网络）"""
import time
import sys

sys.path.insert(0, ".")
from monitor_combo import (day_key, day_ts, confirm_at_1d, extract_lucy,
                           latest_date, judge_combo, round_health_ok, short)

CFG = {"gap_haos_lucy_days": 10, "combo_fresh_days": 10}
NOW = day_ts("2026-09-22") + 3600          # 09-22 01:00 UTC
PASS = 0


def ok(cond, name):
    global PASS
    assert cond, f"FAIL: {name}"
    PASS += 1
    print(f"  ok  {name}")


# ---------- day_key / confirm_at_1d ----------
ok(day_key("2026-09-17") == "2026-09-17", "day_key 日期串")
ok(day_key(1790000000) == "2026-09-21", "day_key epoch")
ok(day_key(None) is None and day_key("bad") is None, "day_key 容错")
# 【v1.1 用户口径】冻结只到信号所在日K收盘：+1 天 00:00（旧口径 +2 已废弃）
ok(confirm_at_1d(day_ts("2026-09-22")) == day_ts("2026-09-23"), "1d 冻结到 = 信号K线收盘(+1天00:00)")
ok(confirm_at_1d(day_ts("2026-09-22") + 86399) == day_ts("2026-09-23"), "1d 冻结到跨日不变")

# ---------- extract_lucy（主任务口径：遍历全部取最新鲜，不依赖顺序）----------
data = {"signals": {"buy": [
    {"time": "2025-10-21", "price": 169.47},          # 老箭头（乱序在前）
    {"time": "2026-09-12", "price": 112.0},           # 新鲜
    {"time": "2026-09-15", "price": 118.0},           # 最新鲜（不在末位）
]}}
ok(extract_lucy(data, NOW, 10) == "2026-09-15", "lucy 取新鲜窗口内最新（乱序不误判）")
data2 = {"signals": {"buy": [{"time": "2025-10-21"}]}}
ok(extract_lucy(data2, NOW, 10) is None, "lucy 全过期 → None")
ok(extract_lucy({"signals": {}}, NOW, 10) is None, "lucy 空 → None")
# 10 天边界：09-12 距 09-22 01:00 = 10.04 天 → 丢弃；09-13 → 9.04 天 → 保留
ok(extract_lucy({"signals": {"buy": [{"time": "2026-09-12"}]}}, NOW, 10) is None,
   "lucy 新鲜度边界：>10 天丢弃")
ok(extract_lucy({"signals": {"buy": [{"time": "2026-09-13"}]}}, NOW, 10) == "2026-09-13",
   "lucy 新鲜度边界：≤10 天保留")

# ---------- latest_date ----------
ok(latest_date([{"time": "2026-06-17"}, {"time": "2026-09-17"}]) == "2026-09-17",
   "haos/dvvo 取最新")
ok(latest_date([]) is None and latest_date(None) is None, "haos/dvvo 空 → None")

# ---------- judge_combo（v1.5：强/弱两形态，间隔≤10天+较晚≤10天，同满足推强）----------
ok(judge_combo("2026-09-20", "2026-09-15", None, NOW, CFG) == "haos强+Lucy买入",
   "强组合：间隔 5 天成立")
ok(judge_combo("2026-09-20", "2026-09-12", None, NOW, CFG) == "haos强+Lucy买入",
   "强组合：间隔 8 天成立（v1.4 口径 7→10）")
ok(judge_combo("2026-09-20", "2026-09-10", None, NOW, CFG) == "haos强+Lucy买入",
   "强组合：间隔 10 天（边界）成立")
ok(judge_combo("2026-09-20", "2026-09-09", None, NOW, CFG) is None,
   "强组合：间隔 11 天 → 不推（v1.4 新边界）")
# 新鲜度：较晚信号（09-13）距 09-22 01:00 = 9.04 天 → 成立；较晚 09-11 → 11 天 → 不推
ok(judge_combo("2026-09-11", "2026-09-10", None, NOW, CFG) is None,
   "强组合：新鲜度 较晚>10 天 → 不推（防信号移动到老日期）")
ok(judge_combo("2026-09-13", "2026-09-06", None, NOW, CFG) == "haos强+Lucy买入",
   "强组合：较晚≤10 天 → 推（haos 较老由间隔门控挡）")
ok(judge_combo("2026-09-20", None, None, NOW, CFG) is None, "只有 lucy → 不构成组合")
ok(judge_combo(None, "2026-09-20", None, NOW, CFG) is None, "lucy 消失 → 不推")
# ---- v1.5 弱组合（haos.weak_buy + Lucy，口径与强共用）----
ok(judge_combo("2026-09-20", None, "2026-09-15", NOW, CFG) == "haos弱+Lucy买入",
   "弱组合：仅弱信号成立 → 推弱")
ok(judge_combo("2026-09-20", "2026-09-09", "2026-09-15", NOW, CFG) == "haos弱+Lucy买入",
   "强弱并存但强被间隔挡 → 弱顶上")
ok(judge_combo("2026-09-20", "2026-09-15", "2026-09-16", NOW, CFG) == "haos强+Lucy买入",
   "强弱同满足 → 只推强（防重复刷屏）")
ok(judge_combo("2026-09-20", "2026-09-20", "2026-09-08", NOW, CFG) == "haos强+Lucy买入",
   "强成立弱间隔12天 → 推强")
ok(judge_combo("2026-09-11", None, "2026-09-10", NOW, CFG) is None,
   "弱组合：新鲜度 较晚>10 天 → 不推")
ok(judge_combo("2026-09-20", "2026-09-05", "2026-09-09", NOW, CFG) is None,
   "弱组合：间隔 11 天 → 不推")
ok(judge_combo(None, None, "2026-09-15", NOW, CFG) is None, "弱组合：lucy 无 → 不推")

# ---------- round_health_ok（主监控 §4af 同款）----------
ok(round_health_ok(160, 100, 0.5, True), "护栏：可用过半 → 放行")
ok(not round_health_ok(160, 70, 0.5, True), "护栏：可用不足半 → 跳过")
ok(round_health_ok(1, 0, 0.5, True), "护栏：上轮<2 豁免")
ok(round_health_ok(160, 0, 0.5, False), "护栏：总开关关闭 → 放行")

# ---------- short ----------
ok(short("METAUSDT") == "META", "标的名去 USDT")
ok(short("BRKBUSDT") == "BRKB", "去 USDT 不误伤")

# ---------- 状态机（v1.1 用户口径：冻结只到信号K线收盘，收盘后直接裁定）----------
from monitor_combo import run_state_machine
W = {"watch": {"gap_haos_lucy_days": 10, "gap_dvvo_lucy_days": 3,
               "combo_fresh_days": 10, "freeze_max_rounds": 3,
               "freeze_hard_ceiling": 0}}
T0 = day_ts("2026-09-22") + 8 * 3600        # 09-22 08:00 UTC（当根K线未收盘）
T1 = day_ts("2026-09-23") + 1 * 3600        # 09-23 01:00 UTC（当根已收盘后）
R = lambda s, l: [{"sym": s, "ok": True, "lucy": l, "haos": None}]

# 首轮：已收盘信号（09-21）→ 直接记录
st, _, _ = run_state_machine(R("AAAUSDT", "2026-09-21"), {}, T0, W)
ok(st["raw"].get("AAAUSDT") == 1 and not st["fz"], "首轮：已收盘信号直接记录（不观望）")
# 首轮：当根未收盘信号（09-22）→ 冻到 09-23 00:00（收盘）
st, _, _ = run_state_machine(R("BBBUSDT", "2026-09-22"), {}, T0, W)
ok(st["fz"]["BBBUSDT"]["pd"] == day_ts("2026-09-23"), "首轮：当根信号冻到收盘")
# 收盘后第一轮裁定：还在 → 记录
st, _, _ = run_state_machine(R("BBBUSDT", "2026-09-22"), st, T1, W)
ok(st["raw"].get("BBBUSDT") == 1 and "BBBUSDT" not in st["fz"], "收盘后裁定：还在 → 记录")
# 运行中新出现：已收盘K线上的信号 → 直接记录
st, _, _ = run_state_machine(R("CCCUSDT", "2026-09-21"), {"v":1,"ls":1,"raw":{"DDDUSDT":1},"fz":{},"ok":100}, T0, W)
ok(st["raw"].get("CCCUSDT") == 1 and "CCCUSDT" not in st["fz"], "运行中：已收盘新信号直接记录")
# 运行中新出现：当根未收盘 → 冻到收盘
st, _, _ = run_state_machine(R("EEEUSDT", "2026-09-22"), {"v":1,"ls":1,"raw":{"DDDUSDT":1},"fz":{},"ok":100}, T0, W)
ok(st["fz"]["EEEUSDT"]["pd"] == day_ts("2026-09-23"), "运行中：当根新信号冻到收盘")
# 消失 → 冻结到当根收盘，收盘后裁定确认 → 推提醒
st3, _, _ = run_state_machine(R("AAAUSDT", None), {"v":1,"ls":1,"raw":{"AAAUSDT":1},"fz":{},"ok":100}, T0, W)
ok(st3["fz"]["AAAUSDT"]["pd"] == day_ts("2026-09-23") and st3["fz"]["AAAUSDT"]["cr"] == 1,
   "消失：冻到当根收盘")
st4, _, gone4 = run_state_machine(R("AAAUSDT", None), st3, T1, W)
ok(gone4 == ["AAAUSDT"] and "AAAUSDT" not in st4["raw"], "消失裁定：收盘确认 → 提醒")
# 消失裁定：收盘后又回来了 → 不提醒，回到在册
st5, _, gone5 = run_state_machine(R("AAAUSDT", "2026-09-23"), st3, T1, W)
ok(not gone5 and st5["raw"].get("AAAUSDT") == 1, "消失裁定：收盘后回来 → 静默回在册")

# ---------- v1.2 读失败不判变化（上游抖动 ≠ Lucy 消失）----------
base = {"v": 1, "ls": 1, "raw": {"AAAUSDT": 1, "BBBUSDT": 1}, "fz": {}, "ok": 100}
st6, hits6, gone6 = run_state_machine(
    [{"sym": "AAAUSDT", "ok": False, "lucy": None, "haos": None}]
    + R("BBBUSDT", "2026-09-21"), base, T0, W)
ok(st6["raw"].get("AAAUSDT") == 1 and "AAAUSDT" not in st6["fz"] and not gone6,
   "v1.2：读失败 → raw 保留、不误判消失、不冻结")
ok(st6["raw"].get("BBBUSDT") == 1, "v1.2：读成功的标正常处理")
ok(st6["ok"] == 1, "v1.2：ok 计数=本轮实算成功数（护栏分母语义不变）")

# ---------- v1.7 冻结中信号健在 → 立即解冻恢复推送（2026-09-27 AMAT 实锤场景）----------
W16 = {"watch": {"gap_haos_lucy_days": 10, "combo_fresh_days": 16,
                 "freeze_max_rounds": 3, "freeze_hard_ceiling": 0}}
T_AMAT = day_ts("2026-09-27") + 2 * 3600     # 09-27 02:00 UTC（16 天口径生效后）
st_amat = {"v": 1, "ls": 1, "raw": {"COSTUSDT": 1},
           "fz": {"AMATUSDT": {"pd": day_ts("2026-09-28"), "cr": 1, "r": 2,
                               "born": day_ts("2026-09-27") - 6 * 3600}},
           "ok": 100}
res7 = [{"sym": "AMATUSDT", "ok": True, "lucy": "2026-09-17",
         "haos": "2026-09-11", "haos_w": None}]
st7, hits7, gone7 = run_state_machine(res7, st_amat, T_AMAT, W16)
ok("AMATUSDT" not in st7["fz"] and st7["raw"].get("AMATUSDT") == 1,
   "v1.7：冻结中信号健在(已收盘) → 立即解冻回在册")
ok(hits7 == [("AMATUSDT", "haos强+Lucy买入", "2026-09-17")],
   "v1.7：解冻当轮即推送（不等收盘裁定，v1.8 行内带 Lucy 日期）")
ok(st7["raw"].get("COSTUSDT") == 1 and not gone7,
   "v1.7：其他在册标不受影响、无误报消失")
# 冻结中 cur=1 但当根信号未收盘 → 仍冻到当根收盘（防幽灵保留）
st_uf = {"v": 1, "ls": 1, "raw": {},
         "fz": {"XXXUSDT": {"pd": day_ts("2026-09-28"), "cr": 1, "r": 0,
                            "born": day_ts("2026-09-27") - 3600}},
         "ok": 10}
st8, hits8, _ = run_state_machine(R("XXXUSDT", "2026-09-27"), st_uf, T_AMAT, W16)
ok(st8["fz"].get("XXXUSDT") is not None and not hits8,
   "v1.7：冻结中当根未收盘信号 → 仍冻结不推（防幽灵保留）")
# cur=0 路径不变：读数变 0 → 仍走重置路径（r 累加）
st9, _, _ = run_state_machine(R("AMATUSDT", None), st_amat, T_AMAT, W16)
ok(st9["fz"].get("AMATUSDT", {}).get("cr") == 0
   and st9["fz"]["AMATUSDT"]["r"] == 3,
   "v1.7：cur=0 读数变化 → 仍走重置路径（原语义不变）")

print(f"\n全部 {PASS} 项通过 ✅")
