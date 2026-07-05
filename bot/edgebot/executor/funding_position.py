"""ファンディングキャリーの建玉支援。

構成: MEXC 現物ロング + Gate USDT無期限ショート (デルタニュートラル)。
MEXC 先物の発注APIは一般ユーザー不可のため、ショートレッグは Gate で執行する。
※ funding を受け取るのはショートを置いた Gate 側なので、判定は Gate のレートで行う。

dry_run (デフォルト) は実データで注文内容を組み立てて表示するだけで発注しない。
実運用の順序: carry --live で現物レッグ約定 → short --live でショートレッグ。
"""

from __future__ import annotations

from ..config import CONFIG
from ..edges.funding_arb import annualize
from ..exchanges import mexc
from ..exchanges.gate_futures import GateFuturesClient
from ..exchanges.mexc import MexcSpotClient
from ..http import get_json
from .risk import check_order

GATE_FUNDING_INTERVAL_H = 8.0


def _gate_contract_info(contract: str) -> dict:
    """公開エンドポイント(認証不要)。"""
    return get_json(f"https://api.gateio.ws/api/v4/futures/usdt/contracts/{contract}")


def open_carry(symbol: str, notional_usdt: float, live: bool = False) -> dict:
    """symbol 例: BTC_USDT。Gate の funding が正 (ショート側が受取) であることを確認し、
    MEXC 現物ロング + Gate ショートのプランを組む。live=True で現物レッグのみ発注。
    """
    info = _gate_contract_info(symbol)
    gate_rate = float(info.get("funding_rate", 0.0))
    interval_h = float(info.get("funding_interval", 28800)) / 3600 or GATE_FUNDING_INTERVAL_H
    if gate_rate <= 0:
        raise RuntimeError(
            f"{symbol} の Gate funding は {gate_rate:+.6f} で受取側が先物ロング。"
            "現物ショート不可のためこの形では組めない。")

    mexc_rate = None
    try:
        mexc_rate = float(mexc.futures_funding_rate(symbol).get("fundingRate", 0))
    except Exception:
        pass  # 参考値なので失敗しても続行

    spot_symbol = symbol.replace("_", "")
    book = mexc.spot_book_ticker(spot_symbol)
    limit_px = book["bid"]  # メイカー0%を活かして bid に置く
    qty = notional_usdt / limit_px

    # Gate の建玉枚数に合わせて現物数量を丸める(デルタを揃える)
    multiplier = float(info["quanto_multiplier"])
    contracts = int(qty / multiplier)
    if contracts < 1:
        raise RuntimeError(
            f"notional {notional_usdt} USDT では {symbol} の最小1枚"
            f"(quanto_multiplier={multiplier}, 約{multiplier * limit_px:.2f} USDT)に満たない")
    qty = contracts * multiplier
    notional_usdt = qty * limit_px

    edge_bps_per_settle = gate_rate * 10_000
    check_order(notional_usdt, edge_bps_per_settle)

    plan = {
        "symbol": symbol,
        "gate_funding_rate": gate_rate,
        "mexc_funding_rate_ref": mexc_rate,
        "annualized_pct": round(annualize(gate_rate, interval_h), 2),
        "spot_leg": {
            "venue": "MEXC spot", "side": "BUY", "type": "LIMIT_MAKER",
            "symbol": spot_symbol, "price": limit_px, "qty": qty,
        },
        "futures_leg": {
            "venue": "Gate USDT-perp", "side": "SELL(ショート)",
            "contract": symbol, "contracts": contracts, "qty": qty,
            "note": "現物約定を確認してから `python -m edgebot short` で執行。レバレッジ3倍以下推奨。",
        },
        "live": live,
    }

    if live:
        client = MexcSpotClient(CONFIG.mexc_api_key, CONFIG.mexc_api_secret)
        plan["spot_order_response"] = client.new_order(
            spot_symbol, "BUY", "LIMIT_MAKER", quantity=qty, price=limit_px)
    return plan


def open_gate_short(contract: str, qty: float, live: bool = False) -> dict:
    """Gate でショートレッグを執行する。qty は基軸通貨数量(現物レッグと同数)。"""
    info = _gate_contract_info(contract)
    multiplier = float(info["quanto_multiplier"])
    contracts = int(qty / multiplier)
    if contracts < 1:
        raise RuntimeError(f"qty {qty} は最小1枚(={multiplier})未満")
    mark = float(info.get("mark_price") or info.get("last_price") or 0)
    notional = contracts * multiplier * mark
    check_order(notional, float(info.get("funding_rate", 0)) * 10_000)

    plan = {
        "contract": contract, "contracts": contracts,
        "actual_qty": contracts * multiplier, "est_notional_usdt": round(notional, 2),
        "funding_rate": info.get("funding_rate"), "live": live,
    }
    if live:
        client = GateFuturesClient(CONFIG.gate_api_key, CONFIG.gate_api_secret)
        plan["order_response"] = client.open_short(contract, contracts)
    return plan


def close_gate_short(contract: str, qty: float, live: bool = False) -> dict:
    """ショートレッグを成行で決済する。"""
    info = _gate_contract_info(contract)
    multiplier = float(info["quanto_multiplier"])
    contracts = int(qty / multiplier)
    if contracts < 1:
        raise RuntimeError(f"qty {qty} は最小1枚(={multiplier})未満")
    plan = {"contract": contract, "contracts": contracts, "live": live}
    if live:
        client = GateFuturesClient(CONFIG.gate_api_key, CONFIG.gate_api_secret)
        plan["order_response"] = client.close_short(contract, contracts)
    return plan
