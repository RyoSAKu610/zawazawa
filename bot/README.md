# edgebot — 市場の歪みスキャナ & 実行基盤

クリプト(MEXC 現物/先物・Solana DEX・国内取引所)の**実データだけ**でエッジを計測し、
手数料控除後もプラスが残るエッジから順に実運用へ載せるためのボット基盤。

模擬値・ダミー値は一切使わない。スキャナが出す数字は全て実行時点の取引所API・DEX見積りの実測値。

## 運用フロー(エッジの淘汰)

```
1. scan --loop で常時計測 → logs/edges-YYYYMMDD.jsonl に蓄積
2. 数日回して「手数料控除後プラスが持続する」エッジだけ残す
3. 残ったエッジを小サイズ(--notional 50 程度)で実発注して滑り・実効エッジを確認
4. 実測が計測と一致したらサイズを段階的に上げ、専用実行モジュールを磨く
```

## 実装済みエッジ(botter Advent Calendar 等の公開定番から選定)

| # | エッジ | 内容 | 執行 |
|---|--------|------|------|
| 1 | `funding_arb` | 資金調達率キャリー: 現物ロング+無期限ショートのデルタニュートラルで funding 受取。年率換算・損益分岐回数を実測 | 現物レッグ自動 / 先物レッグ半自動(下記制約) |
| 2 | `cross_exchange_arb` | 取引所間現物アビトラ: MEXC vs Gate/Bybit の bid/ask クロスを両テイカー手数料控除後で計測。両側在庫・同時テイク方式 | 自動化可 |
| 3 | `cex_dex_arb` | CEX-DEX アビトラ: MEXC 板の実サイズVWAP vs Jupiter(Solana)実行可能見積りの乖離。Solana手数料控除 | CEX側自動 / DEX側は要ウォレット実装 |
| 4 | `triangular_arb` | MEXC 内三角アビトラ(USDT→X→BTC/ETH/USDC→USDT)。テイカー3脚前提の保守計測 | 自動化可(要WS低レイテンシ化) |
| 5 | `jpy_premium` | 国内外プレミアム: bitFlyer/bitbank BTC/JPY vs MEXC BTC/USDT×USDJPY | 両側在庫で自動化可 |

### MEXC の重要な実務制約

- **メイカー手数料 0%**(スポット・先物とも。多数ペアはテイカーも0%)→ 薄いエッジでも成立しやすく、本基盤は `LIMIT_MAKER`(post-only)を標準にしている。
- **先物の発注APIは一般ユーザーには開放されていない**(長期メンテナンス扱い。閲覧系は利用可)。
  ファンディングキャリーの先物レッグは (a) MEXC アプリで手動執行、(b) Gate/Bybit でショート、
  (c) MEXC のAPI先物利用申請(機関/MM向け)のいずれかで対応する。

## セットアップ

```bash
cd bot
pip install -r requirements.txt   # requests のみ(無くても標準ライブラリで動く)
cp config.example.env .env        # 実発注する場合のみAPIキーを設定
```

## 使い方

```bash
cd bot

# 全エッジを1回計測(APIキー不要・読み取りのみ)
python -m edgebot scan

# 60秒間隔で常時計測してJSONLへ蓄積(エッジ持続性の検証)
python -m edgebot scan --loop 60

# 特定エッジのみ
python -m edgebot scan --only funding_arb,cross_exchange_arb

# MEXC 資金調達率ランキング(年率換算)
python -m edgebot funding --top 20

# ファンディングキャリー建玉プラン(dry-run: 実データで注文内容を組むだけ)
python -m edgebot carry BTC_USDT --notional 50

# 実発注(現物レッグ。EDGEBOT_MIN_EDGE_BPS 等のリスク上限を通ったときだけ発注)
MEXC_API_KEY=... MEXC_API_SECRET=... python -m edgebot carry BTC_USDT --notional 50 --live

# 残高照会
python -m edgebot balances
```

## リスク管理

全ての実発注は `executor/risk.py` を通る:

- `EDGEBOT_MAX_ORDER_USDT` — 1注文の上限 (デフォルト 100)
- `EDGEBOT_MAX_TOTAL_USDT` — 総建玉上限 (デフォルト 1000)
- `EDGEBOT_MIN_EDGE_BPS` — これ未満のエッジでは発注しない (デフォルト 5bps)
- `EDGEBOT_KILL_SWITCH=1` — 全発注を即時停止

APIキーは環境変数のみ。リポジトリには置かない。**出金権限のないAPIキーを使うこと。**

## テスト

```bash
cd bot && python -m unittest discover -s tests -v
```

(テストは署名・手数料計算・リスク判定など純粋ロジックのみ。市場値の模擬はしない)

## ロードマップ

- [ ] スキャンログ数日分から持続エッジを選定(淘汰第1ラウンド)
- [ ] Gate 先物クライアント追加 → ファンディングキャリー両レッグ全自動化
- [ ] WebSocket 化(MEXC spot WS)で三角/取引所間アビトラのレイテンシ短縮
- [ ] Solana ウォレット統合(Jupiter swap 送信)で CEX-DEX 全自動化
- [ ] MEXC 0%手数料ペアでの薄板MM(メイカー両建てスプレッド取り)
- [ ] 国内株式(kabuステーション等のAPI)は別フェーズで検討

## 情報源(エッジ選定の根拠)

- [仮想通貨botter Advent Calendar](https://qiita.com/advent-calendar/2025/botter)(定番エッジの公開事例)
- [消えたエッジの話(2024)](https://qiita.com/chanta/items/158f0d2b63afa2e6935b)(エッジの寿命と淘汰の考え方)
- [MEXC 手数料一覧](https://www.mexc.com/fee) / [MEXC ゼロ手数料](https://www.mexc.com/zero-fee)
- [MEXC 0手数料市場向けOSSボット](https://github.com/Neutral-Debug/Mexc-Trading-Bot)(post-only 徹底の先行例)
