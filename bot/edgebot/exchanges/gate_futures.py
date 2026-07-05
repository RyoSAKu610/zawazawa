"""Gate.io USDT無期限先物アダプタ (認証API)。https://api.gateio.ws/api/v4

資金調達率キャリー戦略の「先物ショート」レッグ用。
MEXC の先物発注APIは一般ユーザーには開放されていない(閲覧系のみ利用可)ため、
先物ショートを実際に発注する取引所として Gate.io を使う。現物ロング/先物ショートの
組み合わせでファンディングを受け取るデルタニュートラル戦略を想定している。

署名方式は Gate API v4 (HMAC-SHA512):
    SIGN = hex(HMAC_SHA512(secret, signature_string))
    signature_string = f"{METHOD}\\n{url_path}\\n{query_string}\\n{hashed_payload}\\n{timestamp}"
    hashed_payload = hex(SHA512(request_body または空文字列))
    timestamp = str(int(time.time()))
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import time
import urllib.parse

from ..http import get_json, post_json

BASE = "https://api.gateio.ws"
API_PREFIX = "/api/v4"


class GateFuturesClient:
    """Gate.io USDT無期限先物の口座参照・発注クライアント。"""

    def __init__(self, api_key: str, api_secret: str):
        if not api_key or not api_secret:
            raise ValueError("GATE_API_KEY / GATE_API_SECRET が未設定です")
        self.api_key = api_key
        self.api_secret = api_secret.encode()

    def _signed_headers(self, method: str, url_path: str, query_string: str,
                        body_str: str, ts: str | None = None) -> dict:
        """Gate API v4 署名ヘッダを生成する。

        ts を明示的に渡すとその値を timestamp として使う(テスト用)。
        None の場合は現在時刻を使う。
        """
        timestamp = ts if ts is not None else str(int(time.time()))
        hashed_payload = hashlib.sha512((body_str or "").encode()).hexdigest()
        signature_string = f"{method}\n{url_path}\n{query_string}\n{hashed_payload}\n{timestamp}"
        sign = hmac.new(self.api_secret, signature_string.encode(), hashlib.sha512).hexdigest()
        return {
            "KEY": self.api_key,
            "Timestamp": timestamp,
            "SIGN": sign,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: dict | None = None) -> object:
        url_path = f"{API_PREFIX}{path}"
        query_string = urllib.parse.urlencode(params) if params else ""
        headers = self._signed_headers("GET", url_path, query_string, "")
        return get_json(f"{BASE}{url_path}", params, headers)

    def _post(self, path: str, body: dict) -> object:
        url_path = f"{API_PREFIX}{path}"
        body_str = json.dumps(body)
        headers = self._signed_headers("POST", url_path, "", body_str)
        return post_json(f"{BASE}{url_path}", None, headers, body_str)

    # ---------- 口座・ポジション ----------

    def accounts(self) -> dict:
        """USDT建て先物口座の残高・証拠金情報。"""
        return self._get("/futures/usdt/accounts")

    def positions(self) -> list:
        """保有中の全ポジション。"""
        return self._get("/futures/usdt/positions")

    # ---------- 公開情報 (認証不要) ----------

    def contract_info(self, contract: str) -> dict:
        """契約情報。quanto_multiplier / funding_rate / order_size_min を含む。"""
        return get_json(f"{BASE}{API_PREFIX}/futures/usdt/contracts/{contract}")

    def funding_rate(self, contract: str) -> float:
        info = self.contract_info(contract)
        return float(info.get("funding_rate", 0.0))

    def size_for_qty(self, contract: str, qty: float) -> tuple[int, float]:
        """現物数量(基軸通貨建て)を建玉枚数(整数)に変換する。

        quanto_multiplier は1枚あたりの原資産数量。切り捨て・最小1枚。
        1枚未満になる場合は ValueError。
        戻り値: (contracts, actual_qty) — actual_qty は丸め後の実際の数量。
        """
        info = self.contract_info(contract)
        multiplier = float(info["quanto_multiplier"])
        if multiplier <= 0:
            raise ValueError(f"invalid quanto_multiplier for {contract}: {multiplier}")
        contracts = math.floor(qty / multiplier)
        if contracts < 1:
            raise ValueError(
                f"qty {qty} は {contract} の最小1枚(quanto_multiplier={multiplier})未満です"
            )
        actual_qty = contracts * multiplier
        return contracts, actual_qty

    # ---------- 発注 ----------

    def open_short(self, contract: str, contracts: int, price: float | None = None,
                   tif: str = "gtc", reduce_only: bool = False) -> dict:
        """ショートを建てる。price=None なら成行(price="0", tif="ioc")。

        size は負値でショートを表す(Gate futures の仕様)。
        """
        if price is None:
            body = {"contract": contract, "size": -contracts, "price": "0",
                    "tif": "ioc", "reduce_only": reduce_only}
        else:
            body = {"contract": contract, "size": -contracts, "price": str(price),
                    "tif": tif, "reduce_only": reduce_only}
        return self._post("/futures/usdt/orders", body)

    def close_short(self, contract: str, contracts: int) -> dict:
        """ショートを成行で決済する(reduce_only, size は正値)。"""
        body = {"contract": contract, "size": contracts, "price": "0",
                "tif": "ioc", "reduce_only": True}
        return self._post("/futures/usdt/orders", body)
