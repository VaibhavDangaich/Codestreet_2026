// Capture a CLEAN audit graph (few interactions => readable) for the deck.
const { chromium } = require("playwright");
const path = require("path");
const OUT = path.resolve(__dirname, "../deck/diagrams");

async function main() {
  const browser = await chromium.launch();
  const page = await browser.newPage({
    viewport: { width: 1600, height: 1000 },
    deviceScaleFactor: 2,
  });
  // fresh backend state + fresh audit graph is process-lived; reset members
  try { await page.request.post("http://127.0.0.1:8010/reset"); } catch {}
  await page.goto("http://localhost:3010", { waitUntil: "networkidle" });
  await page.waitForTimeout(2000);

  // two decisions -> two policy rules (FEE-AUTO, LIMIT-CAP) + a few entries
  for (const m of [
    "Please waive my $39 late fee.",
    "Raise my credit limit to $50,000.",
  ]) {
    try {
      await page.getByPlaceholder("Ask the servicing agent…").fill(m);
      await page.getByRole("button", { name: "Send" }).click();
      await page.waitForTimeout(2500);
    } catch {}
  }
  await page.getByRole("button", { name: "Audit graph" }).click();
  await page.waitForTimeout(5000); // let cose settle
  await page.screenshot({ path: path.join(OUT, "ui_graph.png") });
  console.log("saved ui_graph.png (clean)");
  await browser.close();
}
main().catch((e) => { console.error(e); process.exit(1); });
