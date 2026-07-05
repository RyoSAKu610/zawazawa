"""国内取引所 (公開API) と USD/JPY レート。

国内外プレミアム(いわゆる逆キムチプレミアム)計測用。
- bitFlyer: https://api.bitflyer.com/v1/ticker
- bitbank:  https://public.bitbank.cc/{pair}/ticker
- FX:       https://open.er-api.com (無料・キー不要)。実運用では OANDA 等に差し替え可。
"""

from __future__ import annotations

from ..http import get_json


def bitflyer_ticker(product_code: str = "BTC_JPY") -> dict:
    r = get_json("https://api.bitflyer.com/v1/ticker", {"product_code": product_code})
    return {"bid": float(r["best_bid"]), "ask": float(r["best_ask"])}


def bitbank_ticker(pair: str = "btc_jpy") -> dict:
    r = get_json(f"https://public.bitbank.cc/{pair}/ticker")
    d = r["data"]
    return {"bid": float(d["buy"]), "ask": float(d["sell"])}


def usd_jpy() -> float:
    r = get_json("https://open.er-api.com/v6/latest/USD")
    rate = r.get("rates", {}).get("JPY")
    if not rate:
        raise RuntimeError("USD/JPY レート取得に失敗")
    return float(rate)
