"""CLI エントリポイント。

  python -m edgebot scan [--loop 秒] [--only funding_arb,cex_dex_arb]
  python -m edgebot funding [--top 20]
  python -m edgebot carry BTC_USDT --notional 50 [--live] [--auto]
  python -m edgebot balances
  python -m edgebot report [--days 7] [--min-samples 5] [--top 30]
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="edgebot", description="市場の歪みスキャナ/実行基盤")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_scan = sub.add_parser("scan", help="全エッジを実データで計測してランキング")
    p_scan.add_argument("--loop", type=int, default=None, help="秒間隔で常時計測")
    p_scan.add_argument("--only", type=str, default=None, help="カンマ区切りでエッジ名を限定")

    p_f = sub.add_parser("funding", help="MEXC 資金調達率ランキング")
    p_f.add_argument("--top", type=int, default=20)

    p_c = sub.add_parser("carry", help="ファンディングキャリー建玉プラン (デフォルト dry-run)")
    p_c.add_argument("symbol", help="例: BTC_USDT")
    p_c.add_argument("--notional", type=float, required=True, help="USDT建てサイズ")
    p_c.add_argument("--live", action="store_true", help="現物レッグ(MEXC)を実発注する")
    p_c.add_argument("--auto", action="store_true",
                      help="現物約定を自動待機し、約定次第 Gate ショートで自動ヘッジする(--live必須)")

    p_s = sub.add_parser("short", help="Gate 先物ショートレッグ執行 (デフォルト dry-run)")
    p_s.add_argument("contract", help="例: BTC_USDT")
    p_s.add_argument("--qty", type=float, required=True, help="基軸通貨数量(現物レッグと同数)")
    p_s.add_argument("--live", action="store_true")
    p_s.add_argument("--close", action="store_true", help="ショートを決済する")

    sub.add_parser("balances", help="MEXC 残高照会 (APIキー必須)")

    p_r = sub.add_parser("report", help="スキャンログ集計 (エッジ淘汰用レポート)")
    p_r.add_argument("--days", type=int, default=None, help="直近N日分のログのみ集計")
    p_r.add_argument("--min-samples", type=int, default=5, help="ランキングに含める最低サンプル数")
    p_r.add_argument("--top", type=int, default=30, help="ランキング表示件数")

    args = parser.parse_args(argv)

    if args.cmd == "scan":
        from .scanner import main_scan
        only = [s.strip() for s in args.only.split(",")] if args.only else None
        main_scan(loop=args.loop, only=only)

    elif args.cmd == "funding":
        from .edges import funding_arb
        from .scanner import print_ranking
        print_ranking(funding_arb.scan(top=args.top), top=args.top)

    elif args.cmd == "carry":
        if args.auto:
            from .executor.funding_position import run_carry_auto
            result = run_carry_auto(args.symbol, args.notional, live=args.live)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            if not args.live:
                print("\n(dry-run: 発注していません。自動ヘッジには --live)")
        else:
            from .executor.funding_position import open_carry
            plan = open_carry(args.symbol, args.notional, live=args.live)
            print(json.dumps(plan, ensure_ascii=False, indent=2))
            if not args.live:
                print("\n(dry-run: 発注していません。実発注は --live)")

    elif args.cmd == "short":
        from .executor.funding_position import close_gate_short, open_gate_short
        fn = close_gate_short if args.close else open_gate_short
        plan = fn(args.contract, args.qty, live=args.live)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        if not args.live:
            print("\n(dry-run: 発注していません。実発注は --live)")

    elif args.cmd == "balances":
        from .config import CONFIG
        from .exchanges.mexc import MexcSpotClient
        client = MexcSpotClient(CONFIG.mexc_api_key, CONFIG.mexc_api_secret)
        for asset, free in sorted(client.balances().items()):
            if free > 0:
                print(f"{asset:<10} {free}")

    elif args.cmd == "report":
        from .report import main as report_main
        report_main(days=args.days, min_samples=args.min_samples, top=args.top)

    return 0


if __name__ == "__main__":
    sys.exit(main())
