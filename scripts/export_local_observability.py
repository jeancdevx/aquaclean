"""Export real persisted records without a LangSmith key or new provider calls."""

import argparse
import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import httpx
from local_log_report import build_report, render_html


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--from-artifacts",
        action="store_true",
        help="Read the previously captured real records, without any network request",
    )
    args = parser.parse_args()
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    flow_path = root / "07-aplicacion/recorrido-proveedor-real.json"
    deep_path = root / "06-deepagents/ejecuciones-reales.json"
    flow, deep = json.loads(flow_path.read_text()), json.loads(deep_path.read_text())
    prior = root / "antecedentes/00-manifest-paquete-anterior.json"
    prior_manifest = json.loads(prior.read_text()) if prior.exists() else {}
    assert flow["status"] == "passed" and flow["synthetic"] is True
    snapshots = [
        v for v in flow.values() if isinstance(v, dict) and {"case", "events", "runs"} <= v.keys()
    ]
    if not args.from_artifacts:
        with httpx.Client(base_url="http://127.0.0.1:8000", timeout=15) as client:
            for cid in {s["case"]["id"] for s in snapshots}:
                response = client.get("/api/cases/" + cid)
                response.raise_for_status()
                snapshots.append(response.json())
    report = build_report(
        snapshots,
        deep["runs"],
        exported_at=datetime.now(ZoneInfo("America/Lima")).isoformat(),
        provenance={
            "mode": "persisted application API plus original real capture"
            if not args.from_artifacts
            else "original real captures, offline re-export",
            "source_files": [
                {
                    "path": str(p.relative_to(root)),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
                for p in [flow_path, deep_path]
            ],
            "new_model_calls": False,
            "original_execution_revision": {
                k: prior_manifest.get(k) for k in ("base_commit", "diff_sha256")
            },
            "prior_manifest_sha256": hashlib.sha256(prior.read_bytes()).hexdigest()
            if prior.exists()
            else None,
        },
    )
    target = root / "05-observabilidad-local"
    target.mkdir(exist_ok=True)
    (target / "registros-locales.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    (target / "eventos.jsonl").write_text(
        "".join(json.dumps(e, ensure_ascii=False) + "\n" for e in report["events"])
    )
    for filename, rows in [
        ("eventos.csv", report["events"]),
        ("revisiones-hitl.csv", report["approvals"]),
    ]:
        with (target / filename).open("w") as stream:
            writer = csv.DictWriter(stream, fieldnames=sorted({k for row in rows for k in row}))
            writer.writeheader()
            writer.writerows(rows)
    (target / "REPORTE_LOCAL.html").write_text(render_html(report))
    # Operational logs are supplemental, filtered to selected app run IDs. Never export raw logs.
    if not args.from_artifacts:
        logs = subprocess.run(
            ["docker", "compose", "logs", "--no-color", "--timestamps", "api", "worker"],
            capture_output=True,
            text=True,
        )
        selected = []
        for line in logs.stdout.splitlines():
            match = re.search(r"run ([0-9a-f-]{36}) failed \(([A-Za-z0-9_]+)\)", line)
            if match and any(r["app_run_id"] == match[1] for r in report["runs"]):
                # Export only the permitted identifiers/error code, never arbitrary log text.
                selected.append(f"app_run_id={match[1]} error_type={match[2]}")
        (target / "worker-filtrado.log").write_text(
            "\n".join(selected) + ("\n" if selected else "")
        )
        (target / "estado-logs-operativos.json").write_text(
            json.dumps(
                {
                    "command": "docker compose logs --no-color --timestamps api worker",
                    "exit_code": logs.returncode,
                    "matching_lines_retained": len(selected),
                    "status": "filtered_lines_exported"
                    if selected
                    else "no_matching_lines_retained_in_current_containers",
                    "note": "Supplement only; persisted application events remain in eventos.jsonl",
                },
                indent=2,
            )
        )
    (target / "LEEME.md").write_text(
        "# Observabilidad local para la entrega\n\nModalidad preparada según la aclaración del usuario sobre la indicación del profesor. No requiere cuenta ni API key de LangSmith. La inferencia registrada sí se realizó con Gemini configurado; exportar y consultar estos registros no llama al modelo nuevamente.\n\nAbrir REPORTE_LOCAL.html en el navegador, elegir una ejecución y revisar herramientas, planificación/delegación, duración/uso reportado y pausas/reanudaciones. JSON/JSONL/CSV permiten verificar los valores y los IDs. Son IDs locales de aplicación, no IDs de LangSmith. No se recrean spans internos ni costes ausentes. Los tiempos originales se conservan; esta es una nueva exportación de ejecuciones previas, no una ejecución nueva.\n\nReproducir: `uv run python scripts/export_local_observability.py` con Compose activo, o añadir `--from-artifacts` para exportación completamente offline. Capturas: `node web/scripts/capture-local-observability.mjs`. La vista Actividad de la aplicación permite mostrar los eventos persistidos directamente.\n"
    )
    print(
        json.dumps(
            {
                "output": str(target),
                "cases": len(report["cases"]),
                "runs": len(report["runs"]),
                "events": len(report["events"]),
                "approvals": len(report["approvals"]),
                "new_model_calls": False,
            }
        )
    )


if __name__ == "__main__":
    main()
