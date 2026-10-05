#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""K线导演·组合信号监控（独立任务，只买入侧）

监控日线买入组合（combo-v1.5 起两种形态；DVVO 组合已于 2026-09-22 用户拍板删除）：
  ① haos强(haos.strong_buy) + Lucy买入(signals.buy)
  ② haos弱(haos.weak_buy)   + Lucy买入(signals.buy)   【v1.5 2026-09-25 用户拍板新增】
  两信号间隔 ≤ 10 天（强弱共用同一上限）；新鲜度门控：取组合中「较晚出现」的
  那个信号日期，距真实时间 ≤ 10 天。同一标的两形态同时满足 → 只推强的。
  扫描范围 = 主监控标的池（EQUITY）+ 主监控排除名单同样跳过。
  满足即推（重复的标也推），消息只带 标的名称 + 组合信号名。

机制（combo-v1.1，2026-09-22 用户拍板口径）：
  · limit=300 日线扫描（用户指定口径）
  · 防抖冻结：只冻结 Lucy —— 冻结只到「信号所在日K收盘」，收盘后直接裁定
  · 首轮/运行中统一：信号K线已收盘且仍在 → 直接记录；当根未收盘 → 冻到收盘裁定
  · 消失同样：冻结到当根收盘，收盘后直接裁定，确认消失才推提醒
  · 防幽灵：冻结期记冻结前已确认读数 cr，裁定以收盘后读数为准
  · 防信号移动到最新日期：Lucy 在册期间仅时间刷新（重绘）→ 不算事件
  · 防僵尸：freeze_max_rounds=3（连续不稳强制裁定）+ freeze_hard_ceiling 硬上限
  · 防孤儿：状态只存 Lucy 在册(1态)与冻结标的，0 态不落盘 → 结构上无堆积
  · 整轮健康度护栏：本轮可用标的 < 上轮在册×0.5 → 整轮跳过，不写状态不推信号
  · Lucy 消失：经冻结裁定确认后推一条「已消失」提醒（用户：消失要让他知道，
    但不要解除类刷屏）
状态：ntfy 同频道独立 title（kx-combo-state-v1），与主监控/持仓跟进互不干扰。
"""
from __future__ import annotations

import json
import logging
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import requests
import yaml

from kx_client import KxClient
from notifier import build_notifiers

log = logging.getLogger("kx.combo")

STATE_MAX_BYTES = 4000          # ntfy 单消息安全上限（与主监控红线一致）
BUY_TAG, GONE_TAG = "🟢", "🔻"


# ====================================================================== #
#  时间工具（日线日期一律 UTC 口径，与主监控一致）
# ====================================================================== #
def day_key(t) -> str | None:
    """把上游时间归一成 'YYYY-MM-DD'（日期串直接用；epoch 转 UTC 日期）。"""
    if isinstance(t, str) and len(t) >= 10:
        d = t[:10]
        try:
            datetime.strptime(d, "%Y-%m-%d")
            return d
        except ValueError:
            return None
    if isinstance(t, (int, float)):
        return datetime.utcfromtimestamp(float(t)).strftime("%Y-%m-%d")
    return None


def day_ts(d: str) -> float:
    """'YYYY-MM-DD' -> UTC 午夜时间戳。"""
    return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()


def confirm_at_1d(now: float) -> int:
    """【combo-v1.1 用户口径 2026-09-22】冻结只到「信号所在日K收盘」：
    发现变化的当根日K收盘时刻 = (obs_day+1)*86400（UTC 零点即日线收盘）。
    收盘后第一轮直接裁定，不再等下一根走完。"""
    return (int(now // 86400) + 1) * 86400


# ====================================================================== #
#  信号提取（★ 主任务同款口径：遍历全部条目，新鲜窗口内取最新，不依赖列表顺序）
# ====================================================================== #
def extract_lucy(data: dict, now: float, win_days: float) -> str | None:
    """Lucy 日线买入 = signals.buy 里「最新鲜」的那条日期；窗口内没有 → None。

    与主监控 get_lucky_signal 一致：不新鲜的老箭头直接丢弃（绝不回看），
    上游把箭头挪到最新日期（重绘）只影响返回的日期值，不影响「是否有」判定。
    """
    best = None
    for it in (data.get("signals") or {}).get("buy") or []:
        if not isinstance(it, dict):
            continue
        d = day_key(it.get("time"))
        if d is None:
            continue
        if (now - day_ts(d)) > win_days * 86400:   # 不新鲜 → 丢弃
            continue
        if best is None or d > best:
            best = d
    return best


def latest_date(items) -> str | None:
    """信号列表里日期最新的那条（间隔+新鲜度双门控会挡老信号）。"""
    ds = [x for x in (day_key(i.get("time")) for i in items or []
                      if isinstance(i, dict)) if x]
    return max(ds) if ds else None


def judge_combo(lucy: str, haos_s: str | None, haos_w: str | None,
                now: float, cfg: dict) -> str | None:
    """组合判定（v1.5：强/弱两形态，间隔与新鲜度共用同一口径）。

    同一标的两形态同时满足 → 只推强的（强语义包含弱，避免重复刷屏）。
    """
    for haos, name in ((haos_s, "haos强+Lucy买入"), (haos_w, "haos弱+Lucy买入")):
        if not lucy or not haos:
            continue
        if abs(day_ts(haos) - day_ts(lucy)) > float(cfg["gap_haos_lucy_days"]) * 86400:
            continue                                  # 间隔超上限 → 不构成组合
        latest = max(day_ts(lucy), day_ts(haos))
        if (now - latest) > float(cfg["combo_fresh_days"]) * 86400:
            continue                                  # 较晚信号已过 10 天 → 不推
        return name
    return None


# ====================================================================== #
#  整轮健康度护栏（主监控 §4af 同款纯函数）
# ====================================================================== #
def round_health_ok(prev_in_reg: int, now_ok: int, ratio: float, enabled: bool) -> bool:
    if not enabled or prev_in_reg < 2:
        return True
    return now_ok >= prev_in_reg * ratio


# ====================================================================== #
#  ntfy 状态读写（同频道独立 title，与主监控互不干扰）
# ====================================================================== #
def state_load(cfg: dict) -> dict:
    try:
        url = (f"https://ntfy.sh/{cfg['ntfy']['channel']}"
               f"/json?poll=1&since=24h")
        r = requests.get(url, timeout=10)
        best = None
        for line in r.text.splitlines():
            try:
                m = json.loads(line)
            except Exception:
                continue
            if m.get("event") == "message" and \
               m.get("title") == cfg["ntfy"]["state_title"]:
                best = m
        if best:
            st = json.loads(best["message"])
            if isinstance(st, dict) and st.get("v") == 1:
                return st
    except Exception as e:  # noqa: BLE001
        log.warning("状态读取失败（按首轮处理）: %s", e)
    return {}


def state_save(st: dict, cfg: dict) -> bool:
    body = json.dumps(st, ensure_ascii=False, separators=(",", ":"))
    if len(body.encode()) > STATE_MAX_BYTES:
        log.error("状态超限 %dB > %dB，本轮不写（保旧状态）", len(body), STATE_MAX_BYTES)
        return False
    try:
        r = requests.post(
            f"https://ntfy.sh/{cfg['ntfy']['channel']}", data=body,
            headers={"Title": cfg["ntfy"]["state_title"],
                     "Tags": "mailbox"},
            timeout=10)
        return r.status_code in (200, 202)
    except Exception as e:  # noqa: BLE001
        log.error("状态写入失败: %s", e)
        return False


# ====================================================================== #
#  扫描
# ====================================================================== #
def fetch_pool(cli: KxClient, cfg: dict) -> list[str]:
    """池 = futures 面板 EQUITY − 排除名单（与主监控同池同排除）。"""
    excl = set(cfg["watch"].get("exclude_symbols") or [])
    pool = []
    for it in (cli.get_signals("futures", "1d", 1, 500).get("items") or []):
        if (it.get("underlying_type") or "") != "EQUITY":
            continue
        sym = it.get("symbol") or ""
        if sym and sym not in excl:
            pool.append(sym)
    return sorted(set(pool))


def scan_all(cli: KxClient, pool: list[str], cfg: dict) -> list[dict]:
    """并发拉日线（limit=300），提取三信号。"""
    win = float(cfg["watch"]["max_signal_age_days"])
    limit = int(cfg["run"].get("kline_limit", 300))

    def one(sym: str) -> dict:
        try:
            d = cli.get_kline(sym, "futures", "1d", limit)
            if not (d.get("bars") or []):
                return {"sym": sym, "ok": False, "lucy": None, "haos": None, "haos_w": None}
            now = time.time()
            return {"sym": sym, "ok": True,
                    "lucy": extract_lucy(d, now, win),
                    "haos": latest_date((d.get("haos") or {}).get("strong_buy")),
                    "haos_w": latest_date((d.get("haos") or {}).get("weak_buy"))}
        except Exception as e:  # noqa: BLE001
            log.warning("拉取 %s 失败: %s", sym, e)
            return {"sym": sym, "ok": False, "lucy": None, "haos": None, "haos_w": None}

    with ThreadPoolExecutor(int(cfg["watch"].get("scan_workers", 16))) as ex:
        return list(ex.map(one, pool))


# ====================================================================== #
#  状态机（冻结只冻 Lucy）
# ====================================================================== #
def run_state_machine(results: list[dict], st: dict, now: float,
                      cfg: dict) -> tuple[dict, list, list]:
    """返回 (新状态, 命中组合行[(sym_label, combo)], 确认消失列表)。"""
    w = cfg["watch"]
    fmr = int(w.get("freeze_max_rounds", 3))
    fhc = int(w.get("freeze_hard_ceiling", 0))
    ceil_s = (fhc if fhc > 0 else max(fmr * 4, 192)) * 3600

    raw: dict = dict(st.get("raw") or {})       # Lucy 在册表（只存 1 态）
    fz: dict = dict(st.get("fz") or {})         # 冻结表 {sym: {pd,cr,r,born}}
    first = ("ok" not in st) and not raw and not fz
    day_start = int(now // 86400) * 86400       # 今日 UTC 零点（= 当根日K起点）

    def _closed(d: str) -> bool:
        """信号所在日K是否已收盘（信号日期 < 今日 UTC 即已收盘）。"""
        return day_ts(d) < day_start

    hits, gone = [], []
    for r in results:
        sym = r["sym"]
        # 【v1.2】读失败不判变化：上游抖动 ≠ Lucy 消失。跳过该标（raw 保留原状、
        #   不误判消失、不误冻结），下一轮读到真值再正常判定。
        if not r["ok"]:
            continue
        cur = 1 if r["lucy"] else 0

        # ── 冻结中：等收盘裁定（防幽灵：cr=冻结前已确认读数）──
        if sym in fz:
            f = fz[sym]
            if now >= f["pd"] or f["r"] >= fmr or (now - f.get("born", now)) >= ceil_s:
                # 【v1.1】到点优先裁定：收盘后直接裁定，以本轮读数为准，
                #         不再被「读数又变」重置推迟
                del fz[sym]
                if cur:
                    raw[sym] = 1
                else:
                    raw.pop(sym, None)
                    if f["cr"] == 1:
                        gone.append(sym)         # 确认消失 → 提醒
                # 裁定完继续走下方组合判定（出现的当轮即推）
            elif cur == 1:
                # 【v1.7 修复】未到点但读到信号健在（已收盘K）→ 立即解冻恢复推送，
                #   不傻等 pd。原逻辑 cr==cur 时 continue 静默到 pd 且 r 不增长，
                #   导致口径放宽/新鲜度恢复后已在册的标被静默挡住最长 21 小时
                #   （2026-09-27 AMAT 实锤）。防幽灵语义不受影响：真消失=cur 0，
                #   仍走收盘裁定路径；当根新信号仍冻到当根收盘。
                del fz[sym]
                if _closed(r["lucy"]):
                    raw[sym] = 1
                else:
                    fz[sym] = {"pd": day_start + 86400, "cr": 1, "r": 0, "born": now}
                    continue
            elif f["cr"] != cur:                 # 未到点但读数又变 → 重置到当根收盘
                f["pd"] = confirm_at_1d(now)
                f["cr"] = cur
                f["r"] = int(f.get("r", 0)) + 1
            else:
                continue                         # 仍在冻结：不推不判
            if not cur:
                continue

        if first:
            if cur:
                # 【v1.1 用户口径】首轮：信号K线已收盘且仍在 → 直接记录；
                # 当根未收盘 → 冻到收盘，收盘后还在才记录
                if _closed(r["lucy"]):
                    raw[sym] = 1
                else:
                    fz[sym] = {"pd": day_start + 86400, "cr": 0, "r": 0, "born": now}
            continue

        if cur:
            if sym not in raw:
                # 【v1.1 用户口径】运行中新出现：信号K线已收盘且仍在 → 直接记录；
                # 当根未收盘 → 冻到收盘，收盘后直接裁定
                if _closed(r["lucy"]):
                    raw[sym] = 1
                else:
                    fz[sym] = {"pd": day_start + 86400, "cr": 0, "r": 0, "born": now}
                    continue
            combo = judge_combo(r["lucy"], r["haos"], r.get("haos_w"), now, w)
            if combo:
                hits.append((sym, combo, r["lucy"]))  # 在册且满足 → 每轮都推（v1.8 带 Lucy 日期）
        elif sym in raw:
            # 1→0 消失 → 冻到当根收盘，收盘后直接裁定（v1.1 用户口径）
            fz[sym] = {"pd": confirm_at_1d(now), "cr": 1, "r": 0, "born": now}
            raw.pop(sym, None)
        # cur=0 且不在冻结且不在 raw → 无事件（0 态不落盘，天然无孤儿堆积）

    new_st = {"v": 1, "ls": int(now), "raw": raw, "fz": fz,
              "ok": sum(1 for x in results if x["ok"])}
    return new_st, hits, gone


# ====================================================================== #
#  推送（简洁：标的名称 + 组合信号名，其他一律不要）
# ====================================================================== #
def short(sym: str) -> str:
    return sym[:-4] if sym.endswith("USDT") else sym


def push_messages(notifiers: list, hits: list, gone: list, now: float) -> bool:
    if not hits and not gone:
        return False
    lines = [f"{BUY_TAG} 组合买入（日线） {datetime.utcfromtimestamp(now):%m-%d %H:%M}UTC"]
    lines += [f"- {short(s)} {c} Lucy={l}" for s, c, l in hits]
    if gone:
        lines.append("")
        lines.append(f"{GONE_TAG} Lucy买入已消失")
        lines += [f"- {short(s)}" for s in gone]
    md = "\n".join(lines)
    ok = False
    for name, n in notifiers:
        ok = n.send("组合信号监控", md) or ok
    return ok


def push_alert(notifiers: list, text: str) -> None:
    for _, n in notifiers:
        n.send("组合信号监控", text)


def push_log_ntfy(cfg: dict, hits: list, gone: list, ok_n: int, pool_n: int) -> None:
    """【v1.2】推送记录落盘（title=kx-combo-push-log），事后可回查推了什么。"""
    try:
        body = json.dumps(
            {"v": 1, "ts": int(time.time()), "ok": ok_n, "pool": pool_n,
             "hits": [s for s, _, _ in hits], "combos": {s: c for s, c, _ in hits},
             "gone": gone}, ensure_ascii=False, separators=(",", ":"))
        requests.post(f"https://ntfy.sh/{cfg['ntfy']['channel']}", data=body,
                      headers={"Title": cfg["ntfy"]["pushlog_title"], "Tags": "memo"},
                      timeout=10)
    except Exception as e:  # noqa: BLE001
        log.warning("推送日志落盘失败: %s", e)


# ====================================================================== #
def main() -> int:
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    dry = "--dry" in sys.argv
    cfg = yaml.safe_load(open("config.yaml", encoding="utf-8"))
    cli = KxClient(signal_age_days=cfg["watch"]["max_signal_age_days"])
    notifiers = [] if dry else build_notifiers(cfg)

    st = state_load(cfg)
    now = time.time()

    pool = fetch_pool(cli, cfg)
    if not pool:
        push_alert(notifiers, "⚠️ 标的池为空，本轮跳过")
        return 1
    results = scan_all(cli, pool, cfg)
    ok_n = sum(1 for x in results if x["ok"])

    # 整轮健康度护栏（主监控同款）：大面积失败 → 跳过，绝不写状态
    prev_ok = int(st.get("ok") or 0)
    if not round_health_ok(prev_ok, ok_n,
                           float(cfg["watch"].get("min_scan_success_ratio", 0.5)),
                           bool(cfg["watch"].get("round_health_guard", True))):
        push_alert(notifiers, f"⚠️ 上游异常·本轮已跳过（可用 {ok_n}/{prev_ok}）")
        return 1

    new_st, hits, gone = run_state_machine(results, st, now, cfg)

    if dry:
        print(f"[dry] 池 {len(pool)} 可用 {ok_n} | raw {len(new_st['raw'])} "
              f"fz {len(new_st['fz'])} | 命中 {len(hits)} 消失 {len(gone)}")
        for s, c, l in hits:
            print(f"  [dry] {short(s)} {c} Lucy={l}")
        for s in gone:
            print(f"  [dry] 消失 {short(s)}")
        return 0

    push_messages(notifiers, hits, gone, now)
    push_log_ntfy(cfg, hits, gone, ok_n, len(pool))
    state_save(new_st, cfg)
    # 【v1.2】任务日志留一行简报（不再完全静默，云端日志页可见）
    print(f"[combo] {datetime.utcfromtimestamp(now):%m-%d %H:%M}UTC "
          f"可用 {ok_n}/{len(pool)} 命中 {len(hits)} 消失 {len(gone)} "
          f"raw {len(new_st['raw'])} fz {len(new_st['fz'])}")
    for s, c, l in hits:
        print(f"[combo]   推送 {s} {c} Lucy={l}")
    for s in gone:
        print(f"[combo]   消失 {s}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
