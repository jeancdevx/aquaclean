"""Package measured evidence, active docs and selected source. Never includes secrets/data volumes."""

import hashlib
import importlib.metadata
import json
import re
import shutil
import subprocess
import sys
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def command(args):
    return subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL).strip()


def main():
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    flow = json.loads((root / "07-aplicacion/recorrido-proveedor-real.json").read_text())
    assert flow["status"] == "passed", "Do not package an incomplete run as passed"
    criterion = json.loads((root / "criterio-observabilidad.json").read_text())
    local = json.loads((root / "05-observabilidad-local/registros-locales.json").read_text())
    capture = json.loads(
        (root / "05-observabilidad-local/capturas-y-verificacion.json").read_text()
    )
    assert criterion["mode"] == "langsmith_required"
    traces = json.loads((root / "05-langsmith/trazas.json").read_text())
    smith_capture = json.loads((root / "05-langsmith/capturas.json").read_text())
    real_ready = bool(traces.get("traces")) and smith_capture.get("status") == "passed"
    # Active documentation plus its preserved antecedents; no complete repository archive.
    active = [
        "docs/openapi.json",
        "README.md",
        "AGENTS.md",
        "IMPLEMENTATION_STATUS.md",
        ".env.example",
        "compose.yaml",
        "Dockerfile",
        "pyproject.toml",
        "uv.lock",
        "web/package.json",
        "web/pnpm-lock.yaml",
    ]
    active += [str(p) for p in Path("docs").rglob("*.md")]
    active += [str(p) for p in Path("docs/bpmn").glob("*.bpmn")]
    active += [str(p) for p in Path("knowledge").glob("*.md")]
    active += [str(p) for p in Path("config").glob("*.json")]
    for source in active:
        target = root / "documentacion-activa" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    source_files = [
        "src/aquaclean/agents/chains.py",
        "src/aquaclean/agents/schemas.py",
        "src/aquaclean/agents/prompts.py",
        "src/aquaclean/agents/supervisor.py",
        "src/aquaclean/agents/specialists.py",
        "src/aquaclean/agents/deep_incidents/factory.py",
        "src/aquaclean/graphs/main.py",
        "src/aquaclean/graphs/specialist_flow.py",
        "src/aquaclean/graphs/state.py",
        "src/aquaclean/domain/retail.py",
        "src/aquaclean/infrastructure/llm/provider.py",
        "src/aquaclean/infrastructure/llm/schema.py",
        "src/aquaclean/infrastructure/persistence/commands.py",
        "src/aquaclean/infrastructure/persistence/repositories.py",
        "src/aquaclean/infrastructure/persistence/checkpointer.py",
        "src/aquaclean/infrastructure/persistence/retail.py",
        "src/aquaclean/infrastructure/persistence/retail_operations.py",
        "src/aquaclean/infrastructure/persistence/retail_logistics.py",
        "src/aquaclean/infrastructure/persistence/incident_cases.py",
        "src/aquaclean/infrastructure/persistence/incident_research.py",
        "src/aquaclean/infrastructure/observability/tracing.py",
        "src/aquaclean/workers/main.py",
        "src/aquaclean/workers/outbox.py",
        "src/aquaclean/interfaces/api/retail_routes.py",
        "web/src/components/chat/RetailPanel.tsx",
        "tests/integration/test_retail.py",
        "tests/integration/test_deep_incidents.py",
        "tests/integration/test_lcel_runtime.py",
        "tests/integration/test_graph_topology.py",
    ]
    source_files += [
        "tests/controlled_deep_model.py",
        "tests/fakes.py",
        "tests/helpers.py",
        "tests/conftest.py",
        "tests/evaluations/test_gemini_live.py",
        "tests/unit/test_retail_rules.py",
        "tests/unit/test_local_log_report.py",
        "tests/unit/test_langsmith_evidence.py",
        "tests/unit/test_observability.py",
        "web/tests/retail-real.spec.ts",
        "web/tests/chat.spec.ts",
        "web/tests/fakes/session.spec.ts",
    ]
    source_files += [str(p) for p in Path("migrations").glob("*.sql")]
    source_files += [str(p) for p in Path("scripts").glob("*semana10*.py")]
    source_files += [
        "scripts/local_environment.py",
        "scripts/verify_langsmith.py",
        "scripts/export_langsmith_traces.py",
        "scripts/langsmith_evidence.py",
        "scripts/package_langsmith_evidence.py",
        "scripts/export_local_observability.py",
        "scripts/local_log_report.py",
        "scripts/create_retail_media.py",
        "scripts/write_build_revision.py",
        "scripts/verify_semana10_persistence.py",
        "scripts/run_demo.py",
    ]
    source_files += [str(p) for p in Path("web/scripts").glob("*.mjs")]
    for source in source_files:
        target = root / "extractos" / source
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    logs = {
        "tests-deterministic.xml": "controlled/tests-deterministic.xml",
        "tests-local-observability.xml": "controlled/tests-local-observability.xml",
        "tests-langsmith-controlled.xml": "controlled/tests-langsmith-controlled.xml",
        "tests-langsmith-hitl-controlled.xml": "controlled/tests-langsmith-hitl-controlled.xml",
        "tests-gemini-real-final.xml": "real/tests-gemini-real.xml",
        "tests-ui-retail-real.xml": "real/tests-ui-retail-real.xml",
        "tests-ui-fake.xml": "fake/tests-ui-fake.xml",
        "playwright-real-ui.log": "real/playwright-ui.log",
        "playwright-fake-ui.log": "fake/playwright-ui.log",
        "frontend-check.log": "frontend-check.log",
        "frontend-build.log": "frontend-build.log",
        "compose-build.log": "compose-build.log",
        "compose-start.log": "compose-start.log",
        "gemini-real.log": "attempts/gemini-initial-schema-failure.log",
        "gemini-real-final.log": "real/gemini-final.log",
        "retail-real.log": "real/retail-final.log",
    }
    for source, target in logs.items():
        src = Path("artifacts/semana10/work") / source
        if src.exists():
            dst = root / "08-pruebas" / target
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    browser = Path("artifacts/semana10/work/tests-ui-general-final.xml")
    if browser.exists():
        shutil.copy2(browser, root / "08-pruebas/real/tests-ui-general.xml")
    for item in Path("artifacts/semana10/media").glob("*"):
        if item.suffix in {".png", ".pdf", ".wav"}:
            media = root / "07-aplicacion/medios-sinteticos"
            media.mkdir(exist_ok=True)
            shutil.copy2(item, media / item.name)
    shutil.copy2("docs/arquitectura/MATRIZ_BPMN_CODIGO.md", root / "03-bpmn/MATRIZ_BPMN_CODIGO.md")
    _write_explanation(root, flow)
    # Image validation, source extract line checks and package-relative evidence links.
    validations = []
    for path in sorted(root.rglob("*.png")):
        with Image.open(path) as image:
            image.verify()
        with Image.open(path) as image:
            validations.append(
                {"path": str(path.relative_to(root)), "width": image.width, "height": image.height}
            )
    for folder in ["01-lcel", "06-deepagents"]:
        for extract in json.loads((root / folder / "extractos.json").read_text()):
            lines = Path(extract["path"]).read_text().splitlines()
            assert (
                lines[extract["start"] - 1 : extract["start"] - 1 + len(extract["lines"])]
                == extract["lines"]
            )
    for name in ["INDICE_EVIDENCIAS.md", "CONTENIDO_PARA_INFORME.md"]:
        text = (root / name).read_text()
        for link in re.findall(r"\]\(([^)]+)\)", text):
            if link == "00-manifest.json":
                continue  # created after file hashing, then verified before ZIP creation
            if not link.startswith(("https://", "http://")):
                assert (root / link.split("#")[0]).exists(), link
    (root / "08-pruebas/validacion-paquete.json").write_text(
        json.dumps(
            {
                "pngs_verified": validations,
                "links_and_extracts": "passed",
                "image_legibility": "Exact SVG retained; PNG dimensions verified and representative images inspected visually",
                "historical_document_links": "Antecedent Markdown retains original relative paths/commit context; not new evidence",
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    tracked_diff = subprocess.check_output(["git", "diff", "--binary"])
    untracked = command(["git", "ls-files", "--others", "--exclude-standard"]).splitlines()
    changed = [
        p
        for p in untracked
        if not p.startswith("auditoria-aquaclean-2026-11-03/") and Path(p).is_file()
    ]
    revision = hashlib.sha256(tracked_diff)
    for item in sorted(changed):
        revision.update(item.encode())
        revision.update(Path(item).read_bytes())
    files = [
        {
            "path": str(p.relative_to(root)),
            "bytes": p.stat().st_size,
            "sha256": sha(p),
            "kind": _kind(p.relative_to(root)),
        }
        for p in sorted(root.rglob("*"))
        if p.is_file() and p.name != "00-manifest.json"
    ]
    audit = Path("auditoria-aquaclean-2026-11-03")
    audit_manifest = json.loads((audit / "MANIFEST.json").read_text())
    audit_changes = [
        entry["path"]
        for entry in audit_manifest["files"]
        if sha(audit / entry["path"]) != entry["sha256"]
    ]
    # Detect accidental inclusion of locally configured keys, without printing them.
    from aquaclean.config import Settings

    settings = Settings()
    for secret in [
        settings.gemini_api_key.get_secret_value(),
        settings.langsmith_api_key.get_secret_value(),
    ]:
        if len(secret) >= 12:
            assert not any(secret.encode() in (root / f["path"]).read_bytes() for f in files), (
                "Secret detected: package rejected"
            )
    manifest = {
        "created_at": datetime.now(ZoneInfo("America/Lima")).isoformat(),
        "timezone": "America/Lima",
        "base_commit": command(["git", "rev-parse", "HEAD"]),
        "branch": command(["git", "branch", "--show-current"]),
        "diff_sha256": revision.hexdigest(),
        "diff_hash_method": "git diff --binary plus sorted new file path/content, excluding preexisting audit input; artifacts ignored",
        "worktree": command(["git", "status", "--short"]),
        "published_commits_prs_deployments": False,
        "preexisting_audit_input": {
            "original_manifest_sha256": sha(audit / "MANIFEST.json"),
            "format_import_changes_to_auxiliary_tools": audit_changes,
            "xml_reports_and_historical_results_preserved_by_checksum": all(
                p.startswith("herramientas/") for p in audit_changes
            ),
        },
        "versions": {
            name: importlib.metadata.version(name)
            for name in [
                "langchain",
                "langchain-core",
                "langgraph",
                "deepagents",
                "langsmith",
                "langchain-google-genai",
                "psycopg",
                "pgvector",
            ]
        },
        "runtime_tools": {
            "python": sys.version.split()[0],
            "docker": command(["docker", "--version"]),
            "compose": command(["docker", "compose", "version", "--short"]),
        },
        "frontend": {
            "node": command(["node", "--version"]),
            "pnpm": command(["pnpm", "--version"]),
        },
        "commands_results_limits": json.loads((root / "08-pruebas/checks.json").read_text()),
        "rubric_status": {
            "LCEL": "implemented and application-tested",
            "LangGraph_HITL": "implemented; PostgreSQL resume/retry tested",
            "monitoring": "real LangSmith required; verified"
            if real_ready
            else "required real LangSmith pending authorized access/captures",
            "LangSmith": traces["status"],
            "DeepAgents": "SDK planning/delegation real Gemini and controlled tests",
            "ecosystem": "LangSmith transversal required for week10; local logs auxiliary only",
        },
        "observability_criterion": criterion,
        "local_observability": {
            "cases": len(local["cases"]),
            "runs": len(local["runs"]),
            "events": len(local["events"]),
            "approvals": len(local["approvals"]),
            "exported_at": local["exported_at"],
            "new_model_calls": False,
            "original_execution_dates_preserved": True,
            "capture_verification": capture,
        },
        "evidence_package_ready_under_current_criterion": real_ready,
        "langsmith_evidence": {
            "status": traces["status"],
            "search_performed": traces["search_performed"],
            "trace_count": len(traces.get("traces", [])),
            "capture_status": smith_capture["status"],
            "local_logs_satisfy_requirement": False,
        },
        "completed_week10": False,
        "completion_flag_reason": "Real LangSmith evidence is required; access/captures pending when real_ready is false. Academic final report is a later phase.",
        "files": files,
        "manifest_self_hash": "excluded",
    }
    (root / "00-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    assert (root / "00-manifest.json").is_file()
    archive = root.parent / "evidencias-semana10.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for path in sorted(root.rglob("*")):
            if path.is_file():
                zipped.write(path, root.name + "/" + str(path.relative_to(root)))
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert all(
            not any(
                part in {".env", "node_modules", ".venv", "storageState.json"}
                for part in Path(n).parts
            )
            and not n.endswith(".har")
            for n in zipped.namelist()
        )
    print(
        json.dumps(
            {
                "zip": str(archive),
                "bytes": archive.stat().st_size,
                "sha256": sha(archive),
                "files": len(files),
                "week10_complete": False,
                "evidence_package_ready_under_current_criterion": real_ready,
            },
            ensure_ascii=False,
        )
    )


def _kind(path):
    value = str(path)
    if value.startswith("05-langsmith/"):
        return "actual_langsmith_sdk_export_or_explicit_blocked_status_not_local_logs"
    if value.startswith("05-observabilidad-local/"):
        return "new_local_projection_of_prior_real_execution_records_no_new_inference"
    if (
        value.startswith("antecedentes/")
        or "/antecedentes/" in value
        or "attempt" in value
        or "intento" in value
    ):
        return "historical_or_prior_attempt_distinguished"
    if "/fake/" in value or "/controlled/" in value:
        return "controlled_test_not_real_provider"
    if value.startswith(("04-hitl/", "07-aplicacion/")) or "real" in value:
        return "real_provider_evidence_original_execution_dates_preserved_or_explicit_synthetic_fixture"
    return "current_exact_source_or_documentation"


def _write_explanation(root, flow):
    main = json.loads((root / "02-langgraph/principal.json").read_text())
    expanded = json.loads((root / "02-langgraph/subgrafos.json").read_text())
    index = [
        "# Índice de evidencias · semana 10",
        "",
        "Datos sintéticos. ZIP preparatorio para redactar después el informe académico. LangSmith real en plan gratuito es requisito vigente. Los logs locales solo son auxiliares. El acceso y la captura externos están pendientes según la verificación actual; no se afirma ausencia de ejecuciones remotas ni se sustituye el informe final.",
        "",
        "| Punto de actividad | Evidencia principal | Límite |",
        "|---|---|---|",
        "| 1 LCEL | [Flujo](01-lcel/flujo-lcel.png), [extractos exactos](01-lcel/extractos.txt), [términos](01-lcel/TERMINOS.md) | Renderizados de código, no VS Code. astream se evalúa aparte del SSE. |",
        "| 2 LangGraph/BPMN/HITL | [Grafo](02-langgraph/principal.png), [subgrafos](02-langgraph/subgrafos.png), [HITL](02-langgraph/hitl-acercamiento.png), [matriz](03-bpmn/MATRIZ_BPMN_CODIGO.md) | Grados desde topología; BPMN descriptivo, no ejecución XML. |",
        "| 3 LangSmith requerido | [Verificación](05-langsmith/verificacion.json), [exportación](05-langsmith/trazas.json), [capturas/estado](05-langsmith/capturas.json), [recorrido preparado](05-langsmith/recorrido-minimo.json) | Acceso pendiente: consulta remota no realizada, cero capturas LangSmith; logs locales no satisfacen el punto. |",
        "| 4 Deep Agents | [Catálogo](06-deepagents/catalogo.json), [fábrica](06-deepagents/extractos.txt), [ejecución real](06-deepagents/ejecuciones-reales.json), [HITL real](06-deepagents/04-propuesta-real-hitl.png) | Modelo controlado se distingue de Gemini; harness solo propone. |",
        "| 5 Ecosistema | [Gráfico](09-ecosistema/ecosistema.png) | LangSmith transversal requerido; logs auxiliares. Distinto de capas de software. |",
        "",
        "## Inventario de imágenes y pies",
        "",
        "Cada imagen siguiente tiene fuente exacta o captura Playwright real. Los SVG conservan texto vectorial para ampliar.",
        "",
    ]
    for image in sorted(root.rglob("*.png")):
        relative = str(image.relative_to(root))
        if relative.startswith(("documentacion-activa/", "extractos/")):
            continue
        point = (
            "1"
            if relative.startswith("01-")
            else "2"
            if relative.startswith(("02-", "03-", "04-"))
            else "3"
            if relative.startswith("05-")
            else "4"
            if relative.startswith("06-")
            else "5"
            if relative.startswith("09-")
            else "2/4 (apoyo de aplicación)"
        )
        caption = (
            "Extracto de código renderizado desde líneas verificadas"
            if image.stem
            in {
                "route",
                "structured",
                "structured_chain",
                "interpret",
                "awrap_model_call",
                "create_incident_agent",
                "investigate",
                "create_deep_agent-llamada",
            }
            else "XML BPMN V2 importado/renderizado en bpmn.io"
            if relative.startswith("03-")
            else "Diagrama renderizado desde fuente exacta"
            if relative.startswith(("01-", "02-", "09-"))
            else "Reporte local exacto renderizado y capturado con Playwright desde registros reales previos; no LangSmith ni captura del producto"
            if relative.startswith("05-observabilidad-local/")
            and image.stem != "04-actividad-aplicacion-real"
            else "Captura Playwright de la interfaz real de LangSmith, vinculada a IDs externos verificados"
            if relative.startswith("05-langsmith/")
            else "Registro renderizado desde JSON de una ejecución real Gemini/SDK, no LangSmith"
            if image.stem == "planificacion-delegacion-real"
            else "Captura Playwright de aplicación real con datos sintéticos y backend persistente"
        )
        index.append(
            f"- Punto {point}{' (solo apoyo; no acredita LangSmith)' if relative.startswith('05-observabilidad-local/') else ''}: [{image.name}]({relative}). {caption}; {image.stem.replace('-', ' ')}."
        )
    (root / "INDICE_EVIDENCIAS.md").write_text("\n".join(index) + "\n")
    content = f"""# Contenido verificable para redactar el informe después

No es el informe académico final. No declara aprobación integral de la semana 10. Fecha y revisión exactas en [manifest](00-manifest.json). Antecedentes V1 mantienen sus fechas; los intentos fallidos nuevos se conservan y no se presentan como éxitos.

## 1 Términos LCEL identificables

`agents/chains.py:structured_chain` compone ChatPromptTemplate y MessagesPlaceholder con el modelo estructurado inyectado mediante `|`, produciendo RunnableSequence. `llm/provider.py:structured` usa ainvoke y validación Pydantic completa con reparación acotada. Supervisor y especialistas invocan ese puerto desde la aplicación: prueba `test_application_invokes_project_lcel_for_supervisor_and_specialist`. V1 ya construía RunnableSequence internamente; no se afirma ausencia previa de Runnables. `provider.stream` usa astream, probado por evaluación real separada; el chat SSE transmite texto validado. El wire schema simplifica restricciones de generación que Gemini rechazaba, sin retirar la validación del dominio. Véanse [texto exacto](01-lcel/extractos.txt), [términos](01-lcel/TERMINOS.md) y [figura LCEL](01-lcel/flujo-lcel.png).

## 2 Grafo, grados, HITL y compatibilidad BPMN

Exportación del grafo final: **{main["node_count"]} nodos y {main["edge_count"]} aristas posibles**, incluyendo START/END. Expansión de especialistas: **{expanded["node_count"]} nodos y {expanded["edge_count"]} aristas**. Véanse [JSON](02-langgraph/principal.json), [grados CSV](02-langgraph/principal-grados.csv), [grafo](02-langgraph/principal.png), [subgrafos](02-langgraph/subgrafos.png), [acercamiento HITL](02-langgraph/hitl-acercamiento.png). La suma de grados de entrada y salida iguala las aristas en cada exportación. Supervisor elige P1–P4 o aclaración; stage puede responder o revisar; execute puede responder o reconfirmar excepción V1. No se recorren todas las ramas en un único run. Errores de proveedor/cuota, presupuesto, cancelación y conflictos los gestiona el worker fuera del grafo.

La revisión real usa interrupt con PostgreSQL y Command(resume) en el mismo thread. Caso de recepción `{flow["reception_case_id"]}` y orden `{flow["service_order_id"]}`. [Antes de aprobar](04-hitl/01-antes-de-aprobar.png) no había orden/cliente/pago; la misma revisión sobrevivió a [reinicio](04-hitl/02-revision-tras-reinicio.png). [Recorrido JSON](07-aplicacion/recorrido-proveedor-real.json) y [resultado persistido](04-hitl/03-resultado-persistido.png). Los tests cubren rechazo/corrección, obsolescencia, roles/hash/política/selección, reinicio y duplicación. El actor demo no acredita empleados reales.

Los siete XML V2 importaron sin advertencias en bpmn.io: [validación](03-bpmn/importacion-bpmn-io.json). [Matriz actividad–código–prueba](03-bpmn/MATRIZ_BPMN_CODIGO.md). Los XML son descriptivos; LangGraph no los ejecuta. La producción/inspección/transporte son tareas humanas declaradas; no se simula su ejecución física.

## 3 LangSmith requerido: evidencia real pendiente

La instrucción vigente exige trazas reales de LangSmith utilizando su plan gratuito. La propuesta anterior de logs como sustituto queda corregida. [Verificación saneada](05-langsmith/verificacion.json), [exportación/estado real](05-langsmith/trazas.json) y [estado de captura](05-langsmith/capturas.json). Falta clave de LangSmith, destino/workspace y sesión CDP autorizada. El endpoint por defecto es US, sin verificación contra la cuenta. Cero enlaces locales no prueba ausencia de ejecuciones externas: la búsqueda remota no pudo realizarse. No hay IDs/URLs/capturas inventados ni nuevas llamadas Gemini.

`scripts/langsmith_evidence.py` consulta el SDK instalado directamente mediante runs.query y traces.list_runs: raíces AquaClean sintéticas, destino/workspace verificado y ventana explícita. No depende exclusivamente de app.trace_links. Exporta estructura/IDs/métricas/metadatos permitidos, sin entradas/salidas completas ni secretos. Las [pruebas controladas](08-pruebas/controlled/tests-langsmith-controlled.xml) prueban seguridad y comportamiento, sin acreditar acceso real.

[Recorrido mínimo preparado](05-langsmith/recorrido-minimo.json): reutilizar primero trazas existentes; solo si una consulta satisfactoria no encuentra ninguna, reutilizar la orden sintética anterior, abrir P4 separado, percibir PNG real y ejecutar investigación Gemini/Deep Agents con ambas delegaciones. Pausa sin efecto del plan y aprobación/reanudación en el mismo thread con otro app_run_id. El plan queda abierto, sin inventar cumplimiento/cierre. Este recorrido está preparado y no se ejecutó sin trazado verificable. Scripts run-langsmith-minimal.mjs y capture-langsmith.mjs incluidos.

Las capturas requeridas son de la interfaz autenticada: listado, árbol expandido, modelo, herramientas, Deep Agents y pausa/reanudación correlacionadas. El script registra bloqueo y cero imágenes si falta acceso; no captura login ni genera una imitación. Los [logs locales](05-observabilidad-local/REPORTE_LOCAL.html) siguen como apoyo, con fechas originales, y no acreditan este punto. Ver [guía LangSmith](documentacion-activa/docs/LANGSMITH.md).

## 4 Deep Agents generados

SDK real `deepagents==0.7.30`, fábrica [extractos](06-deepagents/extractos.txt), investigador P4 y subagentes Evidencias/Procedimientos en [catálogo](06-deepagents/catalogo.json). TodoListMiddleware habilita planificación opt-in. StateBackend nuevo, read_file virtual y dos lecturas acotadas a la misma orden/procedimientos; sin host, shell, SQL libre, pagos o cierre directo. Presupuesto compartido y tiempo limitado. La propuesta normalizada ResolutionProposal valida fuentes/referencias y vuelve a HITL. [Ejecuciones Gemini](06-deepagents/ejecuciones-reales.json) contienen plan, task, herramientas, resultados, llamadas/tokens/duración cuando el proveedor los devuelve; coste desconocido. Se conservó también un intento real rechazado por cuota, sin efectos. Los tests de SDK con modelo controlado no se confunden con Gemini.

Caso P4 separado `{flow["incident_case_id"]}`, vinculado a la misma orden. Plan aprobado permaneció abierto; aceptación/cumplimiento/conformidad posteriores permitieron proponer y aprobar el cierre. [Propuesta real esperando aprobación](06-deepagents/04-propuesta-real-hitl.png). El harness nunca recibió herramientas de escritura de negocio.

## 5 Capas del ecosistema y producto al detalle

[Gráfico exacto](09-ecosistema/ecosistema.png): LangChain/LCEL compone, LangGraph orquesta estado/HITL, Deep Agents investiga y delega, LangSmith es transversal y requerido para evidencias; su ejecución externa está pendiente y los logs locales son auxiliares. No equivale a dominio/aplicación/infraestructura/interfaces de la arquitectura de software.

La recepción nueva sin pedido/recojo previo creó prendas, importes deterministas y adelanto declarado. [Orden recibida](07-aplicacion/01-orden-recibida.png), [móvil](07-aplicacion/02-mostrador-movil.png), [lista/aviso local](07-aplicacion/03-lista-aviso-local.png), [entrega con saldo](07-aplicacion/04-entregada-con-saldo.png) y [comprobante final visible](07-aplicacion/07-comprobante-final-visible.png). Orden final `{flow["final"]["orders"][0]["number"]}` CLOSED, saldo 0.00. Se comprobó rechazo de cierre con saldo 7 PEN. [Solicitud previa sin orden](07-aplicacion/06-solicitud-sin-orden.png). Formatos reales imagen/PDF/audio tienen percepción completada y originales/hash conservados; sus capturas y fixtures están en 07-aplicacion. El aviso READY se entregó una vez a bandeja local; no correo/WhatsApp. La alerta 24 h no interruptora se prueba con reloj de laboratorio en base separada. No se implementa seguimiento corporativo 48 h como cierre por silencio.

Pruebas, comandos, omisiones y límites: [checks](08-pruebas/checks.json). La documentación activa, XML y extractos incluidos permiten sustentar cada afirmación. No hay pago bancario, facturación fiscal, datos personales reales, ni certificación de producción. El paquete conserva el requisito LangSmith pendiente; no se declara completada la semana 10. El informe académico final se redacta después. Los registros anteriores conservan sus fechas y las pruebas nuevas de integración/exportación se identifican por separado.
"""
    (root / "CONTENIDO_PARA_INFORME.md").write_text(content)


if __name__ == "__main__":
    main()
