"""エッジ淘汰用の集計レポート。スキャンログから「手数料控除後プラスが持続するエッジ」を選定する。"""

from __future__ import annotations

import glob
import json
import os
import statistics
from datetime import datetime, timezone

from .config import CONFIG

NEG_INF = float("-inf")


def load_rows(log_dir: str, days: int | None = None) -> list[dict]:
    """logs/edges-*.jsonl を全件(または直近 days 日分)読み込んでレコードのリストを返す。"""
    paths = sorted(glob.glob(os.path.join(log_dir, "edges-*.jsonl")))
    if days is not None:
        paths = paths[-days:]

    rows: list[dict] = []
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                rows.append(json.loads(line))
    return rows


def aggregate(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """(edge, instrument) ごとに samples/errors/positive_ratio 等の統計を計算する。

    net_edge_bps が -Infinity (計測失敗を表すエラー行) は統計値の計算から除外し、
    errors としてカウントするのみ。
    """
    groups: dict[tuple[str, str], list[dict]] = {}
    for r in rows:
        key = (r.get("edge", "?"), r.get("instrument", "?"))
        groups.setdefault(key, []).append(r)

    stats: dict[tuple[str, str], dict] = {}
    for key, group_rows in groups.items():
        errors = [r for r in group_rows if r.get("net_edge_bps") == NEG_INF]
        ok_rows = [r for r in group_rows if r.get("net_edge_bps") != NEG_INF]
        net_values = [float(r["net_edge_bps"]) for r in ok_rows]
        ts_values = [float(r["ts"]) for r in group_rows if "ts" in r]

        samples = len(ok_rows)
        if samples > 0:
            positive_ratio = sum(1 for v in net_values if v > 0) / samples
            mean_net_bps = statistics.mean(net_values)
            median_net_bps = statistics.median(net_values)
            max_net_bps = max(net_values)
            # 時系列順で「最後」を決めるため ts でソートしてから最後の値を取る
            ok_sorted = sorted(ok_rows, key=lambda r: r.get("ts", 0.0))
            last_net_bps = float(ok_sorted[-1]["net_edge_bps"])
        else:
            positive_ratio = 0.0
            mean_net_bps = 0.0
            median_net_bps = 0.0
            max_net_bps = 0.0
            last_net_bps = 0.0

        stats[key] = {
            "samples": samples,
            "errors": len(errors),
            "positive_ratio": positive_ratio,
            "mean_net_bps": mean_net_bps,
            "median_net_bps": median_net_bps,
            "max_net_bps": max_net_bps,
            "last_net_bps": last_net_bps,
            "first_ts": min(ts_values) if ts_values else None,
            "last_ts": max(ts_values) if ts_values else None,
        }
    return stats


def _fmt_ts(ts: float | None) -> str:
    if ts is None:
        return "-"
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def print_report(stats: dict[tuple[str, str], dict], min_samples: int = 5, top: int = 30) -> None:
    """(edge, instrument) ランキング + エッジ別ロールアップ + 実運用候補を表示する。"""
    eligible = {k: v for k, v in stats.items() if v["samples"] >= min_samples}
    ranked = sorted(
        eligible.items(),
        key=lambda kv: (kv[1]["positive_ratio"], kv[1]["median_net_bps"]),
        reverse=True,
    )

    print(f"=== エッジ×銘柄 ランキング (samples >= {min_samples}) ===")
    print(f"{'edge':<20} {'instrument':<16} {'samples':>7} {'errors':>6} {'勝率':>6} "
          f"{'平均bps':>9} {'中央値bps':>10} {'最大bps':>9} {'直近bps':>9}  最終計測")
    print("-" * 120)
    for (edge, instrument), s in ranked[:top]:
        print(f"{edge:<20} {instrument:<16} {s['samples']:>7} {s['errors']:>6} "
              f"{s['positive_ratio']*100:>5.1f}% {s['mean_net_bps']:>9.2f} "
              f"{s['median_net_bps']:>10.2f} {s['max_net_bps']:>9.2f} {s['last_net_bps']:>9.2f}  "
              f"{_fmt_ts(s['last_ts'])}")

    print()
    print("=== エッジ別ロールアップ (全銘柄合算) ===")
    per_edge: dict[str, dict] = {}
    for (edge, _instrument), s in stats.items():
        acc = per_edge.setdefault(edge, {"samples": 0, "errors": 0, "positive": 0, "net_values": []})
        acc["samples"] += s["samples"]
        acc["errors"] += s["errors"]
        acc["positive"] += round(s["positive_ratio"] * s["samples"])

    print(f"{'edge':<20} {'samples':>7} {'errors':>6} {'勝率':>6}")
    print("-" * 45)
    for edge in sorted(per_edge, key=lambda e: per_edge[e]["samples"], reverse=True):
        acc = per_edge[edge]
        ratio = acc["positive"] / acc["samples"] if acc["samples"] else 0.0
        print(f"{edge:<20} {acc['samples']:>7} {acc['errors']:>6} {ratio*100:>5.1f}%")

    print()
    print("=== 実運用候補 (勝率 >= 50% かつ 中央値bps > 0) ===")
    candidates = [
        (edge, instrument, s) for (edge, instrument), s in eligible.items()
        if s["positive_ratio"] >= 0.5 and s["median_net_bps"] > 0
    ]
    candidates.sort(key=lambda t: (t[2]["positive_ratio"], t[2]["median_net_bps"]), reverse=True)
    if not candidates:
        print("(該当なし)")
    else:
        for edge, instrument, s in candidates:
            print(f"  {edge:<20} {instrument:<16} 勝率={s['positive_ratio']*100:.1f}% "
                  f"中央値={s['median_net_bps']:.2f}bps samples={s['samples']}")


def main(days: int | None = None, min_samples: int = 5, top: int = 30) -> None:
    rows = load_rows(CONFIG.log_dir, days=days)
    stats = aggregate(rows)
    print_report(stats, min_samples=min_samples, top=top)
