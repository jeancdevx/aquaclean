"""Project persisted public events into a local report; never invent tracing spans."""

import json
from datetime import datetime


def _time(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _tokens(usage):
    values = usage if isinstance(usage, list) else [usage]
    observed = [
        v
        for v in values
        if isinstance(v, dict)
        and any(k in v for k in ("input_tokens", "output_tokens", "total_tokens"))
    ]
    if not observed:
        return None
    return {
        key: sum(v[key] for v in observed if isinstance(v.get(key), int))
        if any(isinstance(v.get(key), int) for v in observed)
        else None
        for key in ("input_tokens", "output_tokens", "total_tokens")
    } | {"records_with_usage": len(observed)}


def build_report(snapshots, investigations, *, exported_at, provenance):
    events, runs, cases = {}, {}, {}
    for snapshot in snapshots:
        case = snapshot["case"]
        cases[case["id"]] = {
            k: case.get(k)
            for k in ("id", "organization_id", "process", "status", "order_id", "parent_case_id")
        }
        order = next(iter(snapshot.get("orders", [])), {})
        cases[case["id"]].update(
            service_order_status=order.get("status"),
            order_number=order.get("number"),
            balance=snapshot.get("retail", {}).get("balance"),
        )
        for run in snapshot.get("runs", []):
            runs[run["id"]] = {
                "app_run_id": run["id"],
                "case_id": case["id"],
                "status": run["status"],
                "created_at": run.get("created_at"),
            }
        for event in snapshot.get("events", []):
            if event["event_id"] in events and events[event["event_id"]] != event:
                raise ValueError("Conflicting persisted event ID; evidence cannot be merged")
            events[event["event_id"]] = event
    timeline = []
    for event in sorted(events.values(), key=lambda e: e["sequence"]):
        payload = event["payload"]
        timeline.append(
            {
                "event_sequence": event["sequence"],
                "local_event_id": event["event_id"],
                "created_at": event["created_at"],
                "case_id": event["case_id"],
                "app_run_id": event["run_id"],
                "event_type": event["type"],
                "component": payload.get("agent") or payload.get("name"),
                "status": payload.get("status"),
                "duration_ms_reported": payload.get("duration_ms"),
                "approval_id": payload.get("approval_id"),
                "decision": payload.get("action") if event["type"] == "approval.resolved" else None,
                "error_code": payload.get("code") if event["type"] == "run.failed" else None,
                "model": payload.get("model"),
                "prompt_version": payload.get("prompt_version"),
            }
        )
    deep = {}
    for record in investigations:
        result = record["result"]
        deep[record["app_run_id"]] = {
            "sdk": result.get("sdk"),
            "status": result.get("status") or ("proposed" if result.get("proposal") else "unknown"),
            "model_calls_reported": result.get("model_calls"),
            "duration_ms_reported": result.get("duration_ms"),
            "tokens_reported": _tokens(result.get("usage", [])),
            "cost_usd_reported": result.get("cost_usd"),
            "error_type": result.get("error_type"),
            "journal": [
                {
                    "entry_index": i + 1,
                    "agent": entry["agent"],
                    "tool": entry["tool"],
                    "delegated_to": entry.get("args", {}).get("subagent_type"),
                    "todo_statuses": [
                        t.get("status") for t in entry.get("args", {}).get("todos", [])
                    ],
                }
                for i, entry in enumerate(result.get("journal", []))
            ],
        }
    for rid, run in runs.items():
        case = cases[run["case_id"]]
        own = [e for e in events.values() if e["run_id"] == rid]
        starts = [e for e in own if e["type"] == "run.started"]
        ends = [e for e in own if e["type"] in {"run.completed", "run.failed"}]
        begin = min((e["created_at"] for e in starts), default=None)
        finish = max((e["created_at"] for e in ends), default=None)
        duration = (
            round((_time(finish) - _time(begin)).total_seconds() * 1000)
            if begin and finish
            else None
        )
        if duration is not None and duration < 0:
            raise ValueError("Negative execution duration in source events")
        usage = []
        for event in own:
            if event["type"] != "agent.completed":
                continue
            payload = event["payload"]
            # Deep journal is canonical. Its usage is also echoed in P4's event.
            if payload.get("agent") == "P4" and rid in deep:
                continue
            tokens = _tokens(payload.get("usage", {}).get("tokens", {}))
            if tokens is not None:
                usage.append(
                    {
                        "component": payload.get("agent"),
                        "tokens_reported": tokens,
                        "model_calls_reported": payload.get("usage", {}).get("model_calls"),
                        "coverage": "reported response only; transport retries and unreported SDK usage are not inferred",
                    }
                )
        run.update(
            thread_id=f"org:{case['organization_id']}:case:{case['id']}",
            started_at=begin,
            finished_at=finish,
            duration_ms_from_events=duration,
            public_event_count=len(own),
            agent_usage=usage,
            deep_agents=deep.get(rid),
        )
    approvals = {}
    for event in timeline:
        aid = event.get("approval_id")
        if not aid:
            continue
        approval = approvals.setdefault(aid, {"approval_id": aid, "case_id": event["case_id"]})
        if event["event_type"] == "approval.requested":
            approval.update(
                request_app_run_id=event["app_run_id"], requested_at=event["created_at"]
            )
        elif event["event_type"] == "approval.resolved":
            approval.update(
                resume_app_run_id=event["app_run_id"],
                decided_at=event["created_at"],
                decision=event["decision"],
            )
    for approval in approvals.values():
        if approval.get("requested_at") and approval.get("decided_at"):
            approval["pause_to_decision_ms_from_events"] = round(
                (_time(approval["decided_at"]) - _time(approval["requested_at"])).total_seconds()
                * 1000
            )
    return {
        "kind": "local_application_observability",
        "exported_at": exported_at,
        "execution_dates_preserved": True,
        "provenance": provenance,
        "synthetic": True,
        "langsmith": {"executed": False, "trace_ids": [], "local_ids_are_not_langsmith_ids": True},
        "metric_limits": [
            "Public application events and SDK tool journal; no full internal LCEL/model span tree",
            "Token usage is reported per recorded response or canonical Deep Agents execution; no complete billing total inferred",
            "Missing duration/tokens/cost remain null, never fabricated as zero",
            "Human waiting is correlated between separate app runs, not held open as model execution",
            "No new model calls are performed by this exporter",
        ],
        "cases": list(cases.values()),
        "runs": sorted(runs.values(), key=lambda r: r.get("created_at") or ""),
        "approvals": list(approvals.values()),
        "events": timeline,
    }


def render_html(report):
    data = (
        json.dumps(report, ensure_ascii=False)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return (
        """<!doctype html><html lang="es"><meta charset="utf-8"><title>Aqua Clean · logs locales</title>
<style>body{font:16px/1.5 system-ui;margin:0;color:#0f172a;background:#f8fafc}main{max-width:1400px;margin:auto;padding:32px}h1{font-size:28px}h2{font-size:20px}section{padding:24px;margin:24px 0;background:white;border:1px solid #cbd5e1;border-radius:12px}table{width:100%;border-collapse:collapse}th,td{text-align:left;vertical-align:top;padding:8px;border:1px solid #cbd5e1;font-size:14px;overflow-wrap:anywhere}th{background:#f0fdfa}select{padding:8px;max-width:100%}code,pre{font:13px/1.5 monospace;overflow-wrap:anywhere;white-space:pre-wrap}.note{color:#475569}.ok{color:#0f766e}.metrics{display:flex;gap:24px;flex-wrap:wrap}button,select{font:inherit}a{color:#0f766e}</style>
<main><h1>Observabilidad local · Aqua Clean</h1><p>Registros reales de aplicación y Deep Agents, con datos sintéticos. Exportación sin cuenta ni clave de LangSmith.</p><p class="note">No es una captura de LangSmith. Las fechas pertenecen a las ejecuciones registradas; exportar estos datos no ejecuta nuevamente Gemini.</p>
<section id="overview"><h2>Resumen verificable</h2><div class="metrics" id="metrics"></div><p id="provenance" class="note"></p><div id="cases"></div><p class="note">Duraciones: marcas de eventos o valor registrado. Tokens: solo uso devuelto y conservado. Coste: desconocido. No se reconstruyen spans internos ausentes.</p></section>
<section id="execution"><h2>Ejecuciones y herramientas</h2><label>Ejecución de la aplicación <select id="run"></select></label><div id="run-details"></div><h3>Registro de Deep Agents</h3><div id="deep"></div></section>
<section id="hitl"><h2>Pausa y reanudación HITL</h2><p class="note">La solicitud de revisión y su aprobación son eventos correlacionados por approval_id y thread_id; la reanudación tiene otro app_run_id.</p><div id="approvals"></div></section>
<section><h2>Eventos públicos en orden original</h2><label>Filtrar componente o evento <input id="filter" type="search"></label><div id="events"></div></section></main>
<script id="data" type="application/json">"""
        + data
        + """</script><script>
const report=JSON.parse(document.getElementById('data').textContent);window.localReport=report;
const value=x=>x===null||x===undefined?'No registrado':typeof x==='object'?JSON.stringify(x):String(x);
function table(target,columns,rows){const t=document.createElement('table'),h=t.createTHead().insertRow();for(const c of columns){const th=document.createElement('th');th.textContent=c[0];h.append(th)}const b=t.createTBody();for(const r of rows){const tr=b.insertRow();for(const c of columns)tr.insertCell().textContent=value(c[1](r))}document.getElementById(target).replaceChildren(t)}
document.getElementById('metrics').textContent=`${report.cases.length} casos · ${report.runs.length} ejecuciones · ${report.events.length} eventos públicos · ${report.approvals.length} revisiones`;
document.getElementById('provenance').textContent='Exportado: '+report.exported_at+' · Fuente: '+report.provenance.mode;
table('cases',[['Caso',x=>x.id],['Proceso',x=>x.process],['Estado del caso',x=>x.status],['Orden',x=>x.order_number],['Estado del servicio',x=>x.service_order_status],['Saldo PEN',x=>x.balance]],report.cases);
const select=document.getElementById('run');for(const r of report.runs){const o=document.createElement('option');o.value=r.app_run_id;o.textContent=r.app_run_id+' · '+r.status+(r.deep_agents?' · Deep Agents':'');select.append(o)}
function update(){const r=report.runs.find(x=>x.app_run_id===select.value);if(!r)return;const p=document.createElement('pre');p.textContent='app_run_id: '+r.app_run_id+'\\ncase_id: '+r.case_id+'\\nthread_id: '+r.thread_id+'\\nEstado: '+r.status+'\\nInicio: '+value(r.started_at)+'\\nFin: '+value(r.finished_at)+'\\nDuración entre eventos: '+value(r.duration_ms_from_events)+' ms\\nUso de agentes registrado: '+JSON.stringify(r.agent_usage,null,2);document.getElementById('run-details').replaceChildren(p);if(r.deep_agents){const d=document.createElement('pre');d.textContent='Llamadas del harness: '+value(r.deep_agents.model_calls_reported)+' · duración registrada: '+value(r.deep_agents.duration_ms_reported)+' ms\\nTokens del harness (sin duplicar el evento P4): '+JSON.stringify(r.deep_agents.tokens_reported)+'\\nCoste: '+value(r.deep_agents.cost_usd_reported);document.getElementById('deep').replaceChildren(d);const box=document.createElement('div');box.id='deep-table';document.getElementById('deep').append(box);table('deep-table',[['#',x=>x.entry_index],['Agente',x=>x.agent],['Herramienta',x=>x.tool],['Delegación',x=>x.delegated_to],['Estados de tareas',x=>x.todo_statuses]],r.deep_agents.journal)}else document.getElementById('deep').textContent='Este run no contiene una investigación SDK registrada.'}
select.addEventListener('change',update);const deep=report.runs.find(r=>r.deep_agents&&r.deep_agents.status==='proposed');if(deep)select.value=deep.app_run_id;update();
table('approvals',[['Revisión',x=>x.approval_id],['Run que solicita',x=>x.request_app_run_id],['Run que reanuda',x=>x.resume_app_run_id],['Decisión',x=>x.decision],['Espera hasta decisión (ms)',x=>x.pause_to_decision_ms_from_events]],report.approvals);
function events(){const q=document.getElementById('filter').value.toLowerCase();table('events',[['Secuencia',x=>x.event_sequence],['Fecha original',x=>x.created_at],['app_run_id',x=>x.app_run_id],['Evento',x=>x.event_type],['Componente',x=>x.component],['Estado',x=>x.status],['Duración informada (ms)',x=>x.duration_ms_reported]],report.events.filter(x=>(value(x.component)+' '+x.event_type).toLowerCase().includes(q)))}document.getElementById('filter').addEventListener('input',events);events();
</script></html>"""
    )
