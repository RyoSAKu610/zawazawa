"""エッジ計測の共通型とユーティリティ。"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, asdict


@dataclass
class EdgeResult:
    """1件の計測結果。net_edge_bps が正 = 手数料控除後も歪みが残っている。"""

    edge: str                      # エッジ種別 (funding_arb 等)
    instrument: str                # 対象 (BTCUSDT 等)
    net_edge_bps: float            # 手数料等控除後のエッジ (basis points)
    gross_edge_bps: float          # 控除前
    direction: str                 # 取るべき方向の説明
    annualized_pct: float | None = None  # 年率換算 (キャリー系のみ)
    executable: bool = True        # 現状の口座/API制約で自動執行可能か
    notes: str = ""
    details: dict = field(default_factory=dict)
    ts: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return asdict(self)


def vwap_fill(levels: list[list[float]], notional: float) -> tuple[float, float] | None:
    """板 levels ([[price, qty],...]) を notional (quote建て) ぶん食った場合の
    平均約定価格と充足率を返す。板が足りなければ None。
    """
    remaining = notional
    cost = 0.0
    qty_total = 0.0
    for price, qty in levels:
        level_notional = price * qty
        take = min(remaining, level_notional)
        cost += take
        qty_total += take / price
        remaining -= take
        if remaining <= 1e-12:
            break
    if remaining > 1e-9 or qty_total <= 0:
        return None
    return cost / qty_total, 1.0


def bps(x: float) -> float:
    return x * 10_000.0
