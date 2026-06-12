# ZAWA Agent

ZAWA Agent is a character-driven Mantle DeFi assistant that compares small-wallet actions, blocks unsafe routes, prepares unsigned transaction data, simulates the result, and leaves final approval to the user.

The app is built as a dependency-free static MVP for hackathon demos. It uses deterministic demo adapters for Merchant Moe, ODOS, INIT Capital, Dolomite, and Hold. No private key, seed phrase, or wallet signature is ever collected by the app.

## Usage

Serve the folder from the repository root:

```bash
python3 -m http.server 4173
```

Open:

```txt
http://localhost:4173
```

Demo flow:

1. Click `Connect Wallet`.
2. Click `Switch to Mantle`.
3. Click `Scan Wallet`.
4. Keep the default Custom policy, or choose `$2 Survival`.
5. Click `Run Agent`.
6. Review the opportunity comparison, selected plan, rejected alternatives, unsigned transactions, and simulation result.
7. Click `Approve in Wallet` to run the simulated confirmation step.

Expected default demo result:

- Wallet: `10 USDC`, `0.4 MNT`
- Policy: max spend `$5`, max gas `$0.30`, max risk `30/100`
- Recommended route: `ODOS` USDC to USDT swap
- Blocked route: Dolomite borrow loop, because borrowing and unlimited approvals are disabled
- Transactions: exact USDC approval, then swap execution
- Simulation: pass, with two wallet signatures required

Try `$2 Survival` mode to see ZAWA recommend `Hold` when gas and risk do not justify spending.

## What The MVP Includes

- Wallet scan screen with address, network, MNT balance, token balance, gas reserve, and risky approval status
- Goal and budget policy controls
- Presets for `$2 Survival`, `Explorer`, and `Custom`
- Deterministic opportunity collection for:
  - Merchant Moe swap
  - ODOS swap
  - INIT Capital supply
  - Dolomite borrow loop
  - Hold / take no action
- Policy blocks for wrong chain, gas limit, spend limit, price impact, risk score, disabled lending, disabled borrowing, unknown contracts, expired quotes, unsupported tokens, and unlimited approvals
- Utility ranking that considers output, expected reward, gas, fees, risk, price impact, budget fit, and the Hold option
- Structured agent plan with ordered steps and rejected alternatives
- Unsigned transaction review with exact approval amount, target contract, minimum output, gas estimate, and calldata preview
- Simulation result with warnings and expected balance changes
- ZAWA expression changes for neutral, warning, despair, thinking, victory, and suspicious states

## Safety Model

ZAWA plans and prepares. The user signs.

The MVP follows these rules:

- Never stores or asks for private keys
- Never signs transactions server-side
- Uses exact token approvals by default
- Blocks unlimited approvals unless the user explicitly enables them
- Blocks unknown contracts and unknown spenders
- Blocks borrowing by default
- Always includes `Hold` as a valid option
- Blocks failed simulations before wallet approval
- Keeps numeric risk and policy decisions deterministic
- Uses the ZAWA persona only to explain decisions, not to invent route data

The current adapters are demo adapters. Before production mainnet use, replace them with verified live protocol adapters, real RPC reads, schema validation, quote expiry checks, and on-chain simulation.

## Architecture

```txt
Wallet State
  -> Demo Protocol Adapters
  -> Normalizer
  -> Deterministic Risk Engine
  -> Policy Guard
  -> Utility Ranking
  -> Strategy Planner
  -> Unsigned Transaction Builder
  -> Simulation Layer
  -> User Review
```

Important files:

- `index.html` - static app shell and workflow screens
- `styles.css` - dashboard layout and responsive UI
- `app.js` - browser interaction and rendering
- `src/zawa-agent-core.mjs` - deterministic agent logic
- `tests/zawa-agent-core.test.mjs` - unit tests for policy, planner, and transaction review
- `scripts/validate-static-app.mjs` - static validation smoke test
- `assets/zawa-spritesheet.webp` - animated ZAWA character atlas
- `video/zawa-agent-pv.mp4` - promotional video asset

## Validation

Run unit tests with Node.js:

```bash
node --test tests/*.test.mjs
```

Run the static app smoke check:

```bash
node scripts/validate-static-app.mjs
```

This repository intentionally has no frontend build step or package dependency. It can be hosted as static files on GitHub Pages, Vercel static hosting, Netlify, or any simple web server.

## Product Positioning

ZAWA Agent is an Agentic Economy consumer DeFi assistant for Mantle. It optimizes for user-specific safety and utility rather than only highest APY or highest quoted output.

Final tagline:

```txt
ZAWA Agent - Find the safest next move on Mantle.
```
