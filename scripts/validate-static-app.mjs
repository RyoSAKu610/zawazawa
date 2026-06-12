import { access, readFile } from "node:fs/promises";
import { constants } from "node:fs";

import { runAgent } from "../src/zawa-agent-core.mjs";

const requiredFiles = [
  "index.html",
  "styles.css",
  "app.js",
  "src/zawa-agent-core.mjs",
  "assets/zawa-spritesheet.webp",
  "assets/zawa-pet.json",
  "README.md",
];

for (const file of requiredFiles) {
  await access(new URL(`../${file}`, import.meta.url), constants.R_OK);
}

const index = await readText("index.html");
const app = await readText("app.js");
const readme = await readText("README.md");
const gitignore = await readText(".gitignore");

mustInclude(index, '<script type="module" src="./app.js"></script>', "index loads the module app");
mustInclude(index, "Opportunity Comparison", "index includes opportunity comparison screen");
mustInclude(app, "./src/zawa-agent-core.mjs", "app imports the deterministic core");
mustInclude(readme, "## Usage", "README includes usage instructions");
mustInclude(readme, "## Safety Model", "README documents the safety model");
mustInclude(gitignore, "video/frames/", "generated video frames are ignored");

const run = runAgent({ now: 1781251200000 });

if (run.plan.recommendedPlan.sourceOpportunity.id !== "odos-usdc-usdt") {
  throw new Error("Expected the default demo run to recommend ODOS.");
}

if (!run.review.simulation.success) {
  throw new Error("Expected the default transaction simulation to pass.");
}

console.log("Static app validation passed.");

async function readText(path) {
  return readFile(new URL(`../${path}`, import.meta.url), "utf8");
}

function mustInclude(text, needle, label) {
  if (!text.includes(needle)) {
    throw new Error(`Missing ${label}.`);
  }
}
