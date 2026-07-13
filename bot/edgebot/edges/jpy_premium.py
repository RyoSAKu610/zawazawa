"""エッジ5: 国内外プレミアム (bitFlyer/bitbank の BTC/JPY vs MEXC の BTC/USDT)。

国内円建て価格と海外ドル建て価格の乖離を USD/JPY で換算して計測する。
歴史的に国内はプラス乖離(円建てプレミアム)が出やすい。

執行形態:
  - 乖離が十分大きい時: 安い側で買い高い側で売り(両側在庫)
  - 恒常的プレミアムがある場合: 国内で売り続けるフロー(現物の入替えは BTC 送金)
送金には国内取引所のトラベルルール制約があるため、実運用前に経路を確認すること。
"""

from __future__ import annotations

from ..config import CONFIG
from ..exchanges import domestic, mexc
from .base import EdgeResult, bps


def scan() -> list[EdgeResult]:
    results: list[EdgeResult] = []
    try:
        fx = domestic.usd_jpy()
        mexc_btc = mexc.spot_book_ticker("BTCUSDT")
    except Exception as e:
        return [EdgeResult(edge="jpy_premium", instrument="BTC", net_edge_bps=float("-inf"),
                           gross_edge_bps=0.0, direction="-", executable=False,
                           notes=f"データ取得失敗: {e}")]

    mexc_mid_jpy = (mexc_btc["bid"] + mexc_btc["ask"]) / 2 * fx

    for name, fetch, fee in (
        ("bitFlyer", domestic.bitflyer_ticker, CONFIG.bitflyer_spot_taker),
        ("bitbank", domestic.bitbank_ticker, CONFIG.bitbank_spot_taker),
    ):
        try:
            t = fetch()
        except Exception as e:
            results.append(EdgeResult(edge="jpy_premium", instrument=f"BTC@{name}",
                                      net_edge_bps=float("-inf"), gross_edge_bps=0.0,
                                      direction="-", executable=False, notes=f"{name}取得失敗: {e}"))
            continue
        mid = (t["bid"] + t["ask"]) / 2
        premium = (mid - mexc_mid_jpy) / mexc_mid_jpy
        fee_total = fee + CONFIG.mexc_spot_taker
        gross = abs(premium)
        net = bps(gross) - bps(fee_total)
        direction = (f"{name}で売り / MEXCで買い (国内プレミアム)" if premium > 0
                     else f"{name}で買い / MEXCで売り (国内ディスカウント)")
        results.append(EdgeResult(
            edge="jpy_premium",
            instrument=f"BTC@{name}",
            net_edge_bps=round(net, 2),
            gross_edge_bps=round(bps(gross), 2),
            direction=direction,
            executable=True,
            notes="両側在庫前提。BTC送金でのリバランスはトラベルルール・送金時間に注意。",
            details={
                "premium_pct": round(premium * 100, 4),
                "usd_jpy": fx,
                f"{name.lower()}_mid_jpy": mid,
                "mexc_mid_jpy": round(mexc_mid_jpy, 0),
            },
        ))
    results.sort(key=lambda r: r.net_edge_bps, reverse=True)
    return results
