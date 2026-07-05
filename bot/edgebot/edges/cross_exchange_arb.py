"""エッジ3: 取引所間 現物アビトラ (MEXC vs Gate / Bybit)。

両取引所に在庫を置き、bid/ask がクロスした瞬間に両側同時テイク。
送金はせず、在庫リバランスは乖離が逆転した時に自然に戻るのを待つ(定番の在庫戦略)。

計測: 全共通ペアについて (A の bid) − (B の ask) を両方向で計算し、
双方のテイカー手数料を控除したネットエッジを出す。
"""

from __future__ import annotations

from ..config import CONFIG
from ..exchanges import bybit, gate, mexc
from .base import EdgeResult, bps

MIN_GROSS_BPS = 1.0  # ノイズ除去


def scan(top: int = 20) -> list[EdgeResult]:
    mexc_books = mexc.spot_book_tickers()
    venues: dict[str, dict[str, dict]] = {}
    try:
        venues["gate"] = {p.replace("_", ""): v for p, v in gate.spot_tickers().items()}
    except Exception:
        pass
    try:
        venues["bybit"] = bybit.spot_tickers()
    except Exception:
        pass

    fees = {
        "gate": CONFIG.gate_spot_taker,
        "bybit": CONFIG.bybit_spot_taker,
    }
    mexc_fee = CONFIG.mexc_spot_taker

    results: list[EdgeResult] = []
    for venue, books in venues.items():
        common = mexc_books.keys() & books.keys()
        for sym in common:
            if not sym.endswith("USDT"):
                continue
            m, o = mexc_books[sym], books[sym]
            if min(m["bid"], m["ask"], o["bid"], o["ask"]) <= 0:
                continue
            # 方向A: MEXCで買って venue で売る
            gross_a = (o["bid"] - m["ask"]) / m["ask"]
            # 方向B: venue で買って MEXC で売る
            gross_b = (m["bid"] - o["ask"]) / o["ask"]
            fee_total = mexc_fee + fees[venue]

            for gross, direction in ((gross_a, f"MEXC買い→{venue}売り"),
                                     (gross_b, f"{venue}買い→MEXC売り")):
                gross_bps = bps(gross)
                if gross_bps < MIN_GROSS_BPS:
                    continue
                net = gross_bps - bps(fee_total)
                results.append(EdgeResult(
                    edge="cross_exchange_arb",
                    instrument=sym,
                    net_edge_bps=round(net, 2),
                    gross_edge_bps=round(gross_bps, 2),
                    direction=direction,
                    executable=True,
                    notes="両側在庫前提・同時テイク。best気配のみの計測なのでサイズは板で要確認。",
                    details={
                        "mexc": m, f"{venue}": o,
                        "taker_fee_total_bps": round(bps(fee_total), 2),
                    },
                ))

    results.sort(key=lambda r: r.net_edge_bps, reverse=True)
    return results[:top]
