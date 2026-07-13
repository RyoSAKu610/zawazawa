"""run_carry_auto (自動キャリー執行) のユニットテスト。

ネットワーク不使用: open_carry / MexcSpotClient / open_gate_short をモックし、
実際の待機は発生させない(time.sleep をパッチ)。

実行: cd bot && python -m unittest discover -s tests
"""

import os
import unittest
from unittest import mock

from edgebot.executor.funding_position import run_carry_auto

BASE_PLAN = {
    "symbol": "BTC_USDT",
    "gate_funding_rate": 0.0002,
    "annualized_pct": 21.9,
    "spot_leg": {"venue": "MEXC spot", "side": "BUY", "symbol": "BTCUSDT", "price": 60000.0, "qty": 0.001},
    "futures_leg": {"venue": "Gate USDT-perp", "side": "SELL(ショート)", "contract": "BTC_USDT", "contracts": 10, "qty": 0.001},
}


def _live_plan(status: str = "NEW", executed_qty: str = "0"):
    plan = dict(BASE_PLAN)
    plan["live"] = True
    plan["spot_order_response"] = {
        "symbol": "BTCUSDT", "orderId": "111", "status": status, "executedQty": executed_qty,
    }
    return plan


class TestRunCarryAutoHappyPath(unittest.TestCase):
    @mock.patch("edgebot.executor.funding_position.open_gate_short")
    @mock.patch("edgebot.executor.funding_position.MexcSpotClient")
    @mock.patch("edgebot.executor.funding_position.open_carry")
    @mock.patch("time.sleep")
    def test_polls_until_filled_then_hedges(self, mock_sleep, mock_open_carry, mock_client_cls,
                                             mock_open_gate_short):
        mock_open_carry.return_value = _live_plan()
        client = mock_client_cls.return_value
        client.query_order.side_effect = [
            {"status": "NEW", "executedQty": "0"},
            {"status": "PARTIALLY_FILLED", "executedQty": "0.0005"},
            {"status": "FILLED", "executedQty": "0.001"},
        ]
        mock_open_gate_short.return_value = {
            "contract": "BTC_USDT", "contracts": 10, "actual_qty": 0.001, "live": True,
            "order_response": {"id": "999"},
        }

        result = run_carry_auto("BTC_USDT", 50.0, live=True, fill_timeout_s=300, poll_interval_s=0.01)

        self.assertEqual(result["status"], "hedged")
        self.assertAlmostEqual(result["executed_qty"], 0.001)
        self.assertEqual(client.query_order.call_count, 3)
        mock_open_gate_short.assert_called_once_with("BTC_USDT", 0.001, live=True)
        self.assertIn("futures_result", result)
        self.assertIn("started_at", result)
        self.assertIn("ended_at", result)
        client.cancel_order.assert_not_called()


class TestRunCarryAutoTimeout(unittest.TestCase):
    @mock.patch("edgebot.executor.funding_position.open_gate_short")
    @mock.patch("edgebot.executor.funding_position.MexcSpotClient")
    @mock.patch("edgebot.executor.funding_position.open_carry")
    @mock.patch("time.sleep")
    def test_timeout_cancels_without_hedging(self, mock_sleep, mock_open_carry, mock_client_cls,
                                              mock_open_gate_short):
        mock_open_carry.return_value = _live_plan()
        client = mock_client_cls.return_value
        client.cancel_order.return_value = {"status": "CANCELED", "executedQty": "0"}

        # fill_timeout_s=0 -> 最初のループでタイムアウト判定が即成立する
        result = run_carry_auto("BTC_USDT", 50.0, live=True, fill_timeout_s=0, poll_interval_s=0.01)

        self.assertEqual(result["status"], "timeout_cancelled")
        self.assertEqual(result["executed_qty"], 0.0)
        client.cancel_order.assert_called_once_with("BTCUSDT", "111")
        mock_open_gate_short.assert_not_called()
        client.query_order.assert_not_called()


class TestRunCarryAutoKillSwitch(unittest.TestCase):
    @mock.patch("edgebot.executor.funding_position.open_gate_short")
    @mock.patch("edgebot.executor.funding_position.MexcSpotClient")
    @mock.patch("edgebot.executor.funding_position.open_carry")
    @mock.patch("time.sleep")
    def test_kill_switch_aborts_and_cancels(self, mock_sleep, mock_open_carry, mock_client_cls,
                                             mock_open_gate_short):
        mock_open_carry.return_value = _live_plan()
        client = mock_client_cls.return_value
        client.cancel_order.return_value = {"status": "CANCELED", "executedQty": "0"}

        os.environ["EDGEBOT_KILL_SWITCH"] = "1"
        try:
            result = run_carry_auto("BTC_USDT", 50.0, live=True, fill_timeout_s=300, poll_interval_s=0.01)
        finally:
            os.environ.pop("EDGEBOT_KILL_SWITCH", None)

        self.assertEqual(result["status"], "aborted_kill_switch")
        client.cancel_order.assert_called_once_with("BTCUSDT", "111")
        mock_open_gate_short.assert_not_called()
        client.query_order.assert_not_called()


class TestRunCarryAutoDryRun(unittest.TestCase):
    @mock.patch("edgebot.executor.funding_position.open_gate_short")
    @mock.patch("edgebot.executor.funding_position.MexcSpotClient")
    @mock.patch("edgebot.executor.funding_position.open_carry")
    @mock.patch("time.sleep")
    def test_dry_run_does_not_poll_or_place_orders(self, mock_sleep, mock_open_carry, mock_client_cls,
                                                    mock_open_gate_short):
        plan = dict(BASE_PLAN)
        plan["live"] = False
        mock_open_carry.return_value = plan

        result = run_carry_auto("BTC_USDT", 50.0, live=False)

        self.assertEqual(result["status"], "dry_run")
        self.assertIs(result["plan"], plan)
        mock_client_cls.assert_not_called()
        mock_open_gate_short.assert_not_called()
        mock_sleep.assert_not_called()


if __name__ == "__main__":
    unittest.main()
