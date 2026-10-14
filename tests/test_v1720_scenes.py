#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.7.20 核心场景模拟测试（10 场景，纯合成K线，零网络依赖）
口径：肯特纳 EMA10±ATR14 触下轨+收盘位>0.3；唯一分级=主信号(下影>40%)→🥈否则·；
周六(UTC)信号下册(touch_days 仍计)；周日 sun_half 降权0.5；破位机=死区0.3×ATR+三确认≥1
→2日观察期，收上信号日 EMA10−ATR 复活，期满离场；HARD_CAP=30；stop_eff=止损−0.3×ATR。
"""
import os
import sys
from datetime import date, timedelta

os.environ.pop('KX_GH_TOKEN', None)
sys.path.insert(0, '/tmp/kxhandover/pkg')
import numpy as np
import replica_monitor as rm

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('✅' if cond else '❌'), name, ('| ' + detail) if detail else '')


FLAT = dict(open=99.8, high=100.5, low=99.5, close=100.0, volume=1000)
TAIL = dict(open=98.5, high=99.3, low=97.5, close=98.8, volume=1000)   # 尾段：不触✅/不破位


def make_bars(start='2026-08-14', n=60, tail_from=None, tail=TAIL):
    d0 = date.fromisoformat(start)
    bars = []
    for k in range(n):
        d = d0 + timedelta(days=k)
        b = {'time': d.isoformat() + 'T00:00:00Z', **FLAT}
        if tail_from is not None and k >= tail_from:
            b.update(tail)
        bars.append(b)
    return bars


def set_bar(bars, i, o, h, l, c, v=1000):
    bars[i] = dict(bars[i], open=o, high=h, low=l, close=c, volume=v)


def atr_at(bars, i):
    hi = np.array([b['high'] for b in bars]); lo = np.array([b['low'] for b in bars])
    cl = np.array([b['close'] for b in bars])
    tr = np.concatenate([[hi[0] - lo[0]], np.maximum(hi[1:], cl[:-1]) - np.minimum(lo[1:], cl[:-1])])
    return float(tr[i - 14:i].mean())


def engine_arrays(bars):
    high = np.array([b['high'] for b in bars]); low = np.array([b['low'] for b in bars])
    close = np.array([b['close'] for b in bars]); vol = np.array([float(b['volume']) for b in bars])
    n = len(bars)
    ema10 = rm.ema(close, 10)
    tr = np.maximum(high[1:], close[:-1]) - np.minimum(low[1:], close[:-1])
    tr = np.concatenate([[high[0] - low[0]], tr])
    atr = np.full(n, np.nan)
    for k in range(14, n):
        atr[k] = tr[k - 14:k].mean()
    tp = (high + low + close) / 3
    cci = np.full(n, np.nan)
    for k in range(19, n):
        w = tp[k - 19:k + 1]; m = w.mean(); cci[k] = (tp[k] - m) / (0.015 * np.abs(w - m).mean() + 1e-9)
    dates = [str(b['time'])[:10] for b in bars]
    return high, low, close, vol, ema10, atr, cci, n, dates


I_FRI = 49   # 2026-10-02 周五（起始 2026-08-14）

# ---------- S1: 周五主信号→🥈出卡，stop_eff 精确=止损−0.3×ATR ----------
bars = make_bars()
set_bar(bars, I_FRI, 100, 100.5, 88, 94, 5000)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S1', bars, None)
exp_eff = round(88.0 - 0.3 * atr_at(bars, I_FRI), 2)
ok1 = (latest is not None and latest['day'] == '2026-10-02' and latest['grade'] == '🥈'
       and bool(latest.get('main')) and latest.get('stop_eff') == exp_eff
       and latest.get('stop_eff', 0) < latest['stop'])
check('S1 周五主信号🥈出卡+stop_eff=止损−0.3×ATR', ok1,
      f"grade={latest['grade'] if latest else None} stop_eff={latest.get('stop_eff') if latest else None} expect={exp_eff}")

# ---------- S2: 周六触轨（合格形态）→无卡、touch_days 仍计 ----------
bars = make_bars()
set_bar(bars, 50, 100, 100.5, 88, 94, 5000)   # 2026-10-03 周六
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S2', bars, None)
ok2 = (latest is None and '2026-10-03' in tdays
       and all(c['day'] != '2026-10-03' for c in cands))
check('S2 周六触轨→无卡+候选不入账+touch_days仍计', ok2,
      f"latest={latest is not None} in_touch={'2026-10-03' in tdays} cand_days={[c['day'] for c in cands]}")

# ---------- S3: 周日触轨→出卡、sun_half=True、score_of 减半 ----------
bars = make_bars()
set_bar(bars, 51, 100, 100.5, 88, 94, 5000)   # 2026-10-04 周日
set_bar(bars, 52, 94.2, 95, 93.8, 94.5, 1000)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S3', bars, None)
s_sun = rm.score_of('🥈', '常规', '无', '2026-10-04')
s_norm = rm.score_of('🥈', '常规', '无', '2026-10-02')
ok3 = (latest is not None and latest['day'] == '2026-10-04'
       and latest.get('sun_half') is True and '周日' in latest.get('note', '')
       and s_sun == round(s_norm * 0.5, 2))
check('S3 周日出卡+sun_half=True+score_of减半', ok3,
      f"sun_half={latest.get('sun_half') if latest else None} score周日={s_sun} score常规={s_norm}")

# ---------- S4: 下影≤40% 深CCI触轨→·（深度标签删除回归，无🥇） ----------
bars = make_bars()
set_bar(bars, I_FRI, 90, 95, 88, 94, 5000)   # cp=0.857>0.3, shadow=0.286≤0.4, CCI深
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S4', bars, None)
ok4 = (latest is not None and latest['grade'] == '·' and not latest.get('main')
       and latest.get('cci', 0) <= -175 and '🥇' not in str(latest.get('grade'))
       and '深度' not in str(latest))
check('S4 下影≤40%深CCI触轨→·无卡(深度标签删除回归)', ok4,
      f"grade={latest['grade'] if latest else None} main={latest.get('main') if latest else None} cci={latest.get('cci') if latest else None:.0f}" if latest else 'latest=None')

# ---------- S5: CCI≤−175+下影>40%→🥈（非🥇） ----------
bars = make_bars()
set_bar(bars, I_FRI, 100, 100.5, 88, 94, 5000)   # shadow=0.48>0.4, CCI≈-500
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S5', bars, None)
ok5 = (latest is not None and latest['grade'] == '🥈' and bool(latest.get('main'))
       and latest.get('cci', 0) <= -175 and '🥇' not in str(latest.get('grade')))
check('S5 CCI≤−175+下影>40%→🥈非🥇', ok5,
      f"grade={latest['grade'] if latest else None} cci={latest.get('cci') if latest else None:.0f}" if latest else 'latest=None')

# ---------- S6: 周五信号→周六确认破位→周日收上信号日EMA10−ATR→复活 ----------
bars = make_bars()
set_bar(bars, I_FRI, 100, 100.5, 88, 94, 5000)
set_bar(bars, I_FRI + 1, 88.0, 88.0, 84.0, 84.2, 1200)    # 周六 确认破位(瘫脚)
set_bar(bars, I_FRI + 2, 91.0, 99.0, 84.0, 98.5, 2000)    # 周日 收上信号区上沿
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S6', bars, None)
ok6 = latest is not None and '已收复' in latest.get('note', '') and '破位' not in (latest.get('warn') or '')
check('S6 确认破位→周日收上EMA10−ATR→复活(note含已收复)', ok6,
      f"note={latest.get('note') if latest else None}")

# ---------- S7: 确认破位后 2 日未收复→⚠️破位止损离场 ----------
bars = make_bars()
set_bar(bars, I_FRI, 100, 100.5, 88, 94, 5000)
set_bar(bars, I_FRI + 1, 93, 93.5, 79, 80, 3000)    # 周六 确认破位
set_bar(bars, I_FRI + 2, 80, 81, 73, 74, 2500)      # 周日
set_bar(bars, I_FRI + 3, 74, 75, 70, 71, 1000)      # 周一 (观察期第2日)
set_bar(bars, I_FRI + 4, 71, 72, 70, 71, 1000)      # 周二 期满→离场
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S7', bars, None)
c7 = next((c for c in cands if c['day'] == '2026-10-02'), None)
ok7 = ((latest is None or latest['day'] != '2026-10-02')
       and c7 is not None and '破位止损' in (c7.get('reason') or '')
       and c7.get('exit_date') == '2026-10-06')
check('S7 破位观察期满→⚠️破位止损离场(展示卡出清)', ok7,
      f"reason={c7.get('reason') if c7 else None} exit={c7.get('exit_date') if c7 else None}")

# ---------- S8: 信号后 31 天无事件→硬顶 30 天强制退出 ----------
bars = make_bars(n=85, tail_from=50)          # v1.7.21: cand_win=25≤49 准入；需 n≥i0+31 才能触发硬顶（原 79 根数据不足，属测试构造缺陷）
set_bar(bars, I_FRI, 100, 100.5, 88, 94, 5000)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('S8', bars, None)
c8 = next((c for c in cands if c['day'] == '2026-10-02'), None)
hit8 = c8 is not None and c8.get('reason') == '硬顶'
# 对照组：绕过 analyse 窗口门，直接调用 _simulate 验证机制本身
bars85 = make_bars(n=85, tail_from=50)
set_bar(bars85, I_FRI, 100, 100.5, 88, 94, 5000)
hi, lo, cl, vv, e10, at, cc, nn, dd = engine_arrays(bars85)
ed, ep, rs = rm._simulate(hi, lo, cl, vv, e10, at, cc, nn, dd, i0=I_FRI, ei=I_FRI + 1,
                          stop=88.0, dead=1e9, anchor=98.5, rec_ref=e10[I_FRI] - at[I_FRI])
ctrl8 = (rs == '硬顶' and ed == I_FRI + 30)
check('S8 信号后31天硬顶30天强制退出', hit8,
      f"analyse候选reason={c8.get('reason') if c8 else '候选缺失'}；对照:直接调用_simulate→{rs}@{dd[ed] if ed is not None else None}(机制{'正常' if ctrl8 else '异常'})")

# ---------- S9: render_html warn+sun_half 并存；st 无 skip_by_sym 不崩 ----------
try:
    st9 = {'ver': '1.7.20t', 'up_ts': '测试', 'market_banner': 'm', 'pool_n': 1, 'hit_n': 1,
           'warn': 1, 'n_closed': 0, 'n_open': 1, 'win': 0, 'avg': 0.0, 'cum': 0.0, 'hist_n': 0, 'hist_win': 0.0, 'hist_avg': 0.0, 'hist_med': 0.0}  # 故意无 skip_by_sym
    x9 = {'day': '2026-10-04', 'side': 'buy', 'grade': '🥈', 'main': True, 'anchor': 94.2,
          'zone': '[88.00~97.91]', 'cci': -400.0, 'warn': ' ⚠️破位10-05观察中', 'note': '',
          'haos': '', 'env': '无', 'stop': 88.0, 'stop_eff': 87.7, 'sun_half': True}
    cd9 = {'anchor': 94.2, 'stop': 88.0, 'reason': None}
    p9 = {'sym': 'S9', 'day': '2026-10-04', 'live_ret': 1.2, 'score': 0.8, 'anchor': 94.2,
          'stop': 88.0, 'tier': '轻仓', 'notional': 3.0, 'lev': 1.6}
    html9 = rm.render_html([(0, 'S9', x9, cd9, '常规', '轻仓', 0.8)], {'S9': 94.2}, [p9], st9)
    ok9 = ('🚫周日·降权0.5·复评中' in html9 and '⚠️' in html9
           and '#ff3b30' in html9 and '确认破位·2日观察期' in html9)
    check('S9 render_html 周日红标+⚠️并存且互不干扰；st缺skip_by_sym不崩', ok9)
except Exception as e:
    import traceback
    check('S9 render_html 周日红标+⚠️并存；st缺skip_by_sym不崩', False, f'异常 {e} {traceback.format_exc(limit=2)}')

# ---------- S10: 账本同标不重叠——开仓期间新候选 skip（经组合层 main 验证） ----------
s10 = make_bars()
set_bar(s10, I_FRI, 100, 100.5, 88, 94, 5000)            # 周五主信号(锚=次日开盘94)
for k in range(50, 60):
    s10[k] = dict(s10[k], **TAIL)                         # 尾段：首仓保持'在仓'
set_bar(s10, 50, 94, 99.3, 93.5, 98.8, 1200)             # 次日低开→止损距离6.4%可入账
set_bar(s10, 52, 97.2, 97.6, 96.0, 97.4, 2000)           # 周一二次触轨→同标第二候选(窗口重叠)
s10b = make_bars()
set_bar(s10b, 48, 100, 100.5, 88, 94, 5000)              # 10-01 触轨→垫高 T-1 触发数避免孤星禁入
POOL = ['S10', 'S10B'] + [f'D{k:02d}' for k in range(1, 11)]
BARS_MAP = {'S10': s10, 'S10B': s10b, **{s: make_bars() for s in POOL[2:]}}


class FakeClient:
    def __init__(self, **kw):
        pass

    def get_signals(self, *a, **k):
        return {'items': [{'symbol': s, 'name': '测试', 'underlying_type': 'EQUITY'} for s in POOL]}

    def get_kline(self, sym, *a, **k):
        return {'bars': BARS_MAP[sym]}


_, c10, _, _, _, _ = rm.analyse('S10', s10, None)
both_days = {'2026-10-02', '2026-10-05'} <= {c['day'] for c in c10}
cap = {}
_orig_render = rm.render_html


def _spy(rows, closes, open_pos, st):
    cap['rows'], cap['open_pos'], cap['st'] = rows, open_pos, st
    return _orig_render(rows, closes, open_pos, st)


rm.render_html = _spy
rm.KxClient = FakeClient
try:
    rm.main()
    st10 = cap.get('st') or {}
    sk = (st10.get('skip_by_sym') or {}).get('S10')
    opened = any(p['sym'] == 'S10' for p in cap.get('open_pos', []))
    ok10 = both_days and sk is not None and sk.get('n', 0) >= 1 and opened
    check('S10 同标不重叠：开仓期间新候选skip(组合层skip计数可见)', ok10,
          f"候选日={sorted({c['day'] for c in c10})} skip_by_sym.S10={sk} 在仓={[p['sym'] for p in cap.get('open_pos', [])]}")
except Exception as e:
    import traceback
    check('S10 同标不重叠', False, f'异常 {e} {traceback.format_exc(limit=2)}')
finally:
    rm.render_html = _orig_render

# ---------- 汇总 ----------
total = len(PASS) + len(FAIL)
print(f"\n===== 总通过率: {len(PASS)}/{total} =====")
if FAIL:
    print('失败项:', FAIL)
sys.exit(0 if not FAIL else 1)
