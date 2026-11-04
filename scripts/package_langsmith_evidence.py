"""Package real LangSmith evidence or an explicit blocked preparation, never local-log images."""

import hashlib
import importlib.metadata
import json
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

from aquaclean.config import Settings


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    folder = root / "05-langsmith"
    traces = json.loads((folder / "trazas.json").read_text())
    captures = json.loads((folder / "capturas.json").read_text())
    ready = bool(traces.get("traces")) and captures["status"] == "passed"
    status = "evidence_verified" if ready else "pending_real_langsmith_evidence"
    description = f"""# Monitoreo semana 10: estado real

Requisito: trazas reales de LangSmith en plan gratuito. Los logs locales no lo satisfacen. Estado de este paquete: **{status}**.

Consulta remota realizada: {traces["search_performed"]}. Trazas verificadas exportadas: {len(traces.get("traces", []))}. Capturas reales incluidas: {len(captures["screenshots"])}. Plan gratuito de la cuenta: {traces["account_plan"]}. No se cambió facturación, plan ni retención. La referencia pública del plan gratuito está en docs/LANGSMITH.md; una clave API sigue siendo necesaria para acceso SDK autenticado.

La comprobación local encontró falta de clave, destino/workspace sin configurar y trazado desactivado. El endpoint por defecto corresponde a US, sin verificar la cuenta. Chrome existe sin conexión CDP autorizada; no se copiaron perfiles ni cookies. Cero app.trace_links locales no implica cero ejecuciones remotas. La falta de acceso impide buscar, exportar IDs/URLs y capturar. No se afirma ausencia de trazas ni se fabrica una pantalla. Las pruebas controladas incluidas no acreditan LangSmith real.

El código preparado consulta primero roots AquaClean sintéticas con el SDK, sin depender del ledger local. Si existen ejecuciones, las reutiliza sin nuevas inferencias. Solo una búsqueda satisfactoria sin resultados habilita el recorrido mínimo: orden sintética anterior → nuevo P4 separado por API → PNG real/percepción → RAG y Deep Agents con write_todos/task y ambos subagentes → interrupt sin efecto del plan → aprobación y Command(resume) en el mismo hilo, app_run_id distinto. Mantiene plan abierto hasta cumplimiento humano posterior. No se ejecutó este recorrido sin trazado verificable.

Reproducción desde el repositorio: verificar/exportar, preparar/ejecutar y capturar siguiendo docs/LANGSMITH.md. Los scripts están incluidos como extractos, no un checkout completo ni un entorno con dependencias. El acceso externo efectivo no puede sustituirse por configuración ficticia.

Inventario de capturas requerido: listado de ejecuciones; árbol expandido; llamada al modelo; herramienta; Deep Agents; traza de pausa y traza de reanudación correlacionadas. capturas.json indica los archivos realmente capturados o el bloqueo. No hay capturas de login, credenciales, cookies, storageState, HAR ni imágenes generadas.
"""
    (folder / "RECORRIDO_Y_ESTADO.md").write_text(description)
    sources = {
        "docs/LANGSMITH.md": Path("docs/LANGSMITH.md"),
        "docs/OBSERVABILIDAD_LOCAL.md": Path("docs/OBSERVABILIDAD_LOCAL.md"),
        "AGENTS.md": Path("AGENTS.md"),
    }
    for name in [
        "scripts/langsmith_evidence.py",
        "scripts/verify_langsmith.py",
        "scripts/export_langsmith_traces.py",
        "scripts/package_langsmith_evidence.py",
        "web/scripts/capture-langsmith.mjs",
        "web/scripts/run-langsmith-minimal.mjs",
        "src/aquaclean/infrastructure/observability/tracing.py",
        "tests/unit/test_langsmith_evidence.py",
        "tests/unit/test_observability.py",
    ]:
        sources[name] = Path(name)
    for name in [
        "trazas.json",
        "verificacion.json",
        "capturas.json",
        "recorrido-minimo.json",
        "PENDIENTE.md",
        "RECORRIDO_Y_ESTADO.md",
        "comprobaciones-entorno.json",
        "pruebas-y-limites.json",
    ]:
        p = folder / name
        if p.exists():
            sources["05-langsmith/" + name] = p
    for filename in ["tests-langsmith-controlled.xml", "tests-langsmith-hitl-controlled.xml"]:
        p = Path("artifacts/semana10/work") / filename
        if p.exists():
            sources["pruebas-controladas/" + filename] = p
    for shot in captures["screenshots"]:
        p = folder / shot["file"]
        assert p.parent == folder and p.suffix == ".png"
        assert shot["url"].startswith(
            (
                "https://smith.langchain.com/",
                "https://eu.smith.langchain.com/",
                "https://apac.smith.langchain.com/",
                "https://aws.smith.langchain.com/",
            )
        )
        with Image.open(p) as im:
            im.verify()
        sources["05-langsmith/" + p.name] = p
    settings = Settings()
    for secret in [
        settings.langsmith_api_key.get_secret_value(),
        settings.gemini_api_key.get_secret_value(),
    ]:
        if len(secret) >= 12:
            assert all(secret.encode() not in p.read_bytes() for p in sources.values()), (
                "Secret detected; packaging rejected"
            )
    manifest = {
        "created_at": datetime.now(ZoneInfo("America/Lima")).isoformat(),
        "timezone": "America/Lima",
        "base_commit": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        "branch": subprocess.check_output(["git", "branch", "--show-current"], text=True).strip(),
        "tracked_diff_sha256": hashlib.sha256(
            subprocess.check_output(["git", "diff", "--binary"])
        ).hexdigest(),
        "sdk": importlib.metadata.version("langsmith"),
        "status": status,
        "requirement_satisfied": ready,
        "search_performed": traces["search_performed"],
        "verified_traces": len(traces.get("traces", [])),
        "actual_langsmith_screenshots": len(captures["screenshots"]),
        "new_model_calls": False,
        "local_logs_satisfy_requirement": False,
        "files": [
            {"path": name, "bytes": p.stat().st_size, "sha256": sha(p)}
            for name, p in sorted(sources.items())
        ],
        "manifest_self_hash": "excluded",
    }
    (folder / "00-manifest-langsmith.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    archive = root.parent / "evidencias-langsmith-semana10.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name, p in sorted(sources.items()):
            z.write(p, "langsmith-semana10/" + name)
        z.write(folder / "00-manifest-langsmith.json", "langsmith-semana10/00-manifest.json")
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
    print(
        json.dumps(
            {
                "zip": str(archive),
                "sha256": sha(archive),
                "bytes": archive.stat().st_size,
                "status": status,
                "real_screenshots": len(captures["screenshots"]),
            }
        )
    )


if __name__ == "__main__":
    main()
