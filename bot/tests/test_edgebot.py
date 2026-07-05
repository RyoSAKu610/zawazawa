"""純粋ロジックのユニットテスト。

ここで使う数値は算術検証用の入力であり、市場データの模擬ではない
(スキャナの市場値は常にランタイムのAPI取得)。

実行: cd bot && python -m unittest discover -s tests
"""

import hashlib
import hmac
import os
import unittest
import urllib.parse

os.environ.setdefault("EDGEBOT_MIN_EDGE_BPS", "5.0")

from edgebot.edges.base import bps, vwap_fill
from edgebot.edges.funding_arb import annualize
from edgebot.executor.risk import RiskRejected, check_order


class TestVwapFill(unittest.TestCase):
    def test_single_level(self):
        px, fill = vwap_fill([[100.0, 10.0]], 500.0)
        self.assertAlmostEqual(px, 100.0)
        self.assertEqual(fill, 1.0)

    def test_walks_levels(self):
        # 100で5枚(=500), 110で残り550/110=5枚 → 平均 (500+550)/10
        px, _ = vwap_fill([[100.0, 5.0], [110.0, 100.0]], 1050.0)
        self.assertAlmostEqual(px, 105.0)

    def test_insufficient_depth(self):
        self.assertIsNone(vwap_fill([[100.0, 1.0]], 1000.0))


class TestFundingMath(unittest.TestCase):
    def test_annualize_8h(self):
        # 0.01%/8h = 0.03%/日 = 10.95%/年
        self.assertAlmostEqual(annualize(0.0001, 8.0), 10.95, places=2)

    def test_annualize_negative(self):
        self.assertLess(annualize(-0.0001, 8.0), 0)

    def test_bps(self):
        self.assertAlmostEqual(bps(0.0005), 5.0)


class TestRisk(unittest.TestCase):
    def test_rejects_oversize_order(self):
        with self.assertRaises(RiskRejected):
            check_order(notional_usdt=10_000_000, edge_bps=100)

    def test_rejects_thin_edge(self):
        with self.assertRaises(RiskRejected):
            check_order(notional_usdt=10, edge_bps=0.1)

    def test_rejects_kill_switch(self):
        os.environ["EDGEBOT_KILL_SWITCH"] = "1"
        try:
            with self.assertRaises(RiskRejected):
                check_order(notional_usdt=10, edge_bps=100)
        finally:
            os.environ.pop("EDGEBOT_KILL_SWITCH")

    def test_accepts_valid(self):
        check_order(notional_usdt=10, edge_bps=100)  # 例外が出なければOK


class TestMexcSigning(unittest.TestCase):
    def test_signature_matches_reference(self):
        # MEXC 方式: querystring 全体を HMAC-SHA256
        secret = b"testsecret"
        params = {"symbol": "BTCUSDT", "timestamp": 1700000000000, "recvWindow": 5000}
        qs = urllib.parse.urlencode(params)
        expected = hmac.new(secret, qs.encode(), hashlib.sha256).hexdigest()

        from edgebot.exchanges.mexc import MexcSpotClient
        client = MexcSpotClient("key", "testsecret")
        signed, headers = client._signed(dict(params))
        # timestamp はクライアントが上書きするので、同じ入力で再計算して比較
        qs2 = urllib.parse.urlencode({k: v for k, v in signed.items() if k != "signature"})
        expected2 = hmac.new(secret, qs2.encode(), hashlib.sha256).hexdigest()
        self.assertEqual(signed["signature"], expected2)
        self.assertEqual(headers["X-MEXC-APIKEY"], "key")
        self.assertEqual(len(expected), 64)


if __name__ == "__main__":
    unittest.main()
