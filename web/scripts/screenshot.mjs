/**
 * Drive the board in a real browser and photograph it.
 *
 * The board is a 3D scene and the panels are driven by live data, so
 * typechecking says nothing about whether any of it renders. This walks the
 * page through a named scene and writes PNGs to look at.
 *
 * Both servers must already be running:
 *   python -m uvicorn server.app:app     (the API, port 8000)
 *   npm run dev                          (this app, port 5173)
 *
 * Usage:
 *   node scripts/screenshot.mjs <out.png> <scene> [width] [height]
 *
 * Scenes:
 *   empty   the opening state, before anything is solved
 *   solve   run a full solve and photograph the result
 *   panels  solve, then open the log and the chart
 *   filter  solve, open the log, switch it to records only
 *   replay  solve, start a replay, photograph it part-way through
 *   playback  join the day's recording and photograph it mid-playback
 */

import { chromium } from "playwright";

const OUT = process.argv[2] ?? "board.png";
const SCENE = process.argv[3] ?? "empty";
const WIDTH = Number(process.argv[4] ?? 1440);
const HEIGHT = Number(process.argv[5] ?? 900);

/** A solve makes about 20 live API calls at half a second each. */
const SOLVE_MS = 30000;

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

const press = async (name) => {
  await page.getByRole("button", { name }).first().click();
  await page.waitForTimeout(700);
};

if (SCENE === "playback") {
  await page.getByRole("button").first().click();
  await page.waitForTimeout(2600);
} else if (SCENE !== "empty") {
  await page.getByRole("button").first().click();
  await page.waitForTimeout(SOLVE_MS);
}

if (SCENE === "panels" || SCENE === "filter") {
  await press("יומן");
  await press("גרף");
}

if (SCENE === "filter") {
  await page.getByRole("button", { name: /^שיאים/ }).first().click();
  await page.waitForTimeout(900);
}

if (SCENE === "replay") {
  await press("גרף");
  await press("הרצה חוזרת");
  await page.waitForTimeout(1600);
}

await page.screenshot({ path: OUT });
console.log(
  problems.length ? `problems: ${problems.slice(0, 5).join(" | ")}` : "no console errors",
);
await browser.close();
