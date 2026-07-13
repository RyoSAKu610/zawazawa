"""エッジ2: CEX-DEX アビトラ (MEXC 現物 vs Solana DEX / Jupiter)。

同一トークンの CEX 価格と DEX 実行可能価格の乖離を、実サイズで計測する。
- CEX 側: MEXC 板を想定サイズぶん食った VWAP (テイカー手数料込み)
- DEX 側: Jupiter の実見積り (ルーティング・スリッページ込み)
- Solana のトランザクション代は微小だが priority fee 分を控除

在庫を両側に置いて同時執行する前提(送金レイテンシを踏まない)。
"""

from __future__ import annotations

from ..config import CONFIG
from ..dex import jupiter
from ..exchanges import mexc
from .base import EdgeResult, bps, vwap_fill

# MEXC シンボル -> (Jupiterトークン, 見積もり基準トークン)
PAIRS = [
    ("SOLUSDT", "SOL", "USDT"),
    ("JUPUSDT", "JUP", "USDT"),
]

SOLANA_TX_COST_USD = 0.05  # priority fee 込みの概算上限。details に明示する


def scan(notional: float | None = None) -> list[EdgeResult]:
    notional = notional or CONFIG.trade_notional_usdt
    results: list[EdgeResult] = []

    for mexc_sym, token, quote_token in PAIRS:
        try:
            depth = mexc.spot_depth(mexc_sym, limit=50)
        except Exception as e:
            results.append(_error_result(mexc_sym, f"MEXC板取得失敗: {e}"))
            continue

        # 方向A: DEXで買って CEX で売る
        cex_sell = vwap_fill(depth["bids"], notional)
        # 方向B: CEXで買って DEX で売る
        cex_buy = vwap_fill(depth["asks"], notional)
        if not cex_sell or not cex_buy:
            results.append(_error_result(mexc_sym, f"板が{notional}USDTに対して薄すぎる"))
            continue

        try:
            # DEX買い: USDT -> token
            dex_buy = jupiter.quote(quote_token, token, notional)
            # DEX売り: token -> USDT (CEXで買える数量を売る想定)
            token_qty = notional / cex_buy[0]
            dex_sell = jupiter.quote(token, quote_token, token_qty)
        except Exception as e:
            results.append(_error_result(mexc_sym, f"Jupiter見積り失敗: {e}"))
            continue

        fee = CONFIG.mexc_spot_taker
        tx_bps = bps(SOLANA_TX_COST_USD / notional)

        # 方向A: DEXで notional USDT を token に替え、MEXC で売る
        dex_buy_px = notional / dex_buy["out_amount"]  # USDT per token
        edge_a = bps((cex_sell[0] * (1 - fee) - dex_buy_px) / dex_buy_px) - tx_bps
        # 方向B: MEXC で買い、DEX で売る
        dex_sell_px = dex_sell["out_amount"] / token_qty
        edge_b = bps((dex_sell_px - cex_buy[0] * (1 + fee)) / cex_buy[0]) - tx_bps

        best_dir = "DEX買い→MEXC売り" if edge_a >= edge_b else "MEXC買い→DEX売り"
        results.append(EdgeResult(
            edge="cex_dex_arb",
            instrument=mexc_sym,
            net_edge_bps=round(max(edge_a, edge_b), 2),
            gross_edge_bps=round(max(edge_a, edge_b) + tx_bps + bps(fee), 2),
            direction=best_dir,
            executable=True,
            notes="両側在庫前提。DEX側の執行にはSolanaウォレットとスワップ送信実装が必要。",
            details={
                "notional_usdt": notional,
                "edge_dex_to_cex_bps": round(edge_a, 2),
                "edge_cex_to_dex_bps": round(edge_b, 2),
                "mexc_vwap_bid": cex_sell[0],
                "mexc_vwap_ask": cex_buy[0],
                "jupiter_buy_px": dex_buy_px,
                "jupiter_sell_px": dex_sell_px,
                "jupiter_route_buy": dex_buy["route"],
                "dex_price_impact_pct": dex_buy["price_impact_pct"],
                "solana_tx_cost_usd": SOLANA_TX_COST_USD,
            },
        ))

    results.sort(key=lambda r: r.net_edge_bps, reverse=True)
    return results


def _error_result(sym: str, msg: str) -> EdgeResult:
    return EdgeResult(edge="cex_dex_arb", instrument=sym, net_edge_bps=float("-inf"),
                      gross_edge_bps=0.0, direction="-", executable=False, notes=msg)
