export const MANTLE_CHAIN_ID = 5000;
export const DEMO_WALLET = "0x6100a7aa0000000000000000000000000000cafe";

export const TOKENS = {
  MNT: {
    symbol: "MNT",
    decimals: 18,
    tokenAddress: "native",
  },
  USDC: {
    symbol: "USDC",
    decimals: 6,
    tokenAddress: "0x09bc4e0d864854c6afb6eb9a9cdf58ac190d0df9",
  },
  USDT: {
    symbol: "USDT",
    decimals: 6,
    tokenAddress: "0x201eba5cc46d216ce6dc03f6a759e8e766e956ae",
  },
};

export const CONTRACTS = {
  MERCHANT_MOE_ROUTER: "0x6100000000000000000000000000000000001001",
  ODOS_ROUTER: "0x6100000000000000000000000000000000001002",
  INIT_POOL: "0x6100000000000000000000000000000000002001",
  DOLOMITE_MARGIN: "0x6100000000000000000000000000000000003001",
  UNKNOWN_REWARD_CLAIM: "0x610000000000000000000000000000000000bad0",
};

export const CONTRACT_ALLOWLIST = new Set([
  CONTRACTS.MERCHANT_MOE_ROUTER,
  CONTRACTS.ODOS_ROUTER,
  CONTRACTS.INIT_POOL,
]);

export const MODES = {
  survival: {
    label: "$2 Survival Mode",
    totalBudgetUsd: 2,
    maxSpendUsd: 0.75,
    maxGasUsd: 0.1,
    maxPriceImpactPct: 1,
    maxRiskScore: 20,
    goal: "learn",
    allowSwaps: true,
    allowLending: false,
    allowBorrowing: false,
    allowTokenApprovals: true,
    allowUnlimitedApproval: false,
  },
  explorer: {
    label: "Explorer Mode",
    totalBudgetUsd: 50,
    maxSpendUsd: 15,
    maxGasUsd: 0.3,
    maxPriceImpactPct: 1,
    maxRiskScore: 35,
    goal: "explore",
    allowSwaps: true,
    allowLending: true,
    allowBorrowing: false,
    allowTokenApprovals: true,
    allowUnlimitedApproval: false,
  },
  custom: {
    label: "Custom Demo Mode",
    totalBudgetUsd: 10,
    maxSpendUsd: 5,
    maxGasUsd: 0.3,
    maxPriceImpactPct: 1,
    maxRiskScore: 30,
    goal: "earn",
    allowSwaps: true,
    allowLending: true,
    allowBorrowing: false,
    allowTokenApprovals: true,
    allowUnlimitedApproval: false,
  },
};

export function clonePolicy(mode = "custom") {
  return { ...MODES[mode] };
}

export function createWalletState(options = {}) {
  const {
    connected = true,
    chainId = MANTLE_CHAIN_ID,
    nativeBalanceMnt = 0.4,
    nativeBalanceUsd = 0.33,
    usdcBalanceUsd = 10,
    riskyApproval = true,
  } = options;

  return {
    connected,
    address: connected ? DEMO_WALLET : "",
    chainId,
    nativeBalanceMnt,
    nativeBalanceUsd,
    tokens: connected
      ? [
          {
            ...TOKENS.USDC,
            balance: usdcBalanceUsd,
            balanceUsd: usdcBalanceUsd,
          },
          {
            ...TOKENS.USDT,
            balance: 0,
            balanceUsd: 0,
          },
        ]
      : [],
    allowances:
      connected && riskyApproval
        ? [
            {
              tokenAddress: TOKENS.USDC.tokenAddress,
              spender: CONTRACTS.UNKNOWN_REWARD_CLAIM,
              amountUsd: 999999,
              unlimited: true,
              protocol: "Unknown reward claim",
            },
          ]
        : [],
    fetchedAt: Date.now(),
  };
}

export function formatUsd(value, digits = 2) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(number);
}

export function formatPct(value) {
  return `${Number(value || 0).toFixed(2)}%`;
}

export function toRiskLevel(score) {
  if (score >= 70) return "blocked";
  if (score >= 45) return "high";
  if (score >= 20) return "medium";
  return "low";
}

export function getUsdcBalance(wallet) {
  return wallet.tokens.find((token) => token.symbol === "USDC")?.balanceUsd ?? 0;
}

export function getSpendAmount(policy, wallet) {
  const availableUsdc = getUsdcBalance(wallet);
  const requested = Math.min(policy.maxSpendUsd, policy.totalBudgetUsd, availableUsdc);
  return Math.max(0, roundUsd(requested));
}

export function createAgentContext(options = {}) {
  const policy = {
    ...clonePolicy(options.mode ?? "custom"),
    ...(options.policy ?? {}),
  };

  return {
    wallet: options.wallet ?? createWalletState(),
    policy,
    supportedTokens: [TOKENS.USDC.tokenAddress, TOKENS.USDT.tokenAddress],
    now: options.now ?? Date.now(),
    correlationId: options.correlationId ?? makeCorrelationId(),
  };
}

export function collectOpportunities(context) {
  const spend = getSpendAmount(context.policy, context.wallet);
  const now = context.now;

  const candidates = [
    {
      id: "merchant-moe-usdc-usdt",
      protocol: "Merchant Moe",
      category: "swap",
      action: "Swap USDC to USDT",
      inputToken: TOKENS.USDC,
      outputToken: TOKENS.USDT,
      inputAmountUsd: spend,
      expectedOutputUsd: roundUsd(spend * 0.992),
      minimumOutputUsd: roundUsd(spend * 0.986),
      expectedRewardUsd: roundUsd(spend * 0.21),
      gasCostUsd: 0.04,
      protocolFeeUsd: roundUsd(spend * 0.001),
      priceImpactPct: 0.31,
      routeComplexity: 2,
      liquidityUsd: 1800000,
      contractAddress: CONTRACTS.MERCHANT_MOE_ROUTER,
      contractAllowlisted: true,
      quoteIssuedAt: now,
      expiresAt: now + 90000,
      approval: {
        spender: CONTRACTS.MERCHANT_MOE_ROUTER,
        amountUsd: spend,
        unlimited: false,
      },
      simulationProfile: "safe",
      adapterStatus: "Safe",
      adapterNote: "Direct allowlisted swap route with exact approval.",
      riskInputs: {
        contract: 1,
        liquidity: 2,
        priceImpact: 2,
        approval: 4,
        complexity: 3,
        smartContract: 4,
        volatility: 2,
        lockup: 0,
      },
    },
    {
      id: "odos-usdc-usdt",
      protocol: "ODOS",
      category: "swap",
      action: "Swap USDC to USDT",
      inputToken: TOKENS.USDC,
      outputToken: TOKENS.USDT,
      inputAmountUsd: spend,
      expectedOutputUsd: roundUsd(spend * 0.998),
      minimumOutputUsd: roundUsd(spend * 0.992),
      expectedRewardUsd: roundUsd(spend * 0.23),
      gasCostUsd: 0.05,
      protocolFeeUsd: roundUsd(spend * 0.001),
      priceImpactPct: 0.22,
      routeComplexity: 3,
      liquidityUsd: 2800000,
      contractAddress: CONTRACTS.ODOS_ROUTER,
      contractAllowlisted: true,
      quoteIssuedAt: now,
      expiresAt: now + 90000,
      approval: {
        spender: CONTRACTS.ODOS_ROUTER,
        amountUsd: spend,
        unlimited: false,
      },
      simulationProfile: "safe",
      adapterStatus: "Recommended",
      adapterNote: "Best net output inside budget, gas, and risk limits.",
      riskInputs: {
        contract: 1,
        liquidity: 1,
        priceImpact: 2,
        approval: 4,
        complexity: 3,
        smartContract: 4,
        volatility: 2,
        lockup: 0,
      },
    },
    {
      id: "init-usdc-supply",
      protocol: "INIT Capital",
      category: "lend",
      action: "Supply USDC",
      inputToken: TOKENS.USDC,
      outputToken: TOKENS.USDC,
      inputAmountUsd: spend,
      expectedOutputUsd: undefined,
      minimumOutputUsd: undefined,
      expectedRewardUsd: roundUsd(spend * 0.085),
      estimatedApyPct: 6.8,
      gasCostUsd: 0.07,
      protocolFeeUsd: 0,
      priceImpactPct: 0,
      routeComplexity: 4,
      liquidityUsd: 900000,
      lockupDays: 0,
      contractAddress: CONTRACTS.INIT_POOL,
      contractAllowlisted: true,
      quoteIssuedAt: now,
      expiresAt: now + 120000,
      approval: {
        spender: CONTRACTS.INIT_POOL,
        amountUsd: spend,
        unlimited: false,
      },
      simulationProfile: "warning",
      adapterStatus: "Acceptable",
      adapterNote: "Lending is allowed only outside Survival Mode.",
      riskInputs: {
        contract: 2,
        liquidity: 3,
        priceImpact: 0,
        approval: 4,
        complexity: 5,
        smartContract: 8,
        volatility: 2,
        lockup: 2,
      },
    },
    {
      id: "dolomite-borrow-loop",
      protocol: "Dolomite",
      category: "borrow",
      action: "Borrow loop",
      inputToken: TOKENS.USDC,
      outputToken: TOKENS.USDC,
      inputAmountUsd: spend,
      expectedOutputUsd: undefined,
      minimumOutputUsd: undefined,
      expectedRewardUsd: roundUsd(spend * 0.31),
      estimatedApyPct: 18.4,
      gasCostUsd: 0.14,
      protocolFeeUsd: 0.02,
      priceImpactPct: 0,
      routeComplexity: 8,
      liquidityUsd: 650000,
      lockupDays: 0,
      contractAddress: CONTRACTS.DOLOMITE_MARGIN,
      contractAllowlisted: false,
      quoteIssuedAt: now,
      expiresAt: now + 120000,
      approval: {
        spender: CONTRACTS.DOLOMITE_MARGIN,
        amountUsd: Number.POSITIVE_INFINITY,
        unlimited: true,
      },
      simulationProfile: "blocked",
      adapterStatus: "Blocked",
      adapterNote: "Borrowing, liquidation risk, and unknown spender are blocked.",
      riskInputs: {
        contract: 10,
        liquidity: 5,
        priceImpact: 0,
        approval: 15,
        complexity: 10,
        smartContract: 10,
        volatility: 10,
        lockup: 5,
      },
    },
    {
      id: "hold",
      protocol: "ZAWA",
      category: "hold",
      action: "Hold / take no action",
      inputToken: undefined,
      outputToken: undefined,
      inputAmountUsd: 0,
      expectedOutputUsd: 0,
      minimumOutputUsd: 0,
      expectedRewardUsd: 0,
      gasCostUsd: 0,
      protocolFeeUsd: 0,
      priceImpactPct: 0,
      routeComplexity: 0,
      liquidityUsd: undefined,
      contractAddress: undefined,
      contractAllowlisted: true,
      quoteIssuedAt: now,
      expiresAt: now + 86400000,
      approval: undefined,
      simulationProfile: "safe",
      adapterStatus: "Always available",
      adapterNote: "Doing nothing stays valid when cost or risk is not worth it.",
      riskInputs: {
        contract: 0,
        liquidity: 0,
        priceImpact: 0,
        approval: 0,
        complexity: 0,
        smartContract: 0,
        volatility: 0,
        lockup: 0,
      },
    },
  ];

  return candidates.map((candidate) => normalizeOpportunity(candidate, context));
}

export function normalizeOpportunity(candidate, context) {
  const risk = assessRisk(candidate);
  const policyResult = applyHardPolicies({ ...candidate, risk }, context.policy, context);
  const utility = calculateUtilityScore({ ...candidate, risk }, context.policy);
  const status = resolveOpportunityStatus(candidate, risk, policyResult);

  return {
    ...candidate,
    risk,
    policyResult,
    utility,
    status,
  };
}

export function assessRisk(opportunity) {
  const components = { ...opportunity.riskInputs };
  const hardBlocks = [];

  if (!opportunity.contractAllowlisted && opportunity.category !== "hold") {
    hardBlocks.push("Contract is not on the demo allowlist");
  }

  if (opportunity.approval?.unlimited) {
    hardBlocks.push("Unlimited approval requested");
  }

  const score = Object.values(components).reduce((sum, value) => sum + value, 0);

  return {
    score,
    level: toRiskLevel(score),
    reasons: riskReasonList(opportunity, components),
    hardBlocks,
    components,
  };
}

export function applyHardPolicies(opportunity, profile, context = {}) {
  const violations = [];
  const wallet = context.wallet;
  const supportedTokens = context.supportedTokens ?? [];
  const now = context.now ?? Date.now();

  if (wallet && !wallet.connected) {
    violations.push("Wallet is not connected");
  }

  if (wallet && wallet.chainId !== MANTLE_CHAIN_ID) {
    violations.push("Wrong chain. Switch to Mantle");
  }

  if (
    opportunity.category !== "hold" &&
    opportunity.contractAddress &&
    !CONTRACT_ALLOWLIST.has(opportunity.contractAddress)
  ) {
    violations.push("Contract is not allowlisted");
  }

  if (opportunity.expiresAt && opportunity.expiresAt <= now) {
    violations.push("Quote is expired");
  }

  if (opportunity.inputAmountUsd > profile.maxSpendUsd) {
    violations.push("Action exceeds maximum spend");
  }

  if (opportunity.gasCostUsd > profile.maxGasUsd) {
    violations.push("Gas cost exceeds user limit");
  }

  if (
    opportunity.priceImpactPct !== undefined &&
    opportunity.priceImpactPct > profile.maxPriceImpactPct
  ) {
    violations.push("Price impact exceeds user limit");
  }

  if (opportunity.risk.score > profile.maxRiskScore) {
    violations.push("Risk score exceeds user limit");
  }

  if (opportunity.category === "borrow" && !profile.allowBorrowing) {
    violations.push("Borrowing is disabled");
  }

  if (opportunity.category === "lend" && !profile.allowLending) {
    violations.push("Lending is disabled");
  }

  if (opportunity.category === "swap" && !profile.allowSwaps) {
    violations.push("Swaps are disabled");
  }

  if (opportunity.approval && !profile.allowTokenApprovals) {
    violations.push("Token approvals are disabled");
  }

  if (opportunity.approval?.unlimited && !profile.allowUnlimitedApproval) {
    violations.push("Unlimited approval is disabled");
  }

  if (
    opportunity.inputToken?.tokenAddress &&
    !supportedTokens.includes(opportunity.inputToken.tokenAddress)
  ) {
    violations.push("Unsupported input token");
  }

  if (wallet && opportunity.gasCostUsd > 0 && wallet.nativeBalanceUsd < opportunity.gasCostUsd + 0.03) {
    violations.push("Insufficient MNT gas reserve");
  }

  if (opportunity.category === "swap" && !opportunity.minimumOutputUsd) {
    violations.push("Swap is missing minimum output");
  }

  return {
    allowed: violations.length === 0,
    violations,
  };
}

export function calculateUtilityScore(opportunity, profile) {
  const rewardScore = Math.min(opportunity.expectedRewardUsd * 8, 30);
  const outputScore = Math.min(opportunity.expectedOutputUsd ?? 0, 20);
  const gasPenalty = opportunity.gasCostUsd * 20;
  const feePenalty = opportunity.protocolFeeUsd * 10;
  const riskPenalty = opportunity.risk.score * 0.55;
  const priceImpactPenalty = (opportunity.priceImpactPct ?? 0) * 8;
  const budgetFit = opportunity.inputAmountUsd <= profile.maxSpendUsd ? 20 : -100;
  const holdBonus = opportunity.category === "hold" && profile.goal === "preserve" ? 25 : 0;
  const survivalPenalty =
    profile.totalBudgetUsd <= 2 && opportunity.category !== "hold" ? 8 : 0;

  const total =
    rewardScore +
    outputScore +
    budgetFit +
    holdBonus -
    gasPenalty -
    feePenalty -
    riskPenalty -
    priceImpactPenalty -
    survivalPenalty;

  return {
    total: roundScore(total),
    components: {
      rewardScore: roundScore(rewardScore),
      outputScore: roundScore(outputScore),
      gasPenalty: roundScore(-gasPenalty),
      feePenalty: roundScore(-feePenalty),
      riskPenalty: roundScore(-riskPenalty),
      priceImpactPenalty: roundScore(-priceImpactPenalty),
      budgetFit,
      holdBonus,
      survivalPenalty: -survivalPenalty,
    },
  };
}

export function createPlan(context, opportunities) {
  const hold = opportunities.find((opportunity) => opportunity.category === "hold");
  const allowed = opportunities
    .filter((opportunity) => opportunity.policyResult.allowed && opportunity.risk.level !== "blocked")
    .sort((a, b) => b.utility.total - a.utility.total);

  let selected = allowed[0] ?? hold;

  if (!selected || selected.utility.total <= 0) {
    selected = hold;
  }

  if (hold && selected.id !== "hold" && selected.utility.total <= hold.utility.total) {
    selected = hold;
  }

  const recommendedPlan = buildPlanFromOpportunity(selected, opportunities, context);
  const alternatives = allowed
    .filter((opportunity) => opportunity.id !== selected.id)
    .slice(0, 2)
    .map((opportunity) => buildPlanFromOpportunity(opportunity, opportunities, context));

  return {
    recommendedPlan,
    alternatives,
    rejected: opportunities.filter((opportunity) => !opportunity.policyResult.allowed),
  };
}

export function buildPlanFromOpportunity(opportunity, allOpportunities, context) {
  const rejectedAlternatives = allOpportunities
    .filter((candidate) => candidate.id !== opportunity.id && !candidate.policyResult.allowed)
    .map((candidate) => ({
      opportunityId: candidate.id,
      protocol: candidate.protocol,
      reason: candidate.policyResult.violations[0] ?? "Policy rejected this route",
    }));

  if (opportunity.category === "hold") {
    return {
      id: `${context.correlationId}-hold`,
      opportunityId: opportunity.id,
      title: "Hold and protect the gas reserve",
      summary: "No on-chain action is better than paying for a weak move.",
      totalInputUsd: 0,
      estimatedGasUsd: 0,
      expectedNetBenefitUsd: 0,
      totalRiskScore: 0,
      signatures: 0,
      steps: [
        {
          id: "hold-1",
          order: 1,
          action: "hold",
          protocol: "ZAWA",
          description: "Keep funds untouched and revisit when a route beats gas and risk.",
          estimatedGasUsd: 0,
          riskScore: 0,
          requiresSignature: false,
        },
      ],
      rejectedAlternatives,
      sourceOpportunity: opportunity,
    };
  }

  const steps = [];
  let order = 1;

  if (opportunity.approval) {
    steps.push({
      id: `${opportunity.id}-approval`,
      order,
      action: "approve",
      protocol: opportunity.protocol,
      description: `Approve exactly ${formatUsd(opportunity.approval.amountUsd)} ${opportunity.inputToken.symbol}`,
      estimatedGasUsd: roundUsd(opportunity.gasCostUsd * 0.35),
      riskScore: opportunity.risk.score,
      requiresSignature: true,
    });
    order += 1;
  }

  steps.push({
    id: `${opportunity.id}-main`,
    order,
    action: opportunity.category === "lend" ? "lend" : "swap",
    protocol: opportunity.protocol,
    description:
      opportunity.category === "lend"
        ? `Supply ${formatUsd(opportunity.inputAmountUsd)} ${opportunity.inputToken.symbol}`
        : `Swap ${formatUsd(opportunity.inputAmountUsd)} ${opportunity.inputToken.symbol} through ${opportunity.protocol}`,
    estimatedGasUsd: roundUsd(opportunity.gasCostUsd * 0.65),
    riskScore: opportunity.risk.score,
    requiresSignature: true,
  });

  steps.push({
    id: `${opportunity.id}-reserve`,
    order: order + 1,
    action: "hold",
    protocol: "Wallet",
    description: "Keep the remaining wallet balance untouched.",
    estimatedGasUsd: 0,
    riskScore: 0,
    requiresSignature: false,
  });

  return {
    id: `${context.correlationId}-${opportunity.id}`,
    opportunityId: opportunity.id,
    title:
      opportunity.category === "lend"
        ? `Supply with ${opportunity.protocol}`
        : `Swap through ${opportunity.protocol}`,
    summary: planSummary(opportunity),
    totalInputUsd: opportunity.inputAmountUsd,
    estimatedGasUsd: opportunity.gasCostUsd,
    expectedNetBenefitUsd: roundUsd(
      (opportunity.expectedOutputUsd ?? opportunity.inputAmountUsd + opportunity.expectedRewardUsd) -
        opportunity.inputAmountUsd -
        opportunity.gasCostUsd -
        opportunity.protocolFeeUsd
    ),
    totalRiskScore: opportunity.risk.score,
    signatures: steps.filter((step) => step.requiresSignature).length,
    steps,
    rejectedAlternatives,
    sourceOpportunity: opportunity,
  };
}

export function buildTransactions(plan, context) {
  const opportunity = plan.sourceOpportunity;

  if (!opportunity || opportunity.category === "hold") {
    return {
      transactions: [],
      simulation: {
        success: true,
        gasEstimate: 0,
        warnings: ["No signature is required for holding."],
        balanceChanges: [],
      },
    };
  }

  const transactions = [];

  if (opportunity.approval) {
    transactions.push({
      id: `${opportunity.id}-approve`,
      chainId: MANTLE_CHAIN_ID,
      from: context.wallet.address,
      to: opportunity.inputToken.tokenAddress,
      data: makeCalldata("approve", opportunity.approval.spender, opportunity.approval.amountUsd),
      value: "0",
      gasEstimate: 42000,
      summary: {
        action: "Exact token approval",
        protocol: opportunity.protocol,
        input: `${formatUsd(opportunity.approval.amountUsd)} ${opportunity.inputToken.symbol}`,
        approvalAmount: `${formatUsd(opportunity.approval.amountUsd)} ${opportunity.inputToken.symbol}`,
        spender: opportunity.approval.spender,
        token: opportunity.inputToken.tokenAddress,
        unlimited: opportunity.approval.unlimited,
      },
    });
  }

  transactions.push({
    id: `${opportunity.id}-execute`,
    chainId: MANTLE_CHAIN_ID,
    from: context.wallet.address,
    to: opportunity.contractAddress,
    data: makeCalldata(opportunity.category, opportunity.id, opportunity.minimumOutputUsd ?? 0),
    value: "0",
    gasEstimate: opportunity.category === "lend" ? 112000 : 97000,
    summary: {
      action: opportunity.action,
      protocol: opportunity.protocol,
      input: `${formatUsd(opportunity.inputAmountUsd)} ${opportunity.inputToken.symbol}`,
      expectedOutput: opportunity.expectedOutputUsd
        ? `${formatUsd(opportunity.expectedOutputUsd)} ${opportunity.outputToken.symbol}`
        : opportunity.estimatedApyPct
          ? `${formatPct(opportunity.estimatedApyPct)} variable APY`
          : undefined,
      minimumOutput: opportunity.minimumOutputUsd
        ? `${formatUsd(opportunity.minimumOutputUsd)} ${opportunity.outputToken.symbol}`
        : undefined,
      approvalAmount: opportunity.approval
        ? `${formatUsd(opportunity.approval.amountUsd)} ${opportunity.inputToken.symbol}`
        : undefined,
      deadline: new Date(opportunity.expiresAt).toISOString(),
    },
  });

  return {
    transactions,
    simulation: simulateTransactions(transactions, plan, context),
  };
}

export function simulateTransactions(transactions, plan, context) {
  const warnings = [];

  if (!context.wallet.connected) {
    return {
      success: false,
      gasEstimate: 0,
      revertReason: "Wallet is not connected",
      warnings: ["No wallet, no simulation."],
      balanceChanges: [],
    };
  }

  if (context.wallet.chainId !== MANTLE_CHAIN_ID) {
    return {
      success: false,
      gasEstimate: 0,
      revertReason: "Wrong chain",
      warnings: ["Simulation blocked before signing."],
      balanceChanges: [],
    };
  }

  const hasUnlimitedApproval = transactions.some((tx) => tx.summary.unlimited);
  if (hasUnlimitedApproval) {
    return {
      success: false,
      gasEstimate: 0,
      revertReason: "Unlimited approval blocked",
      warnings: ["Exact approval policy rejected the transaction."],
      balanceChanges: [],
    };
  }

  if (plan.sourceOpportunity?.policyResult.allowed === false) {
    return {
      success: false,
      gasEstimate: 0,
      revertReason: plan.sourceOpportunity.policyResult.violations.join("; "),
      warnings: ["Policy guard blocked this route."],
      balanceChanges: [],
    };
  }

  if (transactions.length > 1) {
    warnings.push("Two wallet signatures are required: approval, then action.");
  }

  const opportunity = plan.sourceOpportunity;
  const balanceChanges =
    opportunity.category === "swap"
      ? [
          { token: opportunity.inputToken.symbol, amount: `-${formatUsd(opportunity.inputAmountUsd)}` },
          { token: opportunity.outputToken.symbol, amount: `+${formatUsd(opportunity.expectedOutputUsd)}` },
          { token: "MNT gas", amount: `-${formatUsd(opportunity.gasCostUsd)}` },
        ]
      : [
          { token: opportunity.inputToken.symbol, amount: `-${formatUsd(opportunity.inputAmountUsd)}` },
          { token: "Supply position", amount: `+${formatUsd(opportunity.inputAmountUsd)}` },
          { token: "MNT gas", amount: `-${formatUsd(opportunity.gasCostUsd)}` },
        ];

  return {
    success: true,
    gasEstimate: transactions.reduce((sum, tx) => sum + tx.gasEstimate, 0),
    warnings,
    balanceChanges,
  };
}

export function confirmPlan(plan, review, context) {
  if (!review.simulation.success) {
    return {
      status: "blocked",
      expression: "suspicious",
      message: "Simulation failed. The transaction does not leave this screen.",
    };
  }

  if (plan.sourceOpportunity.category === "hold") {
    return {
      status: "held",
      expression: "neutral",
      message: "No move beats holding right now. Doing nothing is the winning action.",
      updatedWallet: context.wallet,
    };
  }

  const hash = makeDemoHash(plan.id);
  const updatedWallet = applyBalanceChanges(plan.sourceOpportunity, context.wallet);

  return {
    status: "confirmed",
    expression: "victory",
    txHash: hash,
    actualGasUsd: plan.estimatedGasUsd,
    message: "Confirmed... no hidden leverage, no reckless approval, no unnecessary loss.",
    updatedWallet,
  };
}

export function runAgent(options = {}) {
  const context = createAgentContext(options);
  const opportunities = collectOpportunities(context);
  const plan = createPlan(context, opportunities);
  const review = buildTransactions(plan.recommendedPlan, context);
  const zawa = explainDecision(plan.recommendedPlan, opportunities, review, context);

  return {
    context,
    opportunities,
    plan,
    review,
    zawa,
  };
}

export function explainDecision(plan, opportunities, review, context) {
  if (!context.wallet.connected) {
    return {
      expression: "warning",
      line: "Connect first. I cannot protect a wallet I cannot see.",
    };
  }

  if (context.wallet.chainId !== MANTLE_CHAIN_ID) {
    return {
      expression: "warning",
      line: "Wrong network. Stop. Switch to Mantle before any signature.",
    };
  }

  if (!review.simulation.success) {
    return {
      expression: "suspicious",
      line: "Simulation failed. The transaction does not leave this screen.",
    };
  }

  if (plan.sourceOpportunity.category === "hold") {
    return {
      expression: "despair",
      line: "No move beats holding right now. Painful... but safe.",
    };
  }

  const blocked = opportunities.filter((opportunity) => !opportunity.policyResult.allowed).length;
  return {
    expression: "thinking",
    line: `${opportunities.length} paths found. ${blocked} blocked. ${plan.sourceOpportunity.protocol} gives the best safe route inside your limits.`,
  };
}

function resolveOpportunityStatus(opportunity, risk, policyResult) {
  if (!policyResult.allowed) return "Blocked";
  if (opportunity.category === "hold") return "Available";
  if (risk.level === "low") return opportunity.adapterStatus;
  if (risk.level === "medium") return "Needs review";
  return "High risk";
}

function riskReasonList(opportunity, components) {
  const reasons = [];

  if (components.approval > 0) {
    reasons.push(opportunity.approval?.unlimited ? "Unlimited approval exposure" : "Exact token approval required");
  }

  if (components.smartContract >= 8) {
    reasons.push("Higher smart-contract exposure");
  }

  if (components.complexity >= 8) {
    reasons.push("Complex multi-step route");
  }

  if (components.priceImpact > 0) {
    reasons.push(`Price impact ${formatPct(opportunity.priceImpactPct)}`);
  }

  if (opportunity.category === "hold") {
    reasons.push("No contract interaction");
  }

  return reasons;
}

function planSummary(opportunity) {
  if (opportunity.category === "swap") {
    return `${opportunity.protocol} returns ${formatUsd(opportunity.expectedOutputUsd)} before gas with ${formatPct(
      opportunity.priceImpactPct
    )} price impact.`;
  }

  if (opportunity.category === "lend") {
    return `${opportunity.protocol} can earn a variable ${formatPct(
      opportunity.estimatedApyPct
    )} APY, but lending risk remains visible.`;
  }

  return opportunity.adapterNote;
}

function applyBalanceChanges(opportunity, wallet) {
  const usdcBalance = getUsdcBalance(wallet);
  const updatedTokens = wallet.tokens.map((token) => {
    if (token.symbol === "USDC") {
      const balanceUsd =
        opportunity.category === "swap"
          ? roundUsd(usdcBalance - opportunity.inputAmountUsd)
          : roundUsd(usdcBalance - opportunity.inputAmountUsd);
      return { ...token, balance: balanceUsd, balanceUsd };
    }

    if (token.symbol === "USDT" && opportunity.category === "swap") {
      const balanceUsd = roundUsd(token.balanceUsd + opportunity.expectedOutputUsd);
      return { ...token, balance: balanceUsd, balanceUsd };
    }

    return token;
  });

  return {
    ...wallet,
    nativeBalanceUsd: roundUsd(wallet.nativeBalanceUsd - opportunity.gasCostUsd),
    nativeBalanceMnt: roundUsd(wallet.nativeBalanceMnt - opportunity.gasCostUsd / 0.82),
    tokens: updatedTokens,
    fetchedAt: Date.now(),
  };
}

function roundUsd(value) {
  return Math.round((Number(value) + Number.EPSILON) * 100) / 100;
}

function roundScore(value) {
  return Math.round((Number(value) + Number.EPSILON) * 10) / 10;
}

function makeCorrelationId() {
  return `zawa-${Math.random().toString(16).slice(2, 8)}-${Date.now().toString(36)}`;
}

function makeCalldata(...parts) {
  const input = parts.join(":");
  let hex = "";

  for (let index = 0; index < input.length; index += 1) {
    hex += input.charCodeAt(index).toString(16).padStart(2, "0");
  }

  return `0x${hex.padEnd(96, "0").slice(0, 96)}`;
}

function makeDemoHash(seed) {
  let hash = 2166136261;

  for (let index = 0; index < seed.length; index += 1) {
    hash ^= seed.charCodeAt(index);
    hash = Math.imul(hash, 16777619);
  }

  const hex = (hash >>> 0).toString(16).padStart(8, "0");
  return `0x${hex.repeat(8)}`;
}
