#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.7.21 硬顶修复边界场景测试（3 个边界场景 + 展示层探针，纯合成K线，零网络依赖）

修复语义：候选扫描窗 n−HARD_CAP → n−2×HARD_CAP（三处准入），硬顶退出 j−i0≥30 恢复可达；
30-60 天龄信号以「硬顶退出」closed 入账本。

E1a 信号恰在扫描窗边界（i0 = cand_win = n−2×HARD_CAP）→ 准入，且最终「硬顶」退出（j−i0=30 可达）
E1b 信号在扫描窗外 1 根（i0 = cand_win−1）→ 不准入（无该候选 / 不展示 / touch_days 不计）
E1c 30-60天龄信号硬顶退出入账后 → 同标占位释放：窗口内新信号正常开仓入账，同标 skip 计数为 0
E2  展示层边界：i0 < cand_win（龄≥60 天）不可能成为 latest；扫描窗边界内老信号可占展示位（事实探针）
"""
import os
import sys
from datetime import date, timedelta

os.environ.pop('KX_GH_TOKEN', None)
sys.path.insert(0, '/tmp/kxhandover/pkg')
import replica_monitor as rm

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('✅' if cond else '❌'), name, ('| ' + detail) if detail else '')


FLAT = dict(open=99.8, high=100.5, low=99.5, close=100.0, volume=1000)
TAIL = dict(open=98.5, high=99.3, low=97.5, close=98.8, volume=1000)   # 不触✅/不破位（high 99.3 < dead≈99.9）


def make_bars(start='2026-08-14', n=85):
    d0 = date.fromisoformat(start)
    return [{'time': (d0 + timedelta(days=k)).isoformat() + 'T00:00:00Z', **FLAT}
            for k in range(n)]


def set_bar(bars, i, **kw):
    bars[i] = dict(bars[i], **kw)


def sig_bar(bars, i):
    """标准主信号：触下轨+下影48%+cp 0.48（走普通路径非 G 路径）。"""
    set_bar(bars, i, open=100, high=100.5, low=88, close=94, volume=5000)


def dates_of(bars):
    return [str(b['time'])[:10] for b in bars]


N = 85                       # cand_win = 85 − 2×30 = 25
CW = N - 2 * rm.HARD_CAP     # 25

# ================= E1a: 信号恰在扫描窗边界 i0 = cand_win =================
bars = make_bars(n=N)
for k in range(CW + 1, N):   # 尾段 TAIL：不触✅/不破位 → 让硬顶成为唯一退出
    bars[k] = dict(bars[k], **TAIL)
sig_bar(bars, CW)            # 2026-09-08 周二，恰在扫描窗边界
D = dates_of(bars)
latest_a, cands_a, tdays_a, _, _, _ = rm.analyse('E1A', bars, None)
c_a = next((c for c in cands_a if c['day'] == D[CW]), None)
ok_a = (c_a is not None and c_a.get('reason') == '硬顶'
        and c_a.get('exit_day') == CW + rm.HARD_CAP and c_a.get('exit_date') == D[CW + rm.HARD_CAP]
        and len(cands_a) == 1 and rm._wd(D[CW]) not in (5, 6))
check('E1a 信号恰在扫描窗边界(i0=cand_win=25)→准入且硬顶退出(j−i0=30)',
      ok_a,
      f"day={D[CW]}({['周一','周二','周三','周四','周五','周六','周日'][rm._wd(D[CW])]}) "
      f"reason={c_a.get('reason') if c_a else '候选缺失'} exit={c_a.get('exit_date') if c_a else None} "
      f"n_cands={len(cands_a)}；注：旧版窗 n−30=55 下该信号必被排除(25<55)")

# ================= E1b: 信号在扫描窗外 1 根 i0 = cand_win − 1 =================
bars = make_bars(n=N)
sig_bar(bars, CW - 1)        # 2026-09-07 周一，窗外 1 根（排除原因只能是窗口，非周六）
latest_b, cands_b, tdays_b, _, _, _ = rm.analyse('E1B', bars, None)
ok_b = (len(cands_b) == 0 and latest_b is None and D[CW - 1] not in tdays_b
        and rm._wd(D[CW - 1]) == 0)
check('E1b 信号在扫描窗外1根(i0=cand_win−1=24)→不准入(无候选/无展示/touch_days不计)',
      ok_b,
      f"day={D[CW-1]}(周一) n_cands={len(cands_b)} latest={latest_b is not None} in_touch={D[CW-1] in tdays_b}")

# ================= E2: 展示层边界 =================
# E2a: ≥60天龄（i0 < cand_win）不可能成为 latest —— 直接复用 E1b 的 latest=None
check('E2a 龄≥60天(i0<cand_win)老信号不可能出现在展示位(latest=None)', latest_b is None,
      f"latest={'None' if latest_b is None else latest_b['day']}")
# E2b: v1.7.21(🟠1) 新语义——展示窗=硬顶窗：龄>30天的信号不上展示卡（它们必然已硬顶出清）
age_a = (N - 1) - CW
ok_e2b = latest_a is None or (N - 1) - 0 <= 99  # 占位；真实断言如下行
ok_e2b = latest_a is None or age_a <= 30
check('E2b 展示窗=硬顶窗：龄>30天信号不上展示(窗内59天龄信号已被展示层过滤)',
      latest_a is None, f"latest={latest_a['day'] if latest_a else None}(期望None,信号龄{age_a}天>30)")

# ================= E1c: 硬顶退出后同标占位释放（组合层 main 验证） =================
I_OLD, I_NEW = 32, 66        # 旧信号 09-15(周二) → 硬顶退出 10-15(idx62)；新信号 10-19(周一) 退出后开仓
ENTRY = dict(open=94, high=99.3, low=93.5, close=98.8, volume=1200)   # 次日低开→止损距离6.4%≤8%可入账


def e1c_bars():
    bars = make_bars(n=N)
    for k in range(I_OLD + 2, N):
        bars[k] = dict(bars[k], **TAIL)
    sig_bar(bars, I_OLD)
    set_bar(bars, I_OLD + 1, **ENTRY)
    sig_bar(bars, I_NEW)     # 覆盖 TAIL → 触轨信号（band≈96~97 < low 88 ✓）
    set_bar(bars, I_NEW + 1, **ENTRY)
    return bars


D3 = dates_of(e1c_bars())
latest_c, cands_c, _, _, _, _ = rm.analyse('S10C', e1c_bars(), None)
c_old = next((c for c in cands_c if c['day'] == D3[I_OLD]), None)
c_new = next((c for c in cands_c if c['day'] == D3[I_NEW]), None)
ok_pre = (c_old is not None and c_old.get('reason') == '硬顶' and c_old.get('exit_date') == D3[I_OLD + 30]
          and c_new is not None and c_new.get('reason') == '在仓' and c_new.get('exit_day') is None
          and latest_c is not None and latest_c['day'] == D3[I_NEW])
check('E1c-前置 旧信号(32)硬顶退出@62 + 新信号(66)在仓 + 展示位=新信号',
      ok_pre,
      f"old={c_old.get('reason') if c_old else '缺失'}@{c_old.get('exit_date') if c_old else '-'} "
      f"new={c_new.get('reason') if c_new else '缺失'} latest={latest_c['day'] if latest_c else None}")

# 垫角标：F1 触轨@31（旧信号 T-1 触发数≥1 避免孤星禁入）；F2 触轨@65（新信号 T-1）
f1 = make_bars(n=N); sig_bar(f1, 31)
f2 = make_bars(n=N); sig_bar(f2, 65)
POOL = ['S10C', 'F1', 'F2'] + [f'D{k:02d}' for k in range(1, 10)]
BARS_MAP = {'S10C': e1c_bars(), 'F1': f1, 'F2': f2, **{s: make_bars(n=60) for s in POOL[3:]}}


class FakeClient:
    def __init__(self, **kw):
        pass

    def get_signals(self, *a, **k):
        return {'items': [{'symbol': s, 'name': '测试', 'underlying_type': 'EQUITY'} for s in POOL]}

    def get_kline(self, sym, *a, **k):
        return {'bars': BARS_MAP[sym]}


cap = {}
_orig_render = rm.render_html


def _spy(rows, closes, open_pos, st):
    cap['rows'], cap['open_pos'], cap['st'] = rows, open_pos, st
    return _orig_render(rows, closes, open_pos, st)


rm.render_html = _spy
rm.KxClient = FakeClient
try:
    rm.main()
    st = cap.get('st') or {}
    open_syms = [p['sym'] for p in cap.get('open_pos', [])]
    sk = (st.get('skip_by_sym') or {}).get('S10C')
    ok_c = ('S10C' in open_syms and sk is None and (st.get('n_closed') or 0) >= 1)
    check('E1c 老信号硬顶退出→占位释放：新信号正常开仓入账、同标skip=0、账本有已平仓',
          ok_c,
          f"在仓={open_syms} skip_by_sym.S10C={sk} n_closed={st.get('n_closed')}")
except Exception as e:
    import traceback
    check('E1c 老信号硬顶退出→占位释放', False, f'异常 {e} {traceback.format_exc(limit=2)}')
finally:
    rm.render_html = _orig_render

# ================= 汇总 =================
total = len(PASS) + len(FAIL)
print(f"\n===== 边界场景: {len(PASS)}/{total} =====")
if FAIL:
    print('失败项:', FAIL)
sys.exit(0 if not FAIL else 1)
