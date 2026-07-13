"""Jupiter (Solana DEX アグリゲータ) 見積りAPI。キー不要の lite-api を使用。

見積りは実際のオンチェーン流動性に基づく実行可能レート(スリッページ・ルーティング込み)。
CEX-DEX アビトラの DEX 側価格として使う。
"""

from __future__ import annotations

from ..http import get_json

QUOTE_URL = "https://lite-api.jup.ag/swap/v1/quote"

# 主要トークンの mint アドレス
MINTS = {
    "SOL": "So11111111111111111111111111111111111111112",
    "USDC": "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v",
    "USDT": "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB",
    "JUP": "JUPyiwrYJFskUPiHa7hkeR8VUtAeFoSYbKedZNsDvCN",
    "WBTC": "3NZ9JMVBmGAqocybic2c7LQCJScmgsAZ6vQqTDzcqmJh",
}

DECIMALS = {"SOL": 9, "USDC": 6, "USDT": 6, "JUP": 6, "WBTC": 8}


def quote(input_token: str, output_token: str, amount_in: float,
          slippage_bps: int = 50) -> dict:
    """amount_in は入力トークンの人間可読数量。

    返り値: {out_amount, price, price_impact_pct, route}
      price = 出力数量 / 入力数量
    """
    in_mint = MINTS[input_token]
    out_mint = MINTS[output_token]
    raw_amount = int(round(amount_in * 10 ** DECIMALS[input_token]))
    r = get_json(QUOTE_URL, {
        "inputMint": in_mint,
        "outputMint": out_mint,
        "amount": raw_amount,
        "slippageBps": slippage_bps,
    })
    out_amount = int(r["outAmount"]) / 10 ** DECIMALS[output_token]
    return {
        "out_amount": out_amount,
        "price": out_amount / amount_in if amount_in else 0.0,
        "price_impact_pct": float(r.get("priceImpactPct", 0) or 0),
        "route": [s.get("swapInfo", {}).get("label", "?") for s in r.get("routePlan", [])],
    }
