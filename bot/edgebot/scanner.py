"""全エッジを実データで一括計測し、ランキング表示 + JSONL 追記ログ。

使い方:
    python -m edgebot scan            # 1回計測
    python -m edgebot scan --loop 60  # 60秒間隔で常時計測(エッジの持続性検証用)
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from .config import CONFIG
from .edges import cex_dex_arb, cross_exchange_arb, funding_arb, jpy_premium, triangular_arb
from .edges.base import EdgeResult

SCANNERS = {
    "funding_arb": lambda: funding_arb.scan(),
    "cross_exchange_arb": lambda: cross_exchange_arb.scan(),
    "cex_dex_arb": lambda: cex_dex_arb.scan(),
    "triangular_arb": lambda: triangular_arb.scan(),
    "jpy_premium": lambda: jpy_premium.scan(),
}


def run_all(only: list[str] | None = None) -> list[EdgeResult]:
    results: list[EdgeResult] = []
    for name, fn in SCANNERS.items():
        if only and name not in only:
            continue
        t0 = time.time()
        try:
            rs = fn()
            results.extend(rs)
            print(f"[scan] {name}: {len(rs)}件 ({time.time()-t0:.1f}s)")
        except Exception as e:
            print(f"[scan] {name}: 失敗 — {e}")
    return results


def log_results(results: list[EdgeResult]) -> str:
    os.makedirs(CONFIG.log_dir, exist_ok=True)
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    path = os.path.join(CONFIG.log_dir, f"edges-{day}.jsonl")
    with open(path, "a") as f:
        for r in results:
            f.write(json.dumps(r.to_dict(), ensure_ascii=False) + "\n")
    return path


def print_ranking(results: list[EdgeResult], top: int = 25) -> None:
    ok = [r for r in results if r.net_edge_bps != float("-inf")]
    ok.sort(key=lambda r: r.net_edge_bps, reverse=True)
    print()
    print(f"{'edge':<20} {'instrument':<26} {'net(bps)':>9} {'gross':>8} {'年率%':>8}  direction")
    print("-" * 110)
    for r in ok[:top]:
        ann = f"{r.annualized_pct:.1f}" if r.annualized_pct is not None else "-"
        mark = "" if r.executable else " [手動]"
        print(f"{r.edge:<20} {r.instrument:<26} {r.net_edge_bps:>9.2f} {r.gross_edge_bps:>8.2f} "
              f"{ann:>8}  {r.direction}{mark}")
    positives = [r for r in ok if r.net_edge_bps > 0]
    print("-" * 110)
    print(f"手数料控除後プラスのエッジ: {len(positives)} / {len(ok)} 件")
    errors = [r for r in results if r.net_edge_bps == float("-inf")]
    for r in errors:
        print(f"  ! {r.edge}/{r.instrument}: {r.notes}")


def main_scan(loop: int | None = None, only: list[str] | None = None) -> None:
    while True:
        started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        print(f"=== edgebot scan {started} ===")
        results = run_all(only)
        print_ranking(results)
        path = log_results(results)
        print(f"ログ追記: {path}")
        if loop is None:
            break
        time.sleep(loop)
