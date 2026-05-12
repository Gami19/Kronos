"""webui/backtest_v1 — v1.0 open-to-open の純粋ロジック検証"""

import sys
from pathlib import Path

import pytest

_WEBUI = Path(__file__).resolve().parent.parent / "webui"
if str(_WEBUI) not in sys.path:
    sys.path.insert(0, str(_WEBUI))

from backend.lib.backtest_v1 import (  # noqa: E402
    first_signal_bar_index,
    long_at_open,
    max_drawdown_from_equity,
    simulate_v1_ooh_strategy_bh,
)


def test_max_drawdown_monotonic_decline():
    eq = [1.0, 0.9, 0.81]
    assert max_drawdown_from_equity(eq) == pytest.approx(0.19)


def test_first_signal_index():
    assert first_signal_bar_index([None, None, True]) == 2
    assert first_signal_bar_index([None, None, None]) == 3


def test_ooh_bh_two_steps_constant_return():
    # O0=100, O1=110, O2=121 → r0=r1=0.1
    opens = [100.0, 110.0, 121.0]
    want = [False, False]  # padded: need len >= n for indexing; use list of len 3
    want3: list = [False, False, None]
    s, b, _, m = simulate_v1_ooh_strategy_bh(opens, 0, 1, want3)
    assert s[-1] == pytest.approx(1.0)
    assert b[-1] == pytest.approx(1.1 * 1.1)
    assert m["bh_cumulative_return"] == pytest.approx(0.21)
    assert m["strategy_cumulative_return"] == pytest.approx(0.0)


def test_strategy_follows_signal_once():
    opens = [100.0, 110.0, 121.0]
    # バー0終了後に次 open でロング → バー1の始値から r1 を取る
    want = [True, False, None]
    s, b, labels, m = simulate_v1_ooh_strategy_bh(opens, 0, 1, want)
    assert long_at_open(0, want, first_signal_bar_index(want)) is False
    assert long_at_open(1, want, first_signal_bar_index(want)) is True
    assert s[-1] == pytest.approx(1.1)  # 最初の r のみ現金、2本目で 10%
    assert b[-1] == pytest.approx(1.21)
    assert len(labels) == 2


def test_trade_count_toggle():
    opens = [10.0, 11.0, 12.0, 13.0]
    want = [True, False, True, None]
    _, _, _, m = simulate_v1_ooh_strategy_bh(opens, 0, 2, want)
    # open0 cash, open1 long, open2 cash, open3 long → 3 transitions among 0..3
    assert m["trade_count"] == 3
