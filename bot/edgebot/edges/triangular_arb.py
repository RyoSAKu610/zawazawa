"""エッジ4: MEXC 内 三角アビトラ。

USDT -> X -> Y -> USDT の3脚。単一取引所内なので送金リスクなし。
メジャー所ではほぼ消えたエッジだが、MEXC はロングテール銘柄が多く
メイカー0%なので、指値ベースなら稀に残る。スキャンはテイカー前提の保守的計測。
"""

from __future__ import annotations

from itertools import combinations

from ..config import CONFIG
from ..exchanges import mexc
from .base import EdgeResult, bps


def scan(top: int = 15, min_net_bps: float = -5.0) -> list[EdgeResult]:
    books = mexc.spot_book_tickers()
    fee = CONFIG.mexc_spot_taker

    # 通貨グラフ構築: symbol は BASE+QUOTE 連結表記なので、USDT/BTC/ETH クオートで分解
    quotes = ("USDT", "USDC", "BTC", "ETH")
    pairs: dict[tuple[str, str], dict] = {}
    for sym, b in books.items():
        for q in quotes:
            if sym.endswith(q) and len(sym) > len(q):
                base = sym[: -len(q)]
                pairs[(base, q)] = b
                break

    # USDT 起点の三角形: USDT -> base(X) -> quote2 経由 -> USDT
    usdt_bases = {b for (b, q) in pairs if q == "USDT"}
    bridge_quotes = [q for q in ("BTC", "ETH", "USDC") if (q, "USDT") in pairs]

    results: list[EdgeResult] = []
    for x in usdt_bases:
        for q2 in bridge_quotes:
            if (x, q2) not in pairs or x == q2:
                continue
            px_x_usdt = pairs[(x, "USDT")]
            px_x_q2 = pairs[(x, q2)]
            px_q2_usdt = pairs[(q2, "USDT")]
            if min(px_x_usdt["ask"], px_x_q2["bid"], px_q2_usdt["bid"]) <= 0:
                continue

            # 経路: USDT で X を買う -> X を q2 建てで売る -> q2 を USDT で売る
            amount = (1.0 / px_x_usdt["ask"]) * (1 - fee)
            amount = amount * px_x_q2["bid"] * (1 - fee)
            amount = amount * px_q2_usdt["bid"] * (1 - fee)
            net = bps(amount - 1.0)
            if net < min_net_bps:
                continue
            results.append(EdgeResult(
                edge="triangular_arb",
                instrument=f"USDT->{x}->{q2}->USDT",
                net_edge_bps=round(net, 2),
                gross_edge_bps=round(net + bps(3 * fee), 2),
                direction="3脚同時テイク (要低レイテンシ)",
                executable=True,
                notes="best気配ベース。執行時は3脚の板深さとレイテンシで大半が消えるため要WS化。",
                details={
                    "legs": {
                        f"{x}USDT.ask": px_x_usdt["ask"],
                        f"{x}{q2}.bid": px_x_q2["bid"],
                        f"{q2}USDT.bid": px_q2_usdt["bid"],
                    },
                },
            ))

    results.sort(key=lambda r: r.net_edge_bps, reverse=True)
    return results[:top]
