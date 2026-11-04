// Minimum genuine application journey. No fake model/routes; never runs before remote discovery.
import { request } from "@playwright/test";
import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { execFileSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";
const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const root = path.resolve(repo, (await readFile(path.join(repo, "artifacts/semana10/CURRENT"), "utf8")).trim());
const output = path.join(root, "05-langsmith");
const filename = path.join(output, "recorrido-minimo.json");
let prior = {};
try { prior = JSON.parse(await readFile(filename, "utf8")); } catch {}
const result = { ...prior, kind: "prepared_real_provider_application_journey", synthetic: true, status: "prepared_not_executed", prepared_at: new Date().toISOString(), model_calls_this_invocation: false,
  steps: ["Search existing LangSmith traces first", "Reuse existing synthetic retail order, no repeated P1 inference", "Open separate synthetic P4 case through actual API", "Attach existing synthetic PNG, real perception", "Investigate using real Gemini + Deep Agents + evidence/procedure tools", "Verify HITL pause without plan effect", "Approve via API and resume same thread with another app_run_id", "Export genuine LangSmith traces and correlate thread/review; capture authenticated UI"] };
let api;
const save = () => writeFile(filename, JSON.stringify(result, null, 2));
async function getCase(cid) { const r = await api.get(`/api/cases/${cid}`); assert.ok(r.ok()); return r.json(); }
async function post(url, data) { const r = await api.post('/api' + url, { data }); assert.ok(r.ok(), `API status ${r.status()}`); return r.json(); }
async function wait(cid, rid) {
  for (let i = 0; i < 480; i++) {
    const s = await getCase(cid), r = s.runs.find(r => r.id === rid);
    if (r && !['queued', 'running'].includes(r.status)) { assert.notEqual(r.status, 'failed', 'Provider run failed; no automatic model retry'); return s; }
    await new Promise(resolve => setTimeout(resolve, 500));
  }
  throw new Error('BoundedRunTimeout');
}
try {
  if (!process.argv.includes('--execute')) {
    await save(); console.log(JSON.stringify({ status: result.status, new_model_calls: false }));
  } else {
    execFileSync('uv', ['run', 'python', 'scripts/export_langsmith_traces.py'], { cwd: repo, stdio: 'pipe' });
    const remote = JSON.parse(await readFile(path.join(output, 'trazas.json'), 'utf8'));
    assert.ok(remote.search_performed, 'Existing trace search must succeed before inference');
    if (remote.traces.length) {
      result.status = 'existing_traces_reused_no_new_inference'; result.reused_traces = remote.traces.map(t => t.run.id);
    } else {
      // Verify both containers actually have tracing enabled at the resolved destination.
      for (const service of ['api', 'worker']) {
        const check = JSON.parse(execFileSync('docker', ['compose', 'exec', '-T', service, 'python', '-c', 'import json; from aquaclean.config import Settings; from urllib.parse import urlparse; s=Settings(); print(json.dumps({"tracing":s.langsmith_tracing,"key":bool(s.langsmith_api_key.get_secret_value()),"project":s.langsmith_project,"agent":s.langsmith_agent_id,"workspace":s.langsmith_workspace_id,"endpoint_host":urlparse(s.langsmith_endpoint).hostname}))'], { cwd: repo, stdio: 'pipe' }).toString());
        assert.ok(check.tracing && check.key && (check.project || check.agent), 'Backend and worker must be configured for real tracing');
        assert.equal(check.endpoint_host, remote.endpoint_host, 'Backend/worker region differs from verified search');
        if (check.workspace) assert.equal(check.workspace, remote.destination.workspace_id_verified);
        if (check.project) assert.equal(check.project, remote.destination.project_name);
        if (check.agent) assert.equal(check.agent, remote.agent_id_configured);
      }
      api = await request.newContext({ baseURL: 'http://127.0.0.1:8000', timeout: 30000 });
      const original = JSON.parse(await readFile(path.join(root, '07-aplicacion/recorrido-proveedor-real.json'), 'utf8'));
      assert.ok(original.synthetic && original.service_order_id);
      result.parent_case_id = original.reception_case_id;
      const parent = await getCase(result.parent_case_id);
      assert.equal(parent.orders[0].id, original.service_order_id);
      if (!result.incident_case_id) {
        result.open_command_id ||= randomUUID(); result.expected_order_version ??= parent.orders[0].version; await save();
        const incident = await post(`/cases/${result.parent_case_id}/incidents`, { command_id: result.open_command_id, expected_version: result.expected_order_version, description: 'Nueva consulta sintética posterior al servicio: verificar el botón registrado en recepción, sin atribuir responsabilidad ni compensación.' });
        result.incident_case_id = incident.incident_case_id; await save();
      }
      const cid = result.incident_case_id;
      if (!result.attachment_id) {
        const response = await api.post(`/api/cases/${cid}/uploads`, { multipart: { file: { name: 'recepcion-sintetica.png', mimeType: 'image/png', buffer: await readFile(path.join(root, '07-aplicacion/medios-sinteticos/recepcion-sintetica.png')) } } });
        assert.ok(response.ok()); result.attachment_id = (await response.json()).id; await save();
      }
      if (!result.proposal_run_id) { result.proposal_run_id = randomUUID(); await save(); }
      let state = await getCase(cid);
      if (!state.runs.some(r => r.id === result.proposal_run_id)) {
        result.model_calls_this_invocation = true;
        await post(`/cases/${cid}/runs`, { run_id: result.proposal_run_id, attachment_ids: [result.attachment_id], text: 'Investiga esta nueva incidencia sintética con write_todos, delega a Evidencias y Procedimientos y recupera ambos resultados. Contrasta la recepción y los hechos registrados, cita chunk_id y propone resolve_incident con verificación física pendiente. No propongas dinero ni cierre. evidence_refs solo copia UUID de allowed_evidence_refs.' });
      }
      state = await wait(cid, result.proposal_run_id);
      assert.equal(state.case.proposal?.action, 'resolve_incident');
      assert.equal(state.command_history.length, 0, 'No P4 plan effect before interrupt');
      const review = state.approvals.findLast(a => a.status === 'pending');
      assert.ok(review); result.approval_id = review.id; result.thread_id = `org:${state.case.organization_id}:case:${cid}`;
      result.before_approval = { case_status: state.case.status, command_count: state.command_history.length, proposal_action: state.case.proposal.action, attachment_perception: state.attachments.map(a => a.perception_status) };
      result.resume_run_id ||= randomUUID(); await save();
      await post(`/cases/${cid}/approvals/${review.id}`, { decision_id: result.resume_run_id, action: 'approve', proposal_hash: review.proposal_hash, case_version: review.case_version, selection: {} });
      state = await wait(cid, result.resume_run_id);
      assert.notEqual(result.proposal_run_id, result.resume_run_id);
      assert.notEqual(state.case.status, 'closed', 'Approved plan stays open pending human fulfillment');
      result.after_approval = { case_status: state.case.status, command_count: state.command_history.length };
      result.status = 'application_journey_executed_remote_export_pending'; await save();
      // Read-only export. Never retry model calls to compensate for eventual trace delivery.
      execFileSync('uv', ['run', 'python', 'scripts/export_langsmith_traces.py'], { cwd: repo, stdio: 'pipe' });
    }
  }
} catch (error) {
  result.status = api ? 'application_failed' : 'blocked_before_application_execution'; result.error_type = error.name;
  result.reason = 'Read sanitized trace verification and application state; no credentials or provider exception bodies exported';
  process.exitCode = 2;
} finally {
  if (api) await api.dispose();
  await save();
}
