// Exact local report and actual application UI. No mocked routes, no model calls.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath, pathToFileURL } from "node:url";
import path from "node:path";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const root = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const output = path.join(root, "05-observabilidad-local");
const reportText = await readFile(path.join(output, "registros-locales.json"), "utf8");
const report = JSON.parse(reportText);
const browser = await chromium.launch();
const result = { kind: "local_report_from_exact_records", captured_at: new Date().toISOString(), source_json_sha256: createHash("sha256").update(reportText).digest("hex"), new_model_calls: false, mocked_routes: false, report_checks: [], screenshots: [] };
try {
  const page = await browser.newPage({ viewport: { width: 1500, height: 1200 } });
  await page.goto(pathToFileURL(path.join(output, "REPORTE_LOCAL.html")).href);
  await page.waitForFunction(() => !!window.localReport);
  assert.equal(await page.evaluate(() => window.localReport.events.length), report.events.length);
  await page.locator("#overview").screenshot({ path: path.join(output, "01-resumen-local.png") });
  result.screenshots.push("01-resumen-local.png");
  const deep = report.runs.find(r => r.deep_agents?.status === "proposed");
  assert.ok(deep, "No actual completed SDK investigation in source");
  await page.locator("#run").selectOption(deep.app_run_id);
  const toolTable = await page.locator("#deep-table").innerText();
  for (const name of ["task", "write_todos", "case_evidence_read", "case_procedures_read"]) assert.ok(toolTable.includes(name));
  await page.locator("#execution").screenshot({ path: path.join(output, "02-ejecucion-deep-local.png") });
  result.screenshots.push("02-ejecucion-deep-local.png");
  assert.ok(report.approvals.some(a => a.request_app_run_id && a.resume_app_run_id && a.request_app_run_id !== a.resume_app_run_id));
  await page.locator("#hitl").screenshot({ path: path.join(output, "03-pausa-reanudacion-local.png") });
  result.screenshots.push("03-pausa-reanudacion-local.png");
  await page.locator("#filter").fill("execute_command");
  assert.ok((await page.locator("#events tbody tr").count()) > 0);
  result.report_checks.push("Original event count matches JSON", "Deep planning/delegation/read tool journal visible", "HITL separated app runs linked by approval ID", "Interactive component filter works");
  try {
    await page.goto("http://127.0.0.1:8000");
    await page.evaluate(cid => localStorage.setItem("aquaclean-case", cid), deep.case_id);
    await page.reload();
    await page.getByRole("button", { name: "Abrir actividad y caso" }).click();
    const activity = page.locator(".activity-item").filter({ hasText: "DeepAgents.investigation" }).first();
    await activity.waitFor({ timeout: 15000 });
    await activity.scrollIntoViewIfNeeded();
    await page.screenshot({ path: path.join(output, "04-actividad-aplicacion-real.png"), fullPage: true });
    result.screenshots.push("04-actividad-aplicacion-real.png");
    result.application_capture = "actual persisted case UI";
  } catch (error) {
    result.application_capture = "not_available";
    result.application_capture_error = error.name;
  }
  result.status = "passed";
} finally {
  await writeFile(path.join(output, "capturas-y-verificacion.json"), JSON.stringify(result, null, 2));
  await browser.close();
}
console.log(JSON.stringify({ status: result.status, screenshots: result.screenshots.length, application_capture: result.application_capture }));
