"""report.py の集計ロジックのユニットテスト(テスト用フィクスチャのみ・ネットワーク不使用)。

実行: cd bot && python -m unittest discover -s tests
"""

import json
import os
import shutil
import tempfile
import unittest

from edgebot.report import aggregate, load_rows

NEG_INF = float("-inf")

# --- テスト用フィクスチャデータ (実市場データではない) ---
DAY1_ROWS = [
    {"edge": "funding_arb", "instrument": "BTCUSDT", "net_edge_bps": 3.0, "gross_edge_bps": 5.0,
     "direction": "long", "annualized_pct": 10.0, "executable": True, "notes": "", "details": {},
     "ts": 1_700_000_000.0},
    {"edge": "funding_arb", "instrument": "BTCUSDT", "net_edge_bps": -1.0, "gross_edge_bps": 1.0,
     "direction": "long", "annualized_pct": None, "executable": True, "notes": "", "details": {},
     "ts": 1_700_000_100.0},
    {"edge": "funding_arb", "instrument": "ETHUSDT", "net_edge_bps": 2.0, "gross_edge_bps": 4.0,
     "direction": "short", "annualized_pct": None, "executable": True, "notes": "", "details": {},
     "ts": 1_700_000_200.0},
    # エラー行: net_edge_bps が -Infinity (計測失敗)
    {"edge": "funding_arb", "instrument": "ETHUSDT", "net_edge_bps": NEG_INF, "gross_edge_bps": 0.0,
     "direction": "-", "annualized_pct": None, "executable": False, "notes": "テスト用エラー行",
     "details": {}, "ts": 1_700_000_300.0},
]

DAY2_ROWS = [
    {"edge": "funding_arb", "instrument": "BTCUSDT", "net_edge_bps": 7.0, "gross_edge_bps": 9.0,
     "direction": "long", "annualized_pct": 20.0, "executable": True, "notes": "", "details": {},
     "ts": 1_700_100_000.0},
]


def _write_jsonl(path: str, rows: list[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


class TestAggregate(unittest.TestCase):
    def setUp(self):
        self.rows = DAY1_ROWS + DAY2_ROWS

    def test_samples_and_errors_excludes_neg_inf(self):
        stats = aggregate(self.rows)
        btc = stats[("funding_arb", "BTCUSDT")]
        eth = stats[("funding_arb", "ETHUSDT")]
        # BTC: 2件 (day1) + 1件 (day2) = 3 サンプル、エラーなし
        self.assertEqual(btc["samples"], 3)
        self.assertEqual(btc["errors"], 0)
        # ETH: 1件正常 + 1件エラー行 → samples=1, errors=1
        self.assertEqual(eth["samples"], 1)
        self.assertEqual(eth["errors"], 1)

    def test_positive_ratio(self):
        stats = aggregate(self.rows)
        btc = stats[("funding_arb", "BTCUSDT")]
        # net_edge_bps: 3.0, -1.0, 7.0 → 正は2/3
        self.assertAlmostEqual(btc["positive_ratio"], 2 / 3)
        eth = stats[("funding_arb", "ETHUSDT")]
        # net_edge_bps: 2.0 (エラー行は除外) → 正は1/1
        self.assertAlmostEqual(eth["positive_ratio"], 1.0)

    def test_median_and_mean(self):
        stats = aggregate(self.rows)
        btc = stats[("funding_arb", "BTCUSDT")]
        # 3.0, -1.0, 7.0 の中央値 = 3.0, 平均 = 3.0
        self.assertAlmostEqual(btc["median_net_bps"], 3.0)
        self.assertAlmostEqual(btc["mean_net_bps"], 3.0)
        self.assertAlmostEqual(btc["max_net_bps"], 7.0)

    def test_last_net_bps_uses_latest_ts(self):
        stats = aggregate(self.rows)
        btc = stats[("funding_arb", "BTCUSDT")]
        # ts が最大の行 (day2, 7.0) が最後の値になる
        self.assertAlmostEqual(btc["last_net_bps"], 7.0)

    def test_empty_rows(self):
        self.assertEqual(aggregate([]), {})


class TestLoadRows(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="edgebot_report_test_")
        self.addCleanup(shutil.rmtree, self.tmpdir, ignore_errors=True)
        _write_jsonl(os.path.join(self.tmpdir, "edges-20260101.jsonl"), DAY1_ROWS)
        _write_jsonl(os.path.join(self.tmpdir, "edges-20260102.jsonl"), DAY2_ROWS)

    def test_load_all_files(self):
        rows = load_rows(self.tmpdir)
        self.assertEqual(len(rows), len(DAY1_ROWS) + len(DAY2_ROWS))

    def test_days_filter_returns_only_newest_file(self):
        rows = load_rows(self.tmpdir, days=1)
        # 日付順で最新 (20260102) の1ファイル分のみ
        self.assertEqual(len(rows), len(DAY2_ROWS))
        for r in rows:
            self.assertEqual(r["instrument"], "BTCUSDT")
            self.assertEqual(r["net_edge_bps"], 7.0)

    def test_days_filter_none_returns_all(self):
        rows = load_rows(self.tmpdir, days=None)
        self.assertEqual(len(rows), len(DAY1_ROWS) + len(DAY2_ROWS))


if __name__ == "__main__":
    unittest.main()
