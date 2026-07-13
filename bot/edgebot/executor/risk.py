"""発注前リスクチェック。全ての実発注はここを通す。"""

from __future__ import annotations

import os

from ..config import CONFIG


class RiskRejected(RuntimeError):
    pass


def check_order(notional_usdt: float, edge_bps: float, open_notional_usdt: float = 0.0) -> None:
    """違反があれば RiskRejected を投げる。"""
    if os.environ.get("EDGEBOT_KILL_SWITCH") == "1":
        raise RiskRejected("EDGEBOT_KILL_SWITCH=1 のため全発注停止中")
    if notional_usdt <= 0:
        raise RiskRejected("notional が 0 以下")
    if notional_usdt > CONFIG.max_order_notional_usdt:
        raise RiskRejected(
            f"1注文上限超過: {notional_usdt:.2f} > {CONFIG.max_order_notional_usdt:.2f} USDT")
    if open_notional_usdt + notional_usdt > CONFIG.max_total_notional_usdt:
        raise RiskRejected(
            f"総建玉上限超過: {open_notional_usdt + notional_usdt:.2f} > "
            f"{CONFIG.max_total_notional_usdt:.2f} USDT")
    if edge_bps < CONFIG.min_edge_bps_to_execute:
        raise RiskRejected(
            f"エッジ不足: {edge_bps:.2f}bps < 最低 {CONFIG.min_edge_bps_to_execute:.2f}bps")
