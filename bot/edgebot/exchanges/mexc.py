"""MEXC アダプタ。

- スポット公開/認証API: https://api.mexc.com  (HMAC-SHA256 署名, X-MEXC-APIKEY ヘッダ)
- 先物公開API:        https://contract.mexc.com

注意: MEXC の先物「発注」API は一般ユーザー向けには長期間メンテナンス扱いで利用不可
(閲覧系エンドポイントは利用可能)。先物レッグの自動執行が必要な戦略は、MEXC の
API 先物利用承認を得るか、Gate 等の他取引所で先物レッグを張ること。
"""

from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

from ..http import get_json, post_json, delete_json

SPOT_BASE = "https://api.mexc.com"
FUT_BASE = "https://contract.mexc.com"


# ---------- 公開: スポット ----------

def spot_book_tickers() -> dict[str, dict]:
    """全ペアの best bid/ask。symbol -> {bid, ask, bid_qty, ask_qty}"""
    rows = get_json(f"{SPOT_BASE}/api/v3/ticker/bookTicker")
    out = {}
    for r in rows:
        try:
            out[r["symbol"]] = {
                "bid": float(r["bidPrice"]),
                "ask": float(r["askPrice"]),
                "bid_qty": float(r["bidQty"]),
                "ask_qty": float(r["askQty"]),
            }
        except (KeyError, ValueError, TypeError):
            continue
    return out


def spot_book_ticker(symbol: str) -> dict:
    r = get_json(f"{SPOT_BASE}/api/v3/ticker/bookTicker", {"symbol": symbol})
    return {
        "bid": float(r["bidPrice"]),
        "ask": float(r["askPrice"]),
        "bid_qty": float(r["bidQty"]),
        "ask_qty": float(r["askQty"]),
    }


def spot_depth(symbol: str, limit: int = 20) -> dict:
    """板。{bids: [[price, qty],...], asks: [...]} float化して返す。"""
    r = get_json(f"{SPOT_BASE}/api/v3/depth", {"symbol": symbol, "limit": limit})
    return {
        "bids": [[float(p), float(q)] for p, q in r["bids"]],
        "asks": [[float(p), float(q)] for p, q in r["asks"]],
    }


def spot_exchange_info() -> dict:
    return get_json(f"{SPOT_BASE}/api/v3/exchangeInfo")


# ---------- 公開: 先物 ----------

def futures_tickers() -> list[dict]:
    """全契約のティッカー(fundingRate 含む)。"""
    r = get_json(f"{FUT_BASE}/api/v1/contract/ticker")
    return r.get("data", [])


def futures_funding_rate(symbol: str) -> dict:
    """symbol 例: BTC_USDT。fundingRate / collectCycle / nextSettleTime を含む。"""
    r = get_json(f"{FUT_BASE}/api/v1/contract/funding_rate/{symbol}")
    return r.get("data", {})


def futures_depth(symbol: str, limit: int = 20) -> dict:
    r = get_json(f"{FUT_BASE}/api/v1/contract/depth/{symbol}", {"limit": limit})
    d = r.get("data", {})
    return {
        "bids": [[float(x[0]), float(x[1])] for x in d.get("bids", [])],
        "asks": [[float(x[0]), float(x[1])] for x in d.get("asks", [])],
    }


# ---------- 認証: スポット ----------

class MexcSpotClient:
    """スポット注文・残高。api_key/secret は環境変数から Config 経由で渡す。"""

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("MEXC_API_KEY / MEXC_API_SECRET が未設定です")
        self.api_key = api_key
        self.api_secret = api_secret.encode()

    def _signed(self, params: dict) -> tuple[dict, dict]:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", 5000)
        qs = urllib.parse.urlencode(params)
        sig = hmac.new(self.api_secret, qs.encode(), hashlib.sha256).hexdigest()
        params["signature"] = sig
        return params, {"X-MEXC-APIKEY": self.api_key}

    def account(self) -> dict:
        params, headers = self._signed({})
        return get_json(f"{SPOT_BASE}/api/v3/account", params, headers)

    def balances(self) -> dict[str, float]:
        acct = self.account()
        return {b["asset"]: float(b["free"]) for b in acct.get("balances", [])}

    def new_order(self, symbol: str, side: str, order_type: str,
                  quantity: float | None = None, quote_qty: float | None = None,
                  price: float | None = None) -> dict:
        """side: BUY/SELL, order_type: LIMIT/MARKET/LIMIT_MAKER。

        メイカー0%を活かすため、通常は LIMIT_MAKER(post-only 相当)を使うこと。
        """
        p: dict = {"symbol": symbol, "side": side, "type": order_type}
        if quantity is not None:
            p["quantity"] = f"{quantity:.10f}".rstrip("0").rstrip(".")
        if quote_qty is not None:
            p["quoteOrderQty"] = f"{quote_qty:.10f}".rstrip("0").rstrip(".")
        if price is not None:
            p["price"] = f"{price:.10f}".rstrip("0").rstrip(".")
        params, headers = self._signed(p)
        return post_json(f"{SPOT_BASE}/api/v3/order", params, headers)

    def cancel_order(self, symbol: str, order_id: str) -> dict:
        params, headers = self._signed({"symbol": symbol, "orderId": order_id})
        return delete_json(f"{SPOT_BASE}/api/v3/order", params, headers)

    def query_order(self, symbol: str, order_id: str) -> dict:
        """注文状況を照会する。status / executedQty を含む。"""
        params, headers = self._signed({"symbol": symbol, "orderId": order_id})
        return get_json(f"{SPOT_BASE}/api/v3/order", params, headers)

    def open_orders(self, symbol: str) -> list:
        params, headers = self._signed({"symbol": symbol})
        return get_json(f"{SPOT_BASE}/api/v3/openOrders", params, headers)
