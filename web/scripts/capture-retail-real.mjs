// Integration evidence: real HTTP API, PostgreSQL worker, Gemini and UI. No page.route.
import { chromium, request } from "@playwright/test";
import { readFile, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { randomUUID, createHash } from "node:crypto";
import { execFileSync } from "node:child_process";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const output = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const api = await request.newContext({ baseURL: "http://127.0.0.1:8000", timeout: 30000 });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 1100 } });
const previous = process.env.RETAIL_RESUME_CASE ? JSON.parse(await readFile(path.join(output, "07-aplicacion/recorrido-proveedor-real.json"), "utf8")) : {};
const result = { ...previous, kind: "current_real_provider", provider: "Gemini configured in backend", synthetic: true, langsmith: "blocked: API key absent", steps: previous.steps || [], screenshots: previous.screenshots || [] };
function stableId(cid, label) { const h = createHash("sha256").update(cid + ":" + label).digest("hex"); return `${h.slice(0,8)}-${h.slice(8,12)}-5${h.slice(13,16)}-a${h.slice(17,20)}-${h.slice(20,32)}`; }
async function post(url, data) { const res = await api.post("/api" + url, { data }); if (!res.ok()) throw new Error(`${url}: ${res.status()} ${(await res.json()).detail}`); return await res.json(); }
async function snapshot(cid) { const res = await api.get("/api/cases/" + cid); if (!res.ok()) throw new Error("snapshot failed"); return res.json(); }
async function wait(cid, rid) {
  for (let i = 0; i < 480; i++) { const s = await snapshot(cid), run = s.runs.find(r => r.id === rid); if (run && !["queued", "running"].includes(run.status)) { if (run.status === "failed") throw new Error(s.messages.at(-1).content); return s; } await new Promise(r => setTimeout(r, 500)); }
  throw new Error("Run exceeded 240 seconds; persisted case retained");
}
async function ask(cid, text, attachment_ids = []) { const r = await post(`/cases/${cid}/runs`, { run_id: randomUUID(), text, attachment_ids }); return await wait(cid, r.id); }
async function approve(s) { const a = s.approvals.findLast(a => a.status === "pending"); if (!a) throw new Error("No pending review: " + s.messages.at(-1)?.content); const r = await post(`/cases/${s.case.id}/approvals/${a.id}`, { decision_id: randomUUID(), action: "approve", proposal_hash: a.proposal_hash, case_version: a.case_version, selection: {} }); return await wait(s.case.id, r.id); }
async function capture(cid, name, mobile = false) {
  await page.setViewportSize(mobile ? { width: 390, height: 1000 } : { width: 1440, height: 1100 });
  await page.goto("http://127.0.0.1:8000"); await page.evaluate(cid => { localStorage.setItem("aquaclean-case", cid); localStorage.removeItem("aquaclean-theme"); }, cid); await page.reload();
  await page.locator("#chat-input").waitFor({ timeout: 20000 });
  await page.getByRole("main", { name: "Conversación" }).evaluate(el => { el.scrollTop = el.scrollHeight; });
  await page.waitForTimeout(500);
  await page.screenshot({ path: path.join(output, name), fullPage: true }); result.screenshots.push(name);
}
async function milestone(cid, action, extra = {}) { const s = await snapshot(cid); const r = await post(`/cases/${cid}/retail-operations`, { command_id: randomUUID(), expected_version: s.orders[0]?.version || s.retail.pickup_request.version, action, evidence: "Operador demo declara hito sintético verificado en laboratorio", ...extra }); result.steps.push({ action, result: r }); return snapshot(cid); }
try {
  const cid = process.env.RETAIL_RESUME_CASE || (await post("/cases", { title: "Semana 10 · Lucía Muestra · mostrador sintético" })).id;
  result.reception_case_id = cid;
  let s;
  if (!process.env.RETAIL_RESUME_CASE) {
  const attachments = [];
  for (const [file, mime] of [["recepcion-sintetica.png", "image/png"], ["recepcion-sintetica.pdf", "application/pdf"], ["recepcion-sintetica.wav", "audio/wav"]]) {
    const res = await api.post(`/api/cases/${cid}/uploads`, { multipart: { file: { name: file, mimeType: mime, buffer: await readFile(path.join(repo, "artifacts/semana10/media", file)) } } });
    if (!res.ok()) throw new Error("Real attachment rejected: " + file); const a = await res.json(); attachments.push(a.id);
  }
  const input = { run_id: randomUUID(), action: "receive", attachment_ids: attachments, reception: { customer: { name: "Lucía Muestra (sintética)", contact: "Contacto ficticio en mostrador" }, received: true, receipt_evidence: "Dos camisas recibidas y contadas por operador demo; botón flojo declarado", channel: "counter", items: [{ garment: "Camisa sintética", quantity: 2, service_code: "wash_piece", observations: "Una camisa con botón flojo en recepción", evidence_refs: attachments }], advance: "5.00", payment_evidence: "Operador declara adelanto sintético de cinco soles" } };
  s = await wait(cid, (await post(`/cases/${cid}/retail-draft`, input)).id);
  if (s.orders.length || s.retail.payments.length || s.inbox.length) throw new Error("Unexpected business effect before HITL");
  if (s.attachments.some(a => a.perception_status !== "completed" || !a.observation)) throw new Error("A modality was not perceived");
  result.before_approval = s; await capture(cid, "04-hitl/01-antes-de-aprobar.png");
  execFileSync("docker", ["compose", "restart", "api", "worker"], { cwd: repo, stdio: "pipe" });
  for (let i = 0; i < 60; i++) { try { if ((await api.get("/health/ready")).ok()) break; } catch {} await new Promise(r => setTimeout(r, 500)); }
  s = await snapshot(cid); if (s.orders.length || s.approvals.at(-1).id !== result.before_approval.approvals.at(-1).id) throw new Error("Pending review did not survive restart");
  await capture(cid, "04-hitl/02-revision-tras-reinicio.png"); s = await approve(s);
  result.after_reception = s; result.service_order_id = s.orders[0].id; await capture(cid, "07-aplicacion/01-orden-recibida.png"); await capture(cid, "07-aplicacion/02-mostrador-movil.png", true);
  await milestone(cid, "start_processing"); await milestone(cid, "finish_processing");
  await post(`/cases/${cid}/operator-events`, { event_id: randomUUID(), kind: "inspection", note: "Inspección física sintética: discrepancia entre botón flojo inicial y reclamo; necesita evaluación humana" });
  }
  let incident = result.incident_case_id;
  if (!incident) {
    s = await ask(cid, "Orden con procesamiento terminado e inspección registrada. Calidad: hay una discrepancia por posible daño del botón de una camisa; propone open_incident para abrir un caso P4 separado vinculado. No declares liberación ni solución.");
    if (s.case.proposal?.action !== "open_incident") throw new Error("Quality did not propose an incident: " + s.case.proposal?.action);
    s = await approve(s); incident = s.command_history.at(-1).result.incident_case_id; if (!incident) throw new Error("No separate P4 case created"); result.incident_case_id = incident;
    await post(`/cases/${incident}/operator-events`, { event_id: randomUUID(), kind: "observation", note: "Reclamo sintético de Lucía Muestra: discrepancia sobre el botón. Recepción registró botón flojo. No se atribuye responsabilidad ni compensación." });
  }
  if (!result.deep_after_plan) {
    s = await snapshot(incident);
    if (!s.approvals.some(a => a.status === "pending")) s = await ask(incident, "Investiga esta incidencia sintética. Planifica con write_todos y delega a Evidencias y Procedimientos; recupera ambos resultados. Contrasta recepción e inspección, cita los chunk_id recuperados y propone resolve_incident con un plan de verificación física, sin dinero ni cierre. Su ejecución humana queda pendiente. evidence_refs solo debe copiar UUID de allowed_evidence_refs.");
    result.deep_before_approval = s; if (s.case.proposal?.action !== "resolve_incident") throw new Error("Deep Agent did not propose a plan: " + s.case.proposal?.action);
    await capture(incident, "06-deepagents/04-propuesta-real-hitl.png"); s = await approve(s); result.deep_after_plan = s;
  }
  if (!result.fulfillment_recorded) {
    for (const kind of ["customer_acceptance", "fulfillment", "conformity"]) await post(`/cases/${incident}/operator-events`, { event_id: stableId(incident, kind), kind, note: "Evidencia sintética posterior al plan: aceptación, verificación física y conformidad declaradas por el responsable demo" });
    result.fulfillment_recorded = true;
  }
  if (!result.incident_closed) {
    s = await snapshot(incident);
    if (!s.approvals.some(a => a.status === "pending")) s = await ask(incident, "La aceptación, cumplimiento y conformidad posteriores al plan están documentados. Investiga con ambos subagentes, verifica evidencia y procedimiento, y propone close_incident para revisión humana. No cierres directamente. evidence_refs solo contiene UUID de allowed_evidence_refs.");
    if (s.case.proposal?.action !== "close_incident") throw new Error("Deep Agent did not propose close: " + s.case.proposal?.action); s = await approve(s); result.incident_closed = s;
  }
  await post(`/cases/${cid}/operator-events`, { event_id: randomUUID(), kind: "inspection", note: "Nueva inspección física sintética tras solución: prendas verificadas por calidad, sin incidencia bloqueante" });
  await post(`/cases/${cid}/operator-events`, { event_id: randomUUID(), kind: "conformity", note: "Calidad declara conformidad física sintética de las dos camisas, botón verificado después de solución" });
  s = await ask(cid, "Calidad: la incidencia separada ya se cerró con evidencia posterior. La inspección y conformidad física están registradas. Recupera procedimiento y propone release para liberar READY con revisión humana; no simules trabajo físico.");
  if (s.case.proposal?.action !== "release") throw new Error("Quality did not propose release: " + s.case.proposal?.action); s = await approve(s); result.ready = s; await capture(cid, "07-aplicacion/03-lista-aviso-local.png");
  s = await milestone(cid, "deliver", { receiver: "Lucía Muestra (sintética)", conformity: true }); await capture(cid, "07-aplicacion/04-entregada-con-saldo.png");
  const blocked = await api.post(`/api/cases/${cid}/retail-operations`, { data: { command_id: randomUUID(), expected_version: s.orders[0].version, action: "close", evidence: "Intento sintético con saldo pendiente" } });
  if (blocked.status() !== 409) throw new Error("Closure with balance was not rejected"); result.closure_with_balance = { status: blocked.status(), body: await blocked.json() };
  await milestone(cid, "payment", { amount: "7.00" }); s = await milestone(cid, "close"); result.final = s;
  await capture(cid, "07-aplicacion/05-cierre-comprobante-demo.png"); await capture(cid, "04-hitl/03-resultado-persistido.png");
  // A distinct P1R case demonstrates a new customer and a pickup without a ServiceOrder.
  const pc = await post("/cases", { title: "Semana 10 · solicitud previa de recojo sintética" });
  const tomorrow = new Date(Date.now() + 86400000).toLocaleDateString("en-CA", { timeZone: "America/Lima" });
  const pr = await post(`/cases/${pc.id}/retail-draft`, { run_id: randomUUID(), action: "request_pickup", pickup: { customer: { name: "Mateo Ensayo (sintético)", contact: "Contacto de demostración" }, address: "Calle ficticia de laboratorio 123, Lima", day: tomorrow, shift: "tarde", declared_volume: "Dos bolsas declaradas, sin prendas recibidas", contact: "Contacto de demostración" } });
  s = await wait(pc.id, pr.id); s = await approve(s); if (s.orders.length || !s.retail.pickup_request) throw new Error("Pickup request became an order"); result.pickup = s; await capture(pc.id, "07-aplicacion/06-solicitud-sin-orden.png");
  delete result.error; result.status = "passed";
} catch (error) { result.status = "failed"; result.error = String(error.message); process.exitCode = 1; }
finally { await writeFile(path.join(output, "07-aplicacion/recorrido-proveedor-real.json"), JSON.stringify(result, null, 2)); await browser.close(); await api.dispose(); console.log(JSON.stringify({ status: result.status, case_id: result.reception_case_id, incident_case_id: result.incident_case_id, error: result.error, screenshots: result.screenshots.length })); }
