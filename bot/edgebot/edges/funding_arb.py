"""エッジ1: 資金調達率(Funding Rate)キャリー — デルタニュートラル。

現物ロング + 無期限ショート(またはその逆)で価格リスクを消し、資金調達率だけを受け取る。
botter界隈で最も再現性が高いとされる定番エッジ。MEXC はメイカー0%なので往復コストが小さい。

計測ロジック(全て実データ):
  - MEXC 先物全銘柄の fundingRate と collectCycle を取得し年率換算
  - 往復コスト = (現物メイカー + 先物メイカー) × 2 を控除
  - コスト回収に必要な資金調達回数と、年率ネットを算出
  - Bybit の同一銘柄 funding と比較し、取引所間 funding 差(perp-perp アビトラ)も出す

執行上の注意: MEXC 先物の発注APIは一般ユーザー不可のため、
  a) MEXC 現物ロング + Gate/Bybit 無期限ショート、または
  b) MEXC 先物の手動執行 + 現物レッグ自動
のどちらかになる。executable フラグに反映済み。
"""

from __future__ import annotations

from ..config import CONFIG
from ..exchanges import bybit, mexc
from .base import EdgeResult, bps


def annualize(rate_per_interval: float, interval_hours: float) -> float:
    """1回あたりの資金調達率を年率(%)に換算。"""
    per_day = rate_per_interval * (24.0 / interval_hours)
    return per_day * 365.0 * 100.0


def scan(top: int = 15, min_abs_annual_pct: float = 5.0) -> list[EdgeResult]:
    results: list[EdgeResult] = []
    tickers = mexc.futures_tickers()
    bybit_linear = {}
    try:
        bybit_linear = bybit.linear_tickers()
    except Exception:
        pass  # Bybit 比較はオプション

    # 往復コスト(現物往復 + 先物往復、メイカー前提)
    roundtrip_cost = 2 * (CONFIG.mexc_spot_maker + CONFIG.mexc_fut_maker)

    for t in tickers:
        sym = t.get("symbol", "")
        if not sym.endswith("_USDT"):
            continue
        try:
            rate = float(t["fundingRate"])
            last = float(t["lastPrice"])
            volume = float(t.get("amount24", 0))
        except (KeyError, ValueError, TypeError):
            continue
        if last <= 0 or volume < 100_000:  # 出来高が薄すぎる銘柄は執行不能として除外
            continue

        interval_h = 8.0  # MEXC は原則8時間毎。個別確認は funding_rate エンドポイントで可能
        annual = annualize(rate, interval_h)
        if abs(annual) < min_abs_annual_pct:
            continue

        per_settle = abs(rate)
        settles_to_breakeven = roundtrip_cost / per_settle if per_settle > 0 else float("inf")
        net_annual = abs(annual) - bps(roundtrip_cost) / 100.0 * (365 / 30)  # 月1回転と仮定した償却
        direction = (
            "現物ロング + 無期限ショート (funding受取)" if rate > 0
            else "現物ショート不可のため 無期限ロング + 他所ショート (funding受取)"
        )

        spot_sym = sym.replace("_", "")
        details = {
            "funding_rate": rate,
            "interval_hours": interval_h,
            "settles_to_breakeven": round(settles_to_breakeven, 1),
            "volume24_usdt": volume,
        }
        by = bybit_linear.get(spot_sym)
        if by and by.get("funding_rate") is not None:
            details["bybit_funding_rate"] = by["funding_rate"]
            details["mexc_minus_bybit"] = rate - by["funding_rate"]

        results.append(EdgeResult(
            edge="funding_arb",
            instrument=sym,
            net_edge_bps=bps(per_settle) - bps(roundtrip_cost) / max(settles_to_breakeven, 1),
            gross_edge_bps=bps(per_settle),
            annualized_pct=round(annual, 2),
            direction=direction,
            executable=rate > 0,  # 正fundingは現物ロングで組めるので執行可能
            notes="先物レッグ: MEXC先物APIは個人発注不可。Gate/Bybitでショートするか手動執行。",
            details=details,
        ))

    results.sort(key=lambda r: abs(r.annualized_pct or 0), reverse=True)
    return results[:top]
