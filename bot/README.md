# edgebot — Market Inefficiency Scanner & Execution Base

A bot foundation for crypto (MEXC spot/futures, Solana DEX, domestic Japanese exchanges) that
measures edges using **real data only**, and rolls out to live trading starting with whichever
edges remain net-positive after fees.

No simulated or dummy values are ever used. Every number the scanner reports is a live measurement
taken from exchange APIs / DEX quotes at run time.

## Operating Flow (Edge Selection)

```
1. Run scan --loop continuously → accumulates into logs/edges-YYYYMMDD.jsonl
2. Run for several days, keep only edges that stay net-positive after fees
3. Place small live orders on surviving edges (--notional ~50) to check slippage / realized edge
4. Once realized matches measured, scale size up gradually and refine the dedicated execution module
```

## Implemented Edges (selected from public botter Advent Calendar staples)

| # | Edge | Description | Execution |
|---|------|-------------|-----------|
| 1 | `funding_arb` | Funding rate carry: delta-neutral spot-long + perp-short collecting funding. Measures annualized rate and breakeven settlement count | Spot leg automated / futures leg semi-automated (see constraint below) |
| 2 | `cross_exchange_arb` | Cross-exchange spot arbitrage: measures MEXC vs Gate/Bybit bid/ask crossing net of both taker fees. Dual-inventory, simultaneous-take approach | Automatable |
| 3 | `cex_dex_arb` | CEX-DEX arbitrage: gap between MEXC order book real-size VWAP and Jupiter (Solana) executable quote, net of Solana fees | CEX side automated / DEX side needs wallet implementation |
| 4 | `triangular_arb` | Triangular arbitrage within MEXC (USDT→X→BTC/ETH/USDC→USDT). Conservative measurement assuming 3 taker legs | Automatable (needs WS low-latency) |
| 5 | `jpy_premium` | Domestic/overseas premium: bitFlyer/bitbank BTC/JPY vs MEXC BTC/USDT × USDJPY | Automatable with dual inventory |

### Key MEXC Operational Constraints

- **0% maker fees** (both spot and futures; many pairs are 0% taker too) → makes thin edges viable,
  so this base defaults to `LIMIT_MAKER` (post-only) orders.
- **The futures order-placement API is not open to retail users** (long-term maintenance status;
  read-only endpoints work fine). The futures leg of the funding carry is handled via
  (a) manual execution in the MEXC app, (b) shorting on Gate/Bybit instead, or
  (c) applying for MEXC's institutional/market-maker futures API access.

## Network Access for Claude Code on the Web

When running in a Claude Code on the Web environment, allow the following domains in the
environment's network policy:

```
api.mexc.com          # MEXC spot
contract.mexc.com     # MEXC futures (read-only)
api.gateio.ws         # Gate spot/futures
api.bybit.com         # Bybit (funding comparison / data only)
lite-api.jup.ag       # Jupiter (Solana DEX quotes)
api.bitflyer.com      # bitFlyer (Japan)
public.bitbank.cc     # bitbank (Japan)
open.er-api.com       # USD/JPY rate
```

## Setup

```bash
cd bot
pip install -r requirements.txt   # only dependency is requests (works with stdlib too)
cp config.example.env .env        # set API keys only if you intend to place live orders
```

### Fastest Start on Windows

```powershell
winget install Python.Python.3.12   # if not already installed
git clone https://github.com/RyoSAKu610/zawazawa.git
cd zawazawa; git checkout claude/crypto-arbitrage-bot-xg6dr8; cd bot
.\run-scan.ps1                       # starts continuous scanning every 60s (Ctrl+C to stop)
```

After running for a few days, run `python -m edgebot report` to get a selection report of
"edges that stay net-positive."

## Usage

```bash
cd bot

# Measure all edges once (no API key needed, read-only)
python -m edgebot scan

# Continuous measurement every 60s, accumulating to JSONL (for checking edge persistence)
python -m edgebot scan --loop 60

# Only specific edges
python -m edgebot scan --only funding_arb,cross_exchange_arb

# MEXC funding rate ranking (annualized)
python -m edgebot funding --top 20

# Funding carry position plan (dry-run: builds the order from real data but doesn't place it)
# Judged on Gate-side funding (the short leg receives it). Delta is matched to Gate's contract size.
python -m edgebot carry BTC_USDT --notional 50

# Live step 1: spot leg (MEXC, LIMIT_MAKER). Only places the order if it passes risk limits
MEXC_API_KEY=... MEXC_API_SECRET=... python -m edgebot carry BTC_USDT --notional 50 --live

# Live step 2: after confirming the spot fill, short leg on Gate (qty must match the spot leg)
GATE_API_KEY=... GATE_API_SECRET=... python -m edgebot short BTC_USDT --qty 0.0005 --live

# Close (short side)
python -m edgebot short BTC_USDT --qty 0.0005 --close --live

# Fully automated both legs: polls for the spot fill and auto-executes the Gate short
# (auto-cancels on timeout, hedges partial fills, kill switch responds immediately)
MEXC_API_KEY=... MEXC_API_SECRET=... GATE_API_KEY=... GATE_API_SECRET=... \
  python -m edgebot carry BTC_USDT --notional 50 --live --auto

# Selection report from scan logs (identifies live-trading candidates)
python -m edgebot report --days 7

# Balance check
python -m edgebot balances
```

## Risk Management

Every live order passes through `executor/risk.py`:

- `EDGEBOT_MAX_ORDER_USDT` — per-order cap (default 50)
- `EDGEBOT_MAX_TOTAL_USDT` — total open notional cap (default 300)
- `EDGEBOT_MIN_EDGE_BPS` — orders below this edge are not placed (default 5bps)
- `EDGEBOT_KILL_SWITCH=1` — immediately halts all order placement

API keys come only from environment variables and are never stored in the repo.
**Use API keys with no withdrawal permission.**

## Tests

```bash
cd bot && python -m unittest discover -s tests -v
```

(Tests cover pure logic only — signing, fee math, risk checks. No market values are simulated.)

## Roadmap

- [ ] Select persistent edges from several days of scan logs (first selection round)
- [x] Add Gate futures client (short-leg execution: `short` command)
- [x] Fully automate both legs of the funding carry (`carry --auto`)
- [ ] Move to WebSocket (MEXC spot WS) to reduce latency for triangular/cross-exchange arb
- [ ] Solana wallet integration (sending Jupiter swaps) to fully automate CEX-DEX arb
- [ ] Thin-book market making on MEXC's 0%-fee pairs (two-sided maker spread capture)
- [ ] Domestic equities (e.g. kabu Station API) considered as a separate future phase

## Sources (Basis for Edge Selection)

- [仮想通貨botter Advent Calendar](https://qiita.com/advent-calendar/2025/botter) (public write-ups of common edges)
- [消えたエッジの話 (2024)](https://qiita.com/chanta/items/158f0d2b63afa2e6935b) (on edge lifespan and decay)
- [MEXC fee schedule](https://www.mexc.com/fee) / [MEXC zero-fee program](https://www.mexc.com/zero-fee)
- [Open-source MEXC 0-fee bot](https://github.com/Neutral-Debug/Mexc-Trading-Bot) (prior art on strict post-only execution)
