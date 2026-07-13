"""Gate.io アダプタ (公開API)。https://api.gateio.ws/api/v4

MEXC 先物発注APIが使えない場合の先物レッグ先、および取引所間アビトラの対向として使う。
"""

from __future__ import annotations

from ..http import get_json

BASE = "https://api.gateio.ws/api/v4"


def spot_tickers() -> dict[str, dict]:
    """通貨ペア -> {bid, ask}。ペア表記は BTC_USDT 形式。"""
    rows = get_json(f"{BASE}/spot/tickers")
    out = {}
    for r in rows:
        try:
            bid, ask = float(r["highest_bid"]), float(r["lowest_ask"])
        except (KeyError, ValueError, TypeError):
            continue
        if bid > 0 and ask > 0:
            out[r["currency_pair"]] = {"bid": bid, "ask": ask}
    return out


def futures_contracts() -> list[dict]:
    """USDT建て無期限の全契約。funding_rate / funding_interval を含む。"""
    return get_json(f"{BASE}/futures/usdt/contracts")


def futures_ticker(contract: str) -> dict:
    rows = get_json(f"{BASE}/futures/usdt/tickers", {"contract": contract})
    return rows[0] if rows else {}


def spot_order_book(pair: str, limit: int = 20) -> dict:
    r = get_json(f"{BASE}/spot/order_book", {"currency_pair": pair, "limit": limit})
    return {
        "bids": [[float(p), float(q)] for p, q in r["bids"]],
        "asks": [[float(p), float(q)] for p, q in r["asks"]],
    }
