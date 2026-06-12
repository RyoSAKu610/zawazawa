import {
  MANTLE_CHAIN_ID,
  MODES,
  clonePolicy,
  confirmPlan,
  createWalletState,
  formatPct,
  formatUsd,
  runAgent,
} from "./src/zawa-agent-core.mjs";

const CELL_WIDTH = 192;
const CELL_HEIGHT = 208;

const spriteStates = {
  neutral: { row: 0, frames: 6, ms: 260 },
  warning: { row: 3, frames: 4, ms: 180 },
  despair: { row: 5, frames: 8, ms: 180 },
  thinking: { row: 8, frames: 6, ms: 220 },
  victory: { row: 4, frames: 5, ms: 150 },
  suspicious: { row: 5, frames: 8, ms: 180 },
  running: { row: 7, frames: 6, ms: 160 },
};

const els = {
  sprite: document.querySelector("#zawaSprite"),
  zawaLine: document.querySelector("#zawaLine"),
  expressionPill: document.querySelector("#expressionPill"),
  connectBtn: document.querySelector("#connectBtn"),
  mantleBtn: document.querySelector("#mantleBtn"),
  scanBtn: document.querySelector("#scanBtn"),
  runBtn: document.querySelector("#runBtn"),
  approveBtn: document.querySelector("#approveBtn"),
  correlationId: document.querySelector("#correlationId"),
  walletAddress: document.querySelector("#walletAddress"),
  walletNetwork: document.querySelector("#walletNetwork"),
  mntBalance: document.querySelector("#mntBalance"),
  usdcBalance: document.querySelector("#usdcBalance"),
  gasStatus: document.querySelector("#gasStatus"),
  approvalStatus: document.querySelector("#approvalStatus"),
  opportunityGrid: document.querySelector("#opportunityGrid"),
  planProtocol: document.querySelector("#planProtocol"),
  planTitle: document.querySelector("#planTitle"),
  planRisk: document.querySelector("#planRisk"),
  planSummary: document.querySelector("#planSummary"),
  planInput: document.querySelector("#planInput"),
  planGas: document.querySelector("#planGas"),
  planNet: document.querySelector("#planNet"),
  planSignatures: document.querySelector("#planSignatures"),
  stepList: document.querySelector("#stepList"),
  rejectedList: document.querySelector("#rejectedList"),
  txList: document.querySelector("#txList"),
  simulationCard: document.querySelector("#simulationCard"),
  simulationStatus: document.querySelector("#simulationStatus"),
  simulationDetails: document.querySelector("#simulationDetails"),
  resultCard: document.querySelector("#resultCard"),
  resultStatus: document.querySelector("#resultStatus"),
  resultMessage: document.querySelector("#resultMessage"),
  resultDetails: document.querySelector("#resultDetails"),
  policyForm: document.querySelector("#policyForm"),
  modeButtons: [...document.querySelectorAll("[data-mode]")],
  fields: {
    totalBudgetUsd: document.querySelector("#totalBudget"),
    maxSpendUsd: document.querySelector("#maxSpend"),
    maxGasUsd: document.querySelector("#maxGas"),
    maxRiskScore: document.querySelector("#maxRisk"),
    maxPriceImpactPct: document.querySelector("#maxImpact"),
    goal: document.querySelector("#goal"),
    allowSwaps: document.querySelector("#allowSwaps"),
    allowLending: document.querySelector("#allowLending"),
    allowBorrowing: document.querySelector("#allowBorrowing"),
    allowTokenApprovals: document.querySelector("#allowApprovals"),
    allowUnlimitedApproval: document.querySelector("#allowUnlimited"),
  },
};

const state = {
  mode: "custom",
  wallet: createWalletState({ connected: false }),
  run: null,
  result: null,
  activeSprite: spriteStates.neutral,
  frame: 0,
};

function setSprite(expression) {
  state.activeSprite = spriteStates[expression] ?? spriteStates.neutral;
  state.frame = 0;
  els.expressionPill.textContent = titleCase(expression);
  paintFrame();
}

function paintFrame() {
  const stateConfig = state.activeSprite;
  const x = -(state.frame % stateConfig.frames) * CELL_WIDTH;
  const y = -stateConfig.row * CELL_HEIGHT;
  els.sprite.style.backgroundPosition = `${x}px ${y}px`;
}

window.setInterval(() => {
  state.frame = (state.frame + 1) % state.activeSprite.frames;
  paintFrame();
}, 150);

function readPolicy() {
  return {
    label: MODES[state.mode].label,
    totalBudgetUsd: numberField("totalBudgetUsd"),
    maxSpendUsd: numberField("maxSpendUsd"),
    maxGasUsd: numberField("maxGasUsd"),
    maxRiskScore: numberField("maxRiskScore"),
    maxPriceImpactPct: numberField("maxPriceImpactPct"),
    goal: els.fields.goal.value,
    allowSwaps: els.fields.allowSwaps.checked,
    allowLending: els.fields.allowLending.checked,
    allowBorrowing: els.fields.allowBorrowing.checked,
    allowTokenApprovals: els.fields.allowTokenApprovals.checked,
    allowUnlimitedApproval: els.fields.allowUnlimitedApproval.checked,
  };
}

function numberField(name) {
  return Number(els.fields[name].value || 0);
}

function writePolicy(policy) {
  els.fields.totalBudgetUsd.value = policy.totalBudgetUsd;
  els.fields.maxSpendUsd.value = policy.maxSpendUsd;
  els.fields.maxGasUsd.value = policy.maxGasUsd;
  els.fields.maxRiskScore.value = policy.maxRiskScore;
  els.fields.maxPriceImpactPct.value = policy.maxPriceImpactPct;
  els.fields.goal.value = policy.goal;
  els.fields.allowSwaps.checked = policy.allowSwaps;
  els.fields.allowLending.checked = policy.allowLending;
  els.fields.allowBorrowing.checked = policy.allowBorrowing;
  els.fields.allowTokenApprovals.checked = policy.allowTokenApprovals;
  els.fields.allowUnlimitedApproval.checked = policy.allowUnlimitedApproval;
}

function runZawa() {
  setSprite("running");
  els.zawaLine.textContent = "Comparing routes... gas, risk, approvals, output, survival odds.";

  window.setTimeout(() => {
    state.run = runAgent({
      wallet: state.wallet,
      policy: readPolicy(),
    });
    state.result = null;
    renderAll();
    setSprite(state.run.zawa.expression);
    els.zawaLine.textContent = state.run.zawa.line;
  }, 220);
}

function renderAll() {
  renderWallet();
  renderPolicyButtons();
  renderOpportunities();
  renderPlan();
  renderReview();
  renderResult();
}

function renderWallet() {
  const wallet = state.wallet;
  const usdc = wallet.tokens.find((token) => token.symbol === "USDC");
  const connected = wallet.connected;
  const onMantle = wallet.chainId === MANTLE_CHAIN_ID;

  els.walletAddress.textContent = connected ? shortenAddress(wallet.address) : "Disconnected";
  els.walletNetwork.textContent = connected ? (onMantle ? "Mantle Mainnet" : `Chain ${wallet.chainId}`) : "Unknown";
  els.mntBalance.textContent = connected
    ? `${wallet.nativeBalanceMnt.toFixed(3)} MNT / ${formatUsd(wallet.nativeBalanceUsd)}`
    : "--";
  els.usdcBalance.textContent = connected && usdc ? formatUsd(usdc.balanceUsd) : "--";
  els.gasStatus.textContent = connected ? (wallet.nativeBalanceUsd >= 0.1 ? "Ready" : "Low reserve") : "--";
  els.approvalStatus.textContent = connected
    ? wallet.allowances.length
      ? `${wallet.allowances.length} risky`
      : "None"
    : "--";

  toggleTone(els.walletNetwork.closest(".metric"), connected && !onMantle, "danger");
  toggleTone(els.gasStatus.closest(".metric"), connected && wallet.nativeBalanceUsd < 0.1, "danger");
  toggleTone(els.approvalStatus.closest(".metric"), connected && wallet.allowances.length > 0, "danger");
}

function renderPolicyButtons() {
  els.modeButtons.forEach((button) => {
    button.classList.toggle("active", button.dataset.mode === state.mode);
  });
}

function renderOpportunities() {
  const opportunities = state.run?.opportunities ?? [];

  if (!opportunities.length) {
    els.opportunityGrid.innerHTML = emptyState("No opportunities yet", "Connect, switch to Mantle, then run the agent.");
    return;
  }

  els.opportunityGrid.innerHTML = opportunities
    .map((opportunity) => {
      const isRecommended =
        state.run.plan.recommendedPlan.sourceOpportunity.id === opportunity.id && opportunity.policyResult.allowed;
      const violations = opportunity.policyResult.violations;
      const reason = violations[0] ?? opportunity.adapterNote;
      const output = opportunity.expectedOutputUsd
        ? `${formatUsd(opportunity.expectedOutputUsd)} ${opportunity.outputToken.symbol}`
        : opportunity.estimatedApyPct
          ? `${formatPct(opportunity.estimatedApyPct)} variable APY`
          : "No output";

      return `
        <article class="opportunity-card ${toneClass(opportunity)} ${isRecommended ? "recommended" : ""}">
          <div class="card-head">
            <div>
              <span>${opportunity.category}</span>
              <h3>${opportunity.protocol}</h3>
            </div>
            <strong>${opportunity.status}</strong>
          </div>
          <dl class="quote-grid">
            <div><dt>Input</dt><dd>${formatUsd(opportunity.inputAmountUsd)}</dd></div>
            <div><dt>Expected</dt><dd>${output}</dd></div>
            <div><dt>Gas</dt><dd>${formatUsd(opportunity.gasCostUsd)}</dd></div>
            <div><dt>Fee</dt><dd>${formatUsd(opportunity.protocolFeeUsd)}</dd></div>
            <div><dt>Impact</dt><dd>${formatPct(opportunity.priceImpactPct)}</dd></div>
            <div><dt>Risk</dt><dd>${opportunity.risk.score}/100</dd></div>
          </dl>
          <p>${reason}</p>
          <div class="utility-row">
            <span>Utility ${opportunity.utility.total}</span>
            <span>${opportunity.risk.level}</span>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderPlan() {
  const plan = state.run?.plan.recommendedPlan;

  if (!plan) {
    els.planProtocol.textContent = "No plan";
    els.planTitle.textContent = "Run the agent";
    els.planRisk.textContent = "--";
    els.planSummary.textContent = "ZAWA has not compared the routes yet.";
    els.planInput.textContent = "--";
    els.planGas.textContent = "--";
    els.planNet.textContent = "--";
    els.planSignatures.textContent = "--";
    els.stepList.innerHTML = "";
    els.rejectedList.innerHTML = emptyListItem("No rejected routes yet.");
    return;
  }

  els.planProtocol.textContent = plan.sourceOpportunity.protocol;
  els.planTitle.textContent = plan.title;
  els.planRisk.textContent = `${plan.totalRiskScore}/100`;
  els.planSummary.textContent = plan.summary;
  els.planInput.textContent = formatUsd(plan.totalInputUsd);
  els.planGas.textContent = formatUsd(plan.estimatedGasUsd);
  els.planNet.textContent = formatUsd(plan.expectedNetBenefitUsd);
  els.planSignatures.textContent = String(plan.signatures);
  els.stepList.innerHTML = plan.steps
    .map(
      (step) => `
        <li>
          <span>${step.order}</span>
          <div>
            <strong>${titleCase(step.action)} - ${step.protocol}</strong>
            <p>${step.description}</p>
          </div>
          <em>${step.requiresSignature ? "Signature" : "No signature"}</em>
        </li>
      `
    )
    .join("");

  els.rejectedList.innerHTML = plan.rejectedAlternatives.length
    ? plan.rejectedAlternatives
        .map(
          (item) => `
            <li>
              <strong>${item.protocol}</strong>
              <span>${item.reason}</span>
            </li>
          `
        )
        .join("")
    : emptyListItem("No rejected alternatives.");
}

function renderReview() {
  const review = state.run?.review;
  const plan = state.run?.plan.recommendedPlan;

  if (!review || !plan) {
    els.txList.innerHTML = emptyState("No unsigned transaction", "Run the agent to prepare review data.");
    els.simulationStatus.textContent = "Waiting";
    els.simulationDetails.textContent = "Run the agent to build unsigned transactions.";
    els.approveBtn.disabled = true;
    return;
  }

  if (!review.transactions.length) {
    els.txList.innerHTML = emptyState("No on-chain action", "The recommended plan is Hold.");
  } else {
    els.txList.innerHTML = review.transactions
      .map(
        (tx) => `
          <article class="tx-card">
            <div class="card-head">
              <div>
                <span>${tx.summary.action}</span>
                <h3>${tx.summary.protocol}</h3>
              </div>
              <strong>${tx.gasEstimate.toLocaleString()} gas</strong>
            </div>
            <dl>
              <div><dt>Target</dt><dd>${shortenAddress(tx.to)}</dd></div>
              <div><dt>Input</dt><dd>${tx.summary.input}</dd></div>
              <div><dt>Minimum output</dt><dd>${tx.summary.minimumOutput ?? "Not required"}</dd></div>
              <div><dt>Approval</dt><dd>${tx.summary.approvalAmount ?? "None"}</dd></div>
              <div><dt>Data</dt><dd>${shortenData(tx.data)}</dd></div>
            </dl>
          </article>
        `
      )
      .join("");
  }

  els.simulationCard.classList.toggle("pass", review.simulation.success);
  els.simulationCard.classList.toggle("fail", !review.simulation.success);
  els.simulationStatus.textContent = review.simulation.success ? "Passed" : "Blocked";
  els.simulationDetails.textContent = simulationText(review);
  els.approveBtn.disabled = !review.simulation.success;
  els.approveBtn.textContent = plan.sourceOpportunity.category === "hold" ? "Accept Hold Plan" : "Approve in Wallet";
}

function renderResult() {
  if (!state.result) {
    els.resultStatus.textContent = "No transaction yet";
    els.resultMessage.textContent = "Final confirmation appears here after wallet approval.";
    els.resultDetails.innerHTML = "";
    els.resultCard.classList.remove("pass", "fail");
    return;
  }

  els.resultStatus.textContent = titleCase(state.result.status);
  els.resultMessage.textContent = state.result.message;
  els.resultCard.classList.toggle("pass", state.result.status === "confirmed" || state.result.status === "held");
  els.resultCard.classList.toggle("fail", state.result.status === "blocked");

  const rows = [];
  if (state.result.txHash) rows.push(["Transaction hash", state.result.txHash]);
  if (state.result.actualGasUsd !== undefined) rows.push(["Actual gas", formatUsd(state.result.actualGasUsd)]);
  if (state.result.updatedWallet) {
    const usdc = state.result.updatedWallet.tokens.find((token) => token.symbol === "USDC");
    const usdt = state.result.updatedWallet.tokens.find((token) => token.symbol === "USDT");
    rows.push(["Updated MNT", `${state.result.updatedWallet.nativeBalanceMnt.toFixed(3)} MNT`]);
    if (usdc) rows.push(["Updated USDC", formatUsd(usdc.balanceUsd)]);
    if (usdt) rows.push(["Updated USDT", formatUsd(usdt.balanceUsd)]);
  }

  els.resultDetails.innerHTML = rows
    .map(([label, value]) => `<div><dt>${label}</dt><dd>${value}</dd></div>`)
    .join("");
}

function approvePlan() {
  if (!state.run) return;

  const outcome = confirmPlan(state.run.plan.recommendedPlan, state.run.review, state.run.context);
  state.result = outcome;

  if (outcome.updatedWallet) {
    state.wallet = outcome.updatedWallet;
  }

  setSprite(outcome.expression);
  els.zawaLine.textContent = outcome.message;
  renderAll();
  document.querySelector("#result").scrollIntoView({ behavior: "smooth", block: "start" });
}

function simulationText(review) {
  if (!review.simulation.success) {
    return review.simulation.revertReason ?? "Simulation failed.";
  }

  const warningText = review.simulation.warnings.length
    ? ` Warnings: ${review.simulation.warnings.join(" ")}`
    : " No warnings.";
  return `Estimated gas ${review.simulation.gasEstimate.toLocaleString()}.${warningText}`;
}

function toneClass(opportunity) {
  if (!opportunity.policyResult.allowed) return "blocked";
  if (opportunity.risk.level === "medium") return "warning";
  if (opportunity.category === "hold") return "hold";
  return "safe";
}

function toggleTone(element, active, className) {
  if (!element) return;
  element.classList.toggle(className, active);
}

function emptyState(title, message) {
  return `
    <div class="empty-state">
      <strong>${title}</strong>
      <span>${message}</span>
    </div>
  `;
}

function emptyListItem(message) {
  return `<li><span>${message}</span></li>`;
}

function shortenAddress(address) {
  if (!address) return "--";
  if (address.length <= 14) return address;
  return `${address.slice(0, 6)}...${address.slice(-4)}`;
}

function shortenData(data) {
  return `${data.slice(0, 14)}...${data.slice(-8)}`;
}

function titleCase(value) {
  return String(value)
    .replace(/[-_]/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

els.connectBtn.addEventListener("click", () => {
  state.wallet = createWalletState({
    connected: true,
    chainId: 1,
    nativeBalanceMnt: 0.4,
    nativeBalanceUsd: 0.33,
    usdcBalanceUsd: 10,
  });
  state.run = null;
  state.result = null;
  setSprite("warning");
  els.zawaLine.textContent = "Wallet detected. Wrong network though. Switch to Mantle before any move.";
  renderAll();
});

els.mantleBtn.addEventListener("click", () => {
  state.wallet = {
    ...state.wallet,
    connected: true,
    chainId: MANTLE_CHAIN_ID,
    address: state.wallet.address || createWalletState().address,
    tokens: state.wallet.tokens.length ? state.wallet.tokens : createWalletState().tokens,
    allowances: state.wallet.allowances.length ? state.wallet.allowances : createWalletState().allowances,
  };
  state.run = null;
  state.result = null;
  setSprite("neutral");
  els.zawaLine.textContent = "Mantle selected. Good. Now compare before signing.";
  renderAll();
});

els.scanBtn.addEventListener("click", () => {
  if (!state.wallet.connected) {
    els.connectBtn.click();
    return;
  }
  setSprite("thinking");
  els.zawaLine.textContent = "Scan complete. 10 USDC, 0.4 MNT, and one risky old approval.";
  renderWallet();
});

els.runBtn.addEventListener("click", runZawa);
els.approveBtn.addEventListener("click", approvePlan);

els.modeButtons.forEach((button) => {
  button.addEventListener("click", () => {
    state.mode = button.dataset.mode;
    writePolicy(clonePolicy(state.mode));
    state.run = null;
    state.result = null;
    setSprite(state.mode === "survival" ? "warning" : "neutral");
    els.zawaLine.textContent =
      state.mode === "survival"
        ? "Two dollars? We survive first. We optimize later."
        : `${MODES[state.mode].label} loaded. Run the agent when ready.`;
    renderAll();
  });
});

els.policyForm.addEventListener("input", () => {
  state.mode = "custom";
  renderPolicyButtons();
});

writePolicy(clonePolicy("custom"));
renderAll();
setSprite("neutral");
