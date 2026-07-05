"""実行設定。APIキーは環境変数からのみ読む(リポジトリに秘密情報を置かない)。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    return float(raw) if raw not in (None, "") else default


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.environ.get(name)
    if not raw:
        return default
    return [s.strip().upper() for s in raw.split(",") if s.strip()]


@dataclass
class Config:
    # --- 認証 (実発注に必要。スキャンだけなら不要) ---
    mexc_api_key: str = field(default_factory=lambda: os.environ.get("MEXC_API_KEY", ""))
    mexc_api_secret: str = field(default_factory=lambda: os.environ.get("MEXC_API_SECRET", ""))
    gate_api_key: str = field(default_factory=lambda: os.environ.get("GATE_API_KEY", ""))
    gate_api_secret: str = field(default_factory=lambda: os.environ.get("GATE_API_SECRET", ""))

    # --- スキャン対象 ---
    # 資金調達率スキャンは全銘柄を見るので設定不要。板系エッジはこのリストを見る。
    symbols: list[str] = field(default_factory=lambda: _env_list(
        "EDGEBOT_SYMBOLS",
        ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT"],
    ))
    # CEX-DEXアビトラで使う想定取引サイズ(USDT建て)。実測スリッページ込みの見積りに使う。
    trade_notional_usdt: float = field(default_factory=lambda: _env_float("EDGEBOT_NOTIONAL_USDT", 500.0))

    # --- 手数料 (テイカー、割合)。実アカウントの手数料が判明したら環境変数で上書きする ---
    # MEXC 公表値: スポット メイカー0%/テイカー0.05% (多数ペアは0/0)、先物 メイカー0%/テイカー0.02%
    mexc_spot_taker: float = field(default_factory=lambda: _env_float("MEXC_SPOT_TAKER", 0.0005))
    mexc_spot_maker: float = field(default_factory=lambda: _env_float("MEXC_SPOT_MAKER", 0.0))
    mexc_fut_taker: float = field(default_factory=lambda: _env_float("MEXC_FUT_TAKER", 0.0002))
    mexc_fut_maker: float = field(default_factory=lambda: _env_float("MEXC_FUT_MAKER", 0.0))
    # Gate 公表値 VIP0: スポット 0.2% (GT割引で実質低下)、無期限 テイカー0.05%/メイカー0.02%
    gate_spot_taker: float = field(default_factory=lambda: _env_float("GATE_SPOT_TAKER", 0.002))
    gate_fut_taker: float = field(default_factory=lambda: _env_float("GATE_FUT_TAKER", 0.0005))
    gate_fut_maker: float = field(default_factory=lambda: _env_float("GATE_FUT_MAKER", 0.0002))
    # Bybit 公表値: スポット 0.1%、無期限 テイカー0.055%/メイカー0.02%
    bybit_spot_taker: float = field(default_factory=lambda: _env_float("BYBIT_SPOT_TAKER", 0.001))
    bybit_fut_taker: float = field(default_factory=lambda: _env_float("BYBIT_FUT_TAKER", 0.00055))
    # 国内 (bitFlyer 現物 0.01–0.15%、bitbank テイカー0.12%/メイカー-0.02%)
    bitflyer_spot_taker: float = field(default_factory=lambda: _env_float("BITFLYER_SPOT_TAKER", 0.0015))
    bitbank_spot_taker: float = field(default_factory=lambda: _env_float("BITBANK_SPOT_TAKER", 0.0012))

    # --- リスク上限 (実発注時) ---
    max_order_notional_usdt: float = field(default_factory=lambda: _env_float("EDGEBOT_MAX_ORDER_USDT", 100.0))
    max_total_notional_usdt: float = field(default_factory=lambda: _env_float("EDGEBOT_MAX_TOTAL_USDT", 1000.0))
    min_edge_bps_to_execute: float = field(default_factory=lambda: _env_float("EDGEBOT_MIN_EDGE_BPS", 5.0))

    # --- 出力 ---
    log_dir: str = field(default_factory=lambda: os.environ.get("EDGEBOT_LOG_DIR", "logs"))


CONFIG = Config()
