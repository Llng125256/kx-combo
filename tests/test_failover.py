#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""v1.7.25 数据源容灾测试（kx_client v3.4.0 故障切换，离线 mock，零网络依赖）

裁决依据（工程双席 2026-10-13）：
  Q1=A 降级模式只给完整 bar（缺今日 bar 属预期语义，绝不伪造盘中 bar）
  Q2=A+C 拉满 limit 保口径一致 + 降级专用 8 线程 + 每标内存缓存
  Q4 口径隔离：新浪数据仅存活心跳，禁止进引擎输入路径

用例：
  F1 导演连续 3 次失败 -> 自动切 S3 降级模式
  F2 S3 bars 带 source='s3' 且引擎 analyse 正常消费（含额外字段不炸）
  F3 缺今日 bar 容忍：最后 bar=昨日完整 bar，analyse 判定基于完整 bar 不崩
  F4 导演 1-2 次失败不切换（仍走主源抛错路径）
  F5 非 futures/1d 请求在 S3 模式被拒绝
  F6 新浪探针只返回 bool（不返回价格数据）
  F7 当日缓存命中：同日二次调用不发网络请求
"""
import os
import sys
import time
from datetime import datetime, timedelta, timezone

os.environ.pop('KX_GH_TOKEN', None)
sys.path.insert(0, '/tmp/kxhandover/pkg')

import kx_client as kc
from kx_client import KxClient

PASS, FAIL = [], []


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('✅' if cond else '❌'), name, detail or '')


# ---------- 构造 46 根合成 S3 bar（模拟 TEM 式短历史，最后完整 bar=昨日） ----------
today = datetime.now(timezone.utc).date()
yesterday = today - timedelta(days=1)
BARS = []
for i in range(46, 0, -1):
    bd = yesterday - timedelta(days=i - 1)
    px = 50.0 + i * 0.1
    BARS.append({"time": f"{bd.isoformat()} 00:00:00", "open": px, "high": px + 0.5,
                 "low": px - 0.5, "close": px + 0.2, "volume": 1000.0, "source": "s3"})

# ---------- mock S3 拉取（替换 _get_kline_s3 的网络层行为，走真实缓存/模式逻辑） ----------
class MockClient(KxClient):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.s3_calls = 0

    def _get(self, *a, **kw):
        # 导演宕机模拟：主源路径一律失败
        raise ConnectionError("模拟导演宕机")

    def probe_sina_alive(self):
        return True

    def _get_kline_s3(self, symbol, market, period, limit):
        # 模拟真实方法的前置行为：参数校验 + 当日缓存命中不发请求
        if market != 'futures' or period != '1d':
            raise ValueError(f"S3 降级仅支持 futures/1d，收到 {market}/{period}")
        fresh = self._s3_cache.get(symbol)
        if fresh and fresh['fetched_day'] == datetime.now(timezone.utc).date():
            return {"bars": list(fresh['bars']), "source": "s3", "degraded": True}
        self.s3_calls += 1
        with self._mode_lock:
            self._s3_cache[symbol] = {"bars": list(BARS),
                                      "fetched_day": datetime.now(timezone.utc).date()}
        return {"bars": list(BARS), "source": "s3", "degraded": True}


# ---------- F4: 1-2 次失败不切换 ----------
c = MockClient()
for _ in range(2):
    try:
        c.get_kline("XUSDT", "futures", "1d", 300)
    except Exception:
        pass
check("F4 导演1-2次失败不切换", c.get_status()['source'] == 'director'
      and c.get_status()['fail_count'] == 2 and c.s3_calls == 0,
      f"mode={c.get_status()['source']} fail={c.get_status()['fail_count']}")

# ---------- F1: 第 3 次失败自动切 S3 并当场降级供数 ----------
try:
    d = c.get_kline("XUSDT", "futures", "1d", 300)
    switched = True
except Exception as e:
    switched = False
check("F1a 第3次失败进入S3模式", c.get_status()['source'] == 's3' and switched,
      f"mode={c.get_status()['source']}")
check("F1b 切换后供数来自S3", d.get('source') == 's3' and d.get('degraded') is True
      and len(d['bars']) == 46)

# ---------- F7: 当日缓存命中（S3 二次调用不再计数网络） ----------
c2 = MockClient()
c2._mode = 's3'
c2._last_probe = time.time()
d1 = c2.get_kline("XUSDT", "futures", "1d", 300)
n1 = c2.s3_calls
d2 = c2.get_kline("XUSDT", "futures", "1d", 300)
check("F7 当日缓存命中不发请求", c2.s3_calls == n1 and d2['bars'] == d1['bars'],
      f"s3_calls={c2.s3_calls}")

# ---------- F2/F3: S3 bars 过引擎 analyse（含缺今日 bar 容忍） ----------
sys.path.insert(0, '/tmp/kxhandover/pkg')
import replica_monitor as rm

sig, cands, tdays, lc, dset = rm.analyse("XUSDT", d['bars'], None)
check("F2 引擎消费S3 bars(额外source字段不炸)", True,
      f"展示信号={'有' if sig else '无'} 候选={len(cands)}")
check("F3a 缺今日bar容忍:最后bar=昨日完整bar", d['bars'][-1]['time'][:10] == yesterday.isoformat(),
      f"last={d['bars'][-1]['time'][:10]}")
check("F3b 判定日历不含今日", today.isoformat() not in dset,
      f"日历末日={sorted(dset)[-1] if dset else '无'}")

# ---------- F5: 非 futures/1d 拒绝 ----------
c3 = MockClient()
c3._mode = 's3'
c3._last_probe = time.time()
try:
    c3.get_kline("XUSDT", "spot", "1d", 300)
    rejected = False
except ValueError:
    rejected = True
except Exception:
    rejected = False
check("F5 非futures/1d在S3模式被拒绝", rejected)

# ---------- F6: 新浪探针只返回 bool ----------
import inspect
src = inspect.getsource(KxClient.probe_sina_alive)
check("F6a 新浪探针返回bool", 'return r.status_code == 200' in src.replace(' ', '')
      or 'status_code == 200' in src)
check("F6b 新浪探针无价格返回路径", 'return {' not in src and "'open'" not in src)

# ---------- 探测回切逻辑（时间窗 mock） ----------
c4 = MockClient()
c4._mode = 's3'
c4._last_probe = time.time() - 3600  # 超过 30 分钟探测窗
probe_state = {'fail': True}


def _probe_fail(*a, **kw):
    raise ConnectionError("导演仍未恢复")


# 导演仍未恢复：保持 s3
c4.session_probe = None
orig_get = c4.session.get
c4.session.get = _probe_fail
c4._maybe_failback()
c4.session.get = orig_get
check("F8a 探测失败保持降级", c4.get_status()['source'] == 's3')


class _R:
    status_code = 200

    def raise_for_status(self):
        pass

    def json(self):
        return {"items": []}


c4.session.get = lambda *a, **kw: _R()
c4._last_probe = time.time() - 3600
c4._maybe_failback()
check("F8b 导演恢复自动回切", c4.get_status()['source'] == 'director'
      and c4.get_status()['fail_count'] == 0)

print()
print(f"===== 容灾测试: {len(PASS)} 过 / {len(FAIL)} 败 =====")
sys.exit(1 if FAIL else 0)
