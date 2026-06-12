import assert from "node:assert/strict";
import test from "node:test";

import {
  MANTLE_CHAIN_ID,
  applyHardPolicies,
  createAgentContext,
  createWalletState,
  runAgent,
  toRiskLevel,
} from "../src/zawa-agent-core.mjs";

test("risk levels follow the deterministic thresholds", () => {
  assert.equal(toRiskLevel(0), "low");
  assert.equal(toRiskLevel(20), "medium");
  assert.equal(toRiskLevel(45), "high");
  assert.equal(toRiskLevel(70), "blocked");
});

test("default demo recommends the ODOS swap route", () => {
  const run = runAgent({ now: 1781251200000 });

  assert.equal(run.context.wallet.chainId, MANTLE_CHAIN_ID);
  assert.equal(run.plan.recommendedPlan.sourceOpportunity.id, "odos-usdc-usdt");
  assert.equal(run.plan.recommendedPlan.signatures, 2);
  assert.equal(run.review.simulation.success, true);
});

test("$2 Survival Mode can recommend Hold instead of spending gas", () => {
  const run = runAgent({
    mode: "survival",
    wallet: createWalletState({
      connected: true,
      chainId: MANTLE_CHAIN_ID,
      nativeBalanceUsd: 0.12,
      usdcBalanceUsd: 2,
    }),
    now: 1781251200000,
  });

  assert.equal(run.plan.recommendedPlan.sourceOpportunity.id, "hold");
  assert.equal(run.plan.recommendedPlan.signatures, 0);
});

test("wrong-chain routes are policy blocked before signing", () => {
  const run = runAgent({
    wallet: createWalletState({ connected: true, chainId: 1 }),
    now: 1781251200000,
  });

  const blocked = run.opportunities.filter((opportunity) =>
    opportunity.policyResult.violations.includes("Wrong chain. Switch to Mantle")
  );

  assert.equal(blocked.length, run.opportunities.length);
  assert.equal(run.zawa.expression, "warning");
});

test("borrowing and unlimited approval stay blocked by default", () => {
  const run = runAgent({ now: 1781251200000 });
  const dolomite = run.opportunities.find((opportunity) => opportunity.id === "dolomite-borrow-loop");

  assert.ok(dolomite);
  assert.equal(dolomite.policyResult.allowed, false);
  assert.match(dolomite.policyResult.violations.join(" | "), /Borrowing is disabled/);
  assert.match(dolomite.policyResult.violations.join(" | "), /Unlimited approval is disabled/);
});

test("transaction review uses exact token approvals", () => {
  const run = runAgent({ now: 1781251200000 });
  const approval = run.review.transactions.find((tx) => tx.summary.action === "Exact token approval");

  assert.ok(approval);
  assert.equal(approval.summary.unlimited, false);
  assert.equal(approval.summary.approvalAmount, "$5.00 USDC");
});

test("expired quotes fail hard policy evaluation", () => {
  const context = createAgentContext({ now: 1781251200000 });
  const opportunity = {
    category: "swap",
    contractAddress: "0x6100000000000000000000000000000000001002",
    inputAmountUsd: 1,
    gasCostUsd: 0.01,
    priceImpactPct: 0.1,
    expiresAt: context.now - 1,
    inputToken: {
      tokenAddress: "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9",
    },
    minimumOutputUsd: 0.98,
    risk: { score: 5 },
  };

  const result = applyHardPolicies(opportunity, context.policy, context);

  assert.equal(result.allowed, false);
  assert.ok(result.violations.includes("Quote is expired"));
});
