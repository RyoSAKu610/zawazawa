"""Bybit アダプタ (公開API)。https://api.bybit.com — 資金調達率の比較対象として使用。"""

from __future__ import annotations

from ..http import get_json

BASE = "https://api.bybit.com"


def linear_tickers() -> dict[str, dict]:
    """USDT無期限 symbol -> {bid, ask, funding_rate, next_funding_time}"""
    r = get_json(f"{BASE}/v5/market/tickers", {"category": "linear"})
    out = {}
    for t in r.get("result", {}).get("list", []):
        try:
            out[t["symbol"]] = {
                "bid": float(t["bid1Price"]),
                "ask": float(t["ask1Price"]),
                "funding_rate": float(t["fundingRate"]) if t.get("fundingRate") else None,
                "next_funding_time": int(t["nextFundingTime"]) if t.get("nextFundingTime") else None,
            }
        except (KeyError, ValueError, TypeError):
            continue
    return out


def spot_tickers() -> dict[str, dict]:
    r = get_json(f"{BASE}/v5/market/tickers", {"category": "spot"})
    out = {}
    for t in r.get("result", {}).get("list", []):
        try:
            bid, ask = float(t["bid1Price"]), float(t["ask1Price"])
        except (KeyError, ValueError, TypeError):
            continue
        if bid > 0 and ask > 0:
            out[t["symbol"]] = {"bid": bid, "ask": ask}
    return out
