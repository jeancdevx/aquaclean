// Genuine LangSmith UI only. Reuse an authorized session; never save cookies or HAR.
import { chromium } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import { parseEnv } from "node:util";
import path from "node:path";
import { fileURLToPath } from "node:url";
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const root = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const output = path.join(root, "05-langsmith");
const data = JSON.parse(await readFile(path.join(output, "trazas.json"), "utf8"));
let local = {};
try { local = parseEnv(await readFile(path.join(repo, ".env"), "utf8")); } catch {}
const cdp = process.env.LANGSMITH_CDP_URL || local.LANGSMITH_CDP_URL;
const result = { captured_at: new Date().toISOString(), kind: "actual_langsmith_ui", mocked_routes: false, new_model_calls: false, screenshots: [], missing: [], status: "blocked" };
let browser, page;
try {
  if (!cdp || !data.traces?.length) {
    result.reason = "Verified remote traces and authorized browser connection required; no login screenshot taken";
    result.missing = ["execution_list", "expanded_tree", "model", "tool", "deepagents", "hitl_pause", "hitl_resume"];
    process.exitCode = 2;
  } else {
    browser = await chromium.connectOverCDP(cdp);
    const context = browser.contexts()[0];
    if (!context) throw new Error("NoAuthorizedContext");
    page = await context.newPage();
    await page.setViewportSize({ width: 1680, height: 1100 });
    const targets = [];
    for (const kind of ["execution_list", "trace_tree", "model", "tool", "deepagents"]) {
      const target = data.capture_targets.find(t => t.kind === kind);
      if (target) targets.push(target); else result.missing.push(kind);
    }
    const pair = Object.values(data.thread_correlations || {}).find(g => g.some(t => t.resume === false) && g.some(t => t.resume === true));
    if (pair) {
      for (const [kind, resume] of [["hitl_pause", false], ["hitl_resume", true]]) {
        const t = pair.find(t => t.resume === resume);
        targets.push({ kind, url: t.url, run_id: t.langsmith_run_id, thread_id: data.traces.find(x => x.run.id === t.langsmith_run_id)?.thread_id });
      }
    } else result.missing.push("correlated_hitl_pair");
    for (const [i, target] of targets.entries()) {
      const url = new URL(target.url);
      if (url.protocol !== "https:" || !["smith.langchain.com", "eu.smith.langchain.com", "apac.smith.langchain.com", "aws.smith.langchain.com"].includes(url.hostname) || url.username || url.password) throw new Error("UnverifiedCaptureHost");
      await page.goto(url.href, { waitUntil: "domcontentloaded" });
      if (/login|signin|auth/i.test(new URL(page.url()).pathname) || await page.locator('input[type="password"]').count()) throw new Error("HumanLoginRequired");
      const expected = target.kind === "execution_list" ? data.destination.project_name : target.kind === "trace_tree" || target.kind.startsWith("hitl_") ? "AquaClean.application_run" : data.traces.flatMap(t => t.spans).find(s => s.id === target.run_id)?.name;
      if (!expected) throw new Error("MissingVerifiedSpanName");
      await page.getByText(expected, { exact: false }).first().waitFor({ timeout: 20000 });
      let expanded = "not_requested";
      if (target.kind === "trace_tree") {
        const expand = page.getByRole("button", { name: /expand all|expandir todo/i });
        if (await expand.count()) { await expand.first().click(); expanded = "expand_all_clicked"; }
        else { expanded = "control_not_identified"; result.missing.push("expanded_tree_control"); }
      }
      const filename = `${String(i + 1).padStart(2, "0")}-${target.kind}-langsmith-real.png`;
      await page.screenshot({ path: path.join(output, filename), fullPage: true });
      result.screenshots.push({ file: filename, ...target, expanded, displayed_span_name: expected });
    }
    result.status = result.missing.length ? "partial" : "passed";
    if (result.status !== "passed") process.exitCode = 2;
  }
} catch (error) {
  result.reason = "Authenticated LangSmith view unavailable; no login/credentials captured";
  result.error_type = error.name;
  process.exitCode = 2;
} finally {
  if (page) await page.close();
  if (browser) await browser.close();
  await writeFile(path.join(output, "capturas.json"), JSON.stringify(result, null, 2));
}
console.log(JSON.stringify({ status: result.status, screenshots: result.screenshots.length, missing: result.missing, new_model_calls: false }));
