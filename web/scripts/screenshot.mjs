/**
 * Screenshot the board for visual review.
 *
 * The board is a 3D scene, so typechecking and unit tests say nothing about
 * whether it actually renders. This drives the real page in a real browser
 * and writes PNGs to look at.
 *
 * Both servers must already be running:
 *   python -m uvicorn server.app:app     (the API, port 8000)
 *   npm run dev                          (this app, port 5173)
 *
 * Usage:
 *   node scripts/screenshot.mjs <out.png> [ms to watch the solve] [width] [height]
 */

import { chromium } from "playwright";

const OUT = process.argv[2] ?? "board.png";
const SOLVE_MS = Number(process.argv[3] ?? 0);
const WIDTH = Number(process.argv[4] ?? 1440);
const HEIGHT = Number(process.argv[5] ?? 900);

// Uses the browser already installed on this machine: Playwright's own
// Chromium build times out on download here.
const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({
  viewport: { width: WIDTH, height: HEIGHT },
  deviceScaleFactor: 2,
});

const problems = [];
page.on("console", (message) => {
  if (message.type() === "error") problems.push(message.text());
});
page.on("pageerror", (error) => problems.push(String(error)));

await page.goto("http://localhost:5173/", { waitUntil: "networkidle" });
await page.waitForTimeout(2500);
await page.screenshot({ path: OUT.replace(/\.png$/, "-empty.png") });

if (SOLVE_MS > 0) {
  await page.getByRole("button").first().click();
  await page.waitForTimeout(SOLVE_MS);
  await page.screenshot({ path: OUT });
}

console.log(problems.length ? `problems: ${problems.slice(0, 5).join(" | ")}` : "no console errors");
await browser.close();
