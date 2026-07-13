"""Gate.io 先物クライアントの純粋ロジックテスト(ネットワーク不使用)。"""

import hashlib
import hmac
import unittest
from unittest import mock

from edgebot.exchanges.gate_futures import GateFuturesClient


class TestGateFuturesSigning(unittest.TestCase):
    def test_signature_matches_reference(self):
        secret = b"testsecret"
        method = "POST"
        url_path = "/api/v4/futures/usdt/orders"
        query_string = ""
        body_str = '{"contract": "BTC_USDT", "size": -1, "price": "0", "tif": "ioc"}'
        timestamp = "1700000000"

        hashed_payload = hashlib.sha512(body_str.encode()).hexdigest()
        signature_string = f"{method}\n{url_path}\n{query_string}\n{hashed_payload}\n{timestamp}"
        expected_sign = hmac.new(secret, signature_string.encode(), hashlib.sha512).hexdigest()

        client = GateFuturesClient("key", "testsecret")
        headers = client._signed_headers(method, url_path, query_string, body_str, ts=timestamp)

        self.assertEqual(headers["SIGN"], expected_sign)
        self.assertEqual(headers["KEY"], "key")
        self.assertEqual(headers["Timestamp"], timestamp)
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertEqual(len(expected_sign), 128)  # SHA512 hexdigest長

    def test_signature_empty_body(self):
        secret = b"s3cr3t"
        method = "GET"
        url_path = "/api/v4/futures/usdt/accounts"
        query_string = ""
        timestamp = "1700000001"

        hashed_payload = hashlib.sha512(b"").hexdigest()
        signature_string = f"{method}\n{url_path}\n{query_string}\n{hashed_payload}\n{timestamp}"
        expected_sign = hmac.new(secret, signature_string.encode(), hashlib.sha512).hexdigest()

        client = GateFuturesClient("key", "s3cr3t")
        headers = client._signed_headers(method, url_path, query_string, "", ts=timestamp)
        self.assertEqual(headers["SIGN"], expected_sign)


class TestSizeForQty(unittest.TestCase):
    def _client_with_multiplier(self, multiplier: str):
        client = GateFuturesClient("key", "secret")
        client.contract_info = mock.Mock(return_value={
            "quanto_multiplier": multiplier,
            "funding_rate": "0.0001",
            "order_size_min": 1,
        })
        return client

    def test_converts_qty_to_contracts(self):
        client = self._client_with_multiplier("0.0001")
        contracts, actual_qty = client.size_for_qty("BTC_USDT", 0.001)
        self.assertEqual(contracts, 10)
        self.assertAlmostEqual(actual_qty, 0.001)

    def test_floors_partial_contract(self):
        client = self._client_with_multiplier("0.0001")
        contracts, actual_qty = client.size_for_qty("BTC_USDT", 0.00105)
        self.assertEqual(contracts, 10)
        self.assertAlmostEqual(actual_qty, 0.001)

    def test_raises_below_min_contract(self):
        client = self._client_with_multiplier("0.0001")
        with self.assertRaises(ValueError):
            client.size_for_qty("BTC_USDT", 0.00001)


class TestOrderBodies(unittest.TestCase):
    def setUp(self):
        self.client = GateFuturesClient("key", "secret")
        self.client._post = mock.Mock(return_value={"id": "123"})

    def test_open_short_market_builds_negative_size(self):
        self.client.open_short("BTC_USDT", 5)
        path, body = self.client._post.call_args[0]
        self.assertEqual(path, "/futures/usdt/orders")
        self.assertEqual(body["contract"], "BTC_USDT")
        self.assertEqual(body["size"], -5)
        self.assertEqual(body["price"], "0")
        self.assertEqual(body["tif"], "ioc")
        self.assertFalse(body["reduce_only"])

    def test_open_short_limit_uses_price_and_tif(self):
        self.client.open_short("BTC_USDT", 3, price=65000.5, tif="gtc")
        _, body = self.client._post.call_args[0]
        self.assertEqual(body["size"], -3)
        self.assertEqual(body["price"], "65000.5")
        self.assertEqual(body["tif"], "gtc")

    def test_close_short_builds_positive_reduce_only(self):
        self.client.close_short("BTC_USDT", 5)
        path, body = self.client._post.call_args[0]
        self.assertEqual(path, "/futures/usdt/orders")
        self.assertEqual(body["size"], 5)
        self.assertEqual(body["price"], "0")
        self.assertEqual(body["tif"], "ioc")
        self.assertTrue(body["reduce_only"])


class TestFundingRate(unittest.TestCase):
    def test_funding_rate_returns_float(self):
        client = GateFuturesClient("key", "secret")
        client.contract_info = mock.Mock(return_value={"funding_rate": "0.00015"})
        self.assertAlmostEqual(client.funding_rate("BTC_USDT"), 0.00015)


if __name__ == "__main__":
    unittest.main()
