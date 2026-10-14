#!/usr/bin/env python3
"""v1.7.15 合成场景测试 + 真实序列回归：
T1a 周五信号跨周末破位：周六确认破位→周日再破→离场（周末K线必须被状态机消费）
T1b 周五信号周末死区容忍：周六/周日收在死区内不破位，周一收复复活
T2  周六新信号下册：不出示、不入账本，但市况统计(touch_days)仍计入
T3  周日信号降权：卡片标注+score减半+有效止损字段
T4  卡片渲染含「有效止损」
T5  LRCX 真实序列回放（回归）
T6  新旧版本对比：真实标的全量候选仅移除周六，其余不受影响
"""
import importlib.util
import sys
from datetime import date, timedelta

sys.path.insert(0, '/tmp/kxhandover/pkg')
import replica_monitor as rm

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('✅' if cond else '❌'), name, detail)


def make_bars(start='2026-08-14', n=60):
    """前段平坦(价格100)，返回 bars 与 dates。"""
    d0 = date.fromisoformat(start)
    bars = []
    for k in range(n):
        d = d0 + timedelta(days=k)
        bars.append({'time': d.isoformat() + 'T00:00:00Z', 'open': 99.8, 'high': 100.5,
                     'low': 99.5, 'close': 100.0, 'volume': 1000})
    return bars, [str(b['time'])[:10] for b in bars]


def idx_of(dates, d):
    return dates.index(d)


def sig_bar(bars, i, o=100, h=100.5, l=88, c=94, v=5000):
    bars[i] = dict(bars[i], open=o, high=h, low=l, close=c, volume=v)


# ---------- T1a: 周五信号跨周末破位 ----------
bars, dates = make_bars()
i = idx_of(dates, '2026-10-02')            # 周五信号日
sig_bar(bars, i)                            # 长下影触轨
for j, (o, h, l, c, v) in {i+1: (93, 93.5, 79, 80, 3000),    # 周六 瘫脚深破
                           i+2: (80, 81, 73, 74, 2500),      # 周日 再破
                           i+3: (74, 75, 70, 71, 1000),      # 周一
                           i+4: (71, 72, 70, 71, 1000)}.items():
    bars[j] = dict(bars[j], open=o, high=h, low=l, close=c, volume=v)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('T1A', bars, None)
fri_gone = latest is None or latest['day'] != '2026-10-02'
fri_exit = any(c['day'] == '2026-10-02' and c.get('exit_day') is not None
               and '破位' in (c.get('reason') or '') for c in cands)
check('T1a 周五信号跨周末被状态机消费→已离场不再展示', fri_gone)
check('T1a 周五候选按破位口径退出(原因含破位)', fri_exit)

# ---------- T1b: 周末死区容忍 + 周一收复复活 ----------
bars, dates = make_bars()
i = idx_of(dates, '2026-10-02')
sig_bar(bars, i)
for j, (o, h, l, c, v) in {i+1: (88.0, 88.0, 84.0, 84.2, 1200),   # 周六 确认破位(瘫脚)
                           i+2: (91.0, 99.0, 84.0, 98.5, 2000),   # 周日 收上信号区上沿+大下影
                           i+3: (99.5, 100.2, 99.0, 99.8, 1000)}.items():
    bars[j] = dict(bars[j], open=o, high=h, low=l, close=c, volume=v)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('T1B', bars, None)
check('T1b 周六确认破位→周日收上信号区上沿→收复复活', latest is not None and '已收复' in latest.get('note', ''),
      f"note={latest.get('note') if latest else None} warn={latest.get('warn') if latest else None}")
check('T1b 复活后无破位警告', latest is not None and '破位' not in (latest.get('warn') or ''))

# ---------- T2: 周六新信号下册 ----------
bars, dates = make_bars()
i = idx_of(dates, '2026-10-03')            # 周六
sig_bar(bars, i)
bars[i+1] = dict(bars[i+1], open=94.2, high=95, low=93.8, close=94.5, volume=1000)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('T2', bars, None)
check('T2 周六信号不出示', latest is None)
check('T2 周六候选不入账本', all(c['day'] != '2026-10-03' for c in cands))
check('T2 周六触及仍计入市况统计(touch_days)', '2026-10-03' in tdays)

# ---------- T3: 周日信号降权 + 有效止损 ----------
bars, dates = make_bars()
i = idx_of(dates, '2026-10-04')            # 周日
sig_bar(bars, i)
bars[i+1] = dict(bars[i+1], open=94.2, high=95, low=93.8, close=94.5, volume=1000)
latest, cands, tdays, lc, dset, _sbd = rm.analyse('T3', bars, None)
check('T3 周日信号正常出示', latest is not None and latest['day'] == '2026-10-04')
check('T3 卡片标注周日降权', latest is not None and '周日信号·权重0.5' in latest.get('note', ''))
import numpy as np
_hi = np.array([b['high'] for b in bars]); _lo = np.array([b['low'] for b in bars])
_cl = np.array([b['close'] for b in bars])
_tr = np.concatenate([[_hi[0]-_lo[0]], np.maximum(_hi[1:], _cl[:-1]) - np.minimum(_lo[1:], _cl[:-1])])
_atr_i = _tr[i-14:i].mean()
expect_eff = round(88.0 - 0.3*_atr_i, 2)
check('T3 有效止损=止损−0.3×ATR', latest is not None and latest.get('stop_eff') == expect_eff,
      f"stop_eff={latest.get('stop_eff')} expect={expect_eff}")
check('T3 score_of 周日层减半', rm.score_of('🥈', '常规', '无', '2026-10-04') == 0.8,
      f"got={rm.score_of('🥈', '常规', '无', '2026-10-04')}")
check('T3 score_of 其他日不受影响', rm.score_of('🥈', '常规', '无', '2026-10-02') == 1.6)
check('T3 sun_half 旗标已置位', latest is not None and latest.get('sun_half') is True)
# T4b：红色标注在标签位、且不占用破位/有效止损文本
try:
    st = {'ver': '1.7.15b', 'up_ts': '测试', 'market_banner': 'm', 'pool_n': 1,
          'hit_n': 1, 'g1': 0, 'warn': 0, 'n_closed': 0, 'n_open': 0, 'win': 0, 'cum': 0.0, 'avg': 0.0, 'hist_n': 0, 'hist_win': 0.0, 'hist_avg': 0.0, 'hist_med': 0.0}
    latest2 = dict(latest); latest2['warn'] = ' ⚠️破位10-12观察中'   # 模拟周日+破位并存
    _cd = {'anchor': latest2['anchor'], 'stop': latest2['stop'], 'reason': None}
    rows2 = [(1, 'T3', latest2, _cd, '常规', '轻仓', 0.8)]
    html2 = rm.render_html(rows2, {}, [], st)
    _miss = [t for t in ('🚫周日·降权0.5·复评中', '#ff3b30', '⚠️主信号', '确认破位·2日观察期') if t not in html2]
    check('T4b 红色🚫标注与破位⚠️并存（标签位独立渲染）', not _miss, f'缺失={_miss}')
except Exception as e:
    check('T4b 红色标注渲染', False, f'异常 {e}')

# ---------- T4: 卡片渲染含有效止损 ----------
try:
    st = {'ver': '1.7.15', 'up_ts': '测试', 'market_banner': 'm', 'pool_n': 1,
          'hit_n': 1, 'g1': 0, 'warn': 0, 'n_closed': 0, 'n_open': 0, 'win': 0, 'cum': 0.0, 'avg': 0.0, 'hist_n': 0, 'hist_win': 0.0, 'hist_avg': 0.0, 'hist_med': 0.0}

    rows = [(1, 'T3', latest, None, '常规', '轻仓', 0.8)]
    html_out = rm.render_html(rows, {}, [], st)
    check('T4 卡片渲染含「有效止损」字段', '有效止损' in html_out and str(latest['stop_eff']) in html_out)
except Exception as e:
    check('T4 卡片渲染', False, f'异常 {e}')

# ---------- T5: LRCX 真实序列回放 ----------
from kx_client import KxClient
cli = KxClient()
d = cli.get_kline('LRCXUSDT', 'futures', '1d', 300)
lb = d.get('bars') or []
latest, cands, tdays, lc, dset, _sbd = rm.analyse('LRCXUSDT', lb, None)
check('T5 LRCX 展示信号仍为 10-07(周三) 且带破位观察',
      latest is not None and latest['day'] == '2026-10-07' and '破位' in (latest.get('warn') or ''))
check('T5 LRCX 有效止损字段存在且低于显示止损',
      latest is not None and isinstance(latest.get('stop_eff'), float) and latest['stop_eff'] < latest['stop'])
check('T5 LRCX 候选不含周六信号', all(rm._wd(c['day']) != 5 for c in cands))

# ---------- T6: 新旧版本全量候选对比（3 个真实标的） ----------
import shutil
shutil.copy('/tmp/kxhandover/replica_monitor_v1714.py.bak', '/tmp/kxhandover/rm_old_v1714.py')
spec = importlib.util.spec_from_file_location('rm_old', '/tmp/kxhandover/rm_old_v1714.py')
rm_old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rm_old)
for sym in ['LRCXUSDT', 'CXMTUSDT', 'DRAMUSDT', 'KORUUSDT']:
    try:
        b = (cli.get_kline(sym, 'futures', '1d', 300).get('bars') or [])
        if len(b) < 40:
            continue
        lo_sig, lo_c, _, _, _ = rm_old.analyse(sym, b, None)
        ne_sig, ne_c, _, _, _, _ = rm.analyse(sym, b, None)
        old_days = {c['day'] for c in lo_c}
        new_days = {c['day'] for c in ne_c}
        removed = old_days - new_days
        added = new_days - old_days
        import datetime as _dt
        def _age_gt30(x):
            return (_dt.date(2026,10,12) - _dt.date(int(x[:4]), int(x[5:7]), int(x[8:10]))).days > 30
        check(f'T6 {sym} 候选仅移除「周六∪超30天龄」(移除{len(removed)}个/新增{len(added)}个)',
              all(rm._wd(x) == 5 or _age_gt30(x) for x in removed) and not added,
              f"removed={sorted(removed)[:4]}")
        old_disp = lo_sig['day'] if lo_sig else None
        new_disp = ne_sig['day'] if ne_sig else None
        ok_disp = (new_disp == old_disp) or (old_disp is not None and rm._wd(old_disp) == 5)
        check(f'T6 {sym} 展示信号不受周六下册影响(或原展示即周六)', ok_disp, f'{old_disp}→{new_disp}')
    except Exception as e:
        check(f'T6 {sym}', False, f'异常 {e}')

print(f"\n===== 结果: {len(PASS)} 过 / {len(FAIL)} 败 =====")
if FAIL:
    print('失败项:', FAIL)
    sys.exit(1)
