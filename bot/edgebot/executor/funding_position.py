"""ファンディングキャリーの建玉支援。

現物レッグ(MEXC)は自動発注、先物レッグは
  - MEXC 先物: API発注不可のため、必要な注文内容を表示して手動執行を促す
  - 将来: Gate 先物クライアントを足して自動化
という半自動から始める(エッジ検証を早く回すため)。

dry_run=True (デフォルト) は実データで注文内容を組み立てて表示するだけで発注しない。
"""

from __future__ import annotations

from ..config import CONFIG
from ..edges.funding_arb import annualize
from ..exchanges import mexc
from ..exchanges.mexc import MexcSpotClient
from .risk import check_order


def open_carry(symbol_fut: str, notional_usdt: float, live: bool = False) -> dict:
    """symbol_fut 例: BTC_USDT。正ファンディング前提: 現物ロング + 先物ショート。"""
    fr = mexc.futures_funding_rate(symbol_fut)
    rate = float(fr["fundingRate"])
    interval_h = float(fr.get("collectCycle", 8))
    if rate <= 0:
        raise RuntimeError(
            f"{symbol_fut} のファンディングは {rate:+.6f} で受取側が先物ロング。"
            "現物ショート不可のためこの形では組めない。")

    spot_symbol = symbol_fut.replace("_", "")
    book = mexc.spot_book_ticker(spot_symbol)
    limit_px = book["bid"]  # メイカー0%を活かして bid に置く
    qty = notional_usdt / limit_px

    edge_bps_per_settle = rate * 10_000
    check_order(notional_usdt, edge_bps_per_settle)

    plan = {
        "symbol": symbol_fut,
        "funding_rate": rate,
        "annualized_pct": round(annualize(rate, interval_h), 2),
        "spot_leg": {
            "venue": "MEXC spot", "side": "BUY", "type": "LIMIT_MAKER",
            "symbol": spot_symbol, "price": limit_px, "qty": qty,
        },
        "futures_leg": {
            "venue": "MEXC futures (手動) または Gate 先物", "side": "SELL(ショート)",
            "symbol": symbol_fut, "qty": qty,
            "note": "現物約定を確認してから同数量ショート。レバレッジは3倍以下推奨。",
        },
        "live": live,
    }

    if live:
        client = MexcSpotClient(CONFIG.mexc_api_key, CONFIG.mexc_api_secret)
        resp = client.new_order(spot_symbol, "BUY", "LIMIT_MAKER",
                                quantity=qty, price=limit_px)
        plan["spot_order_response"] = resp
    return plan
