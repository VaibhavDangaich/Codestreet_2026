// Capture real screenshots of the running app for the deck.
// Usage: node screenshot.cjs   (app must be running on :3010, backend on :8010)
const { chromium } = require("playwright");
const path = require("path");

const OUT = path.resolve(__dirname, "../deck/diagrams");
const URL = "http://localhost:3010";

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 2,
  });
  // reset member state for a clean capture
  try {
    await page.request.post("http://127.0.0.1:8010/reset");
  } catch {}
  await page.goto(URL, { waitUntil: "networkidle" });
  await page.waitForTimeout(2500);

  // populate the chat with a few exchanges (incl. the counterfactual)
  const msgs = [
    "Please waive my $39 late fee, I paid a day late.",
    "I lost my card at the airport, I need a new one asap.",
    "Actually, can you raise my credit limit to $50,000?",
  ];
  for (const m of msgs) {
    try {
      await page.getByPlaceholder("Ask the servicing agent…").fill(m);
      await page.getByRole("button", { name: "Send" }).click();
      await page.waitForTimeout(3000);
    } catch (e) {
      console.log("chat step skipped:", e.message);
    }
  }

  // start a durable case so the Cases tab shows a live saga
  try {
    await page.getByRole("button", { name: "New card" }).click();
    await page.waitForTimeout(3500);
  } catch (e) {
    console.log("case step skipped:", e.message);
  }

  await page.screenshot({ path: path.join(OUT, "ui_main.png") });
  console.log("saved ui_main.png");

  // audit graph tab
  try {
    await page.getByRole("button", { name: "Audit graph" }).click();
    await page.waitForTimeout(4500);
    await page.screenshot({ path: path.join(OUT, "ui_graph.png") });
    console.log("saved ui_graph.png");
  } catch (e) {
    console.log("graph step skipped:", e.message);
  }

  // audit trail tab
  try {
    await page.getByRole("button", { name: "Audit trail" }).click();
    await page.waitForTimeout(1500);
    await page.screenshot({ path: path.join(OUT, "ui_audit.png") });
    console.log("saved ui_audit.png");
  } catch (e) {
    console.log("audit step skipped:", e.message);
  }

  await browser.close();
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
