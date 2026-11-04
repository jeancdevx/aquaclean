"""Real HTTP + Gemini P1–P4 demonstration. Creates only explicitly synthetic cases.

Run with the stack up: uv run python scripts/run_demo.py --restart
Restarting retains named volumes. This script never removes volumes or deletes cases.
"""

import argparse
import asyncio
import hashlib
import json
import subprocess
import time
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx

from aquaclean.domain.entities import LimaClock


async def main(restart: bool):
    from create_demo_media import documents

    documents()
    results = {"synthetic": True, "provider": "real Gemini configured in backend", "steps": []}
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=20) as client:

        async def post(path, body):
            response = await client.post("/api" + path, json=body)
            if response.is_error:
                raise RuntimeError(
                    f"{path}: {response.status_code} {response.json().get('detail')}"
                )
            return response.json()

        async def snapshot(cid):
            response = await client.get("/api/cases/" + cid)
            response.raise_for_status()
            return response.json()

        async def wait(cid, rid):
            start = time.monotonic()
            while time.monotonic() - start < 150:
                value = await snapshot(cid)
                run = next(r for r in value["runs"] if r["id"] == rid)
                if run["status"] not in {"queued", "running"}:
                    if run["status"] == "failed":
                        raise RuntimeError(value["messages"][-1]["content"])
                    return value
                await asyncio.sleep(0.5)
            raise RuntimeError("Ejecución excedió 150 segundos; estado persistido conservado")

        async def ask(cid, text, attachment_ids=None):
            rid = str(uuid4())
            await post(
                f"/cases/{cid}/runs",
                {"run_id": rid, "text": text, "attachment_ids": attachment_ids or []},
            )
            return await wait(cid, rid)

        async def confirm(value, selection=None):
            approval = next(
                (a for a in reversed(value["approvals"]) if a["status"] == "pending"), None
            )
            if not approval:
                raise RuntimeError(
                    "No hay propuesta confirmable: " + value["messages"][-1]["content"]
                )
            cid = value["case"]["id"]
            rid = str(uuid4())
            await post(
                f"/cases/{cid}/approvals/{approval['id']}",
                {
                    "decision_id": rid,
                    "action": "approve",
                    "proposal_hash": approval["proposal_hash"],
                    "case_version": approval["case_version"],
                    "selection": selection or {},
                },
            )
            return await wait(cid, rid)

        async def event(cid, kind, note):
            return await post(
                f"/cases/{cid}/operator-events",
                {"event_id": str(uuid4()), "kind": kind, "note": note},
            )

        async def linked_case(title, number):
            case = await post("/cases", {"title": title, "client_id": "CLI-0001"})
            await post(
                f"/cases/{case['id']}/order-link",
                {"order_number": number, "expected_version": case["version"]},
            )
            return case["id"]

        def record(process, value):
            row = {
                "process": process,
                "case_id": value["case"]["id"],
                "status": value["case"]["status"],
                "orders": [o["number"] for o in value["orders"]],
                "source_ids": list(
                    {
                        s["chunk_id"]
                        for e in value["events"]
                        for s in e["payload"].get("sources", [])
                    }
                ),
            }
            results["steps"].append(row)
            print(json.dumps(row, ensure_ascii=False), flush=True)

        day = str(LimaClock().now().date() + timedelta(days=1))
        case = await post(
            "/cases", {"title": "QA real P1–P4 · datos SINTÉTICOS", "client_id": "CLI-0001"}
        )
        cid = case["id"]
        fixture = Path("tests/fixtures/guia-demo.png").read_bytes()
        upload = await client.post(
            f"/api/cases/{cid}/uploads", files={"file": ("guia-demo.png", fixture, "image/png")}
        )
        upload.raise_for_status()
        attachment_id = upload.json()["id"]
        attachment_hash = hashlib.sha256(fixture).hexdigest()
        value = await ask(
            cid,
            f"Prueba sintética P1. Solicito recojo: cliente CLI-0001, solicitante Operador Demo, correo demo@example.invalid, fecha exacta {day}, turno manana, tipo_ropa toallas; extrae el número de bolsas de la guía adjunta. Presenta los siete campos para confirmar; no registres sin mi confirmación.",
            [attachment_id],
        )
        assert value["case"]["status"] == "awaiting_review", value["messages"][-1]["content"]
        assert value["case"]["proposal"]["fields"]["bolsas"] == 3
        if restart:
            subprocess.run(["docker", "compose", "restart", "api", "worker"], check=True)
            for _ in range(60):
                try:
                    if (await client.get("/health/ready")).status_code == 200:
                        break
                except httpx.HTTPError:
                    pass
                await asyncio.sleep(0.5)
            recovered = await snapshot(cid)
            assert recovered["approvals"][-1]["id"] == value["approvals"][-1]["id"]
            results["restart_pending_approval_verified"] = True
            original = await client.get(f"/api/cases/{cid}/attachments/{attachment_id}")
            original.raise_for_status()
            assert hashlib.sha256(original.content).hexdigest() == attachment_hash
            results["attachment_persistence_verified"] = True
            results["attachment_sha256"] = attachment_hash
        value = await confirm(value)
        assert len(value["orders"]) == 1
        number = value["orders"][0]["number"]
        record("P1", value)
        value = await ask(
            cid,
            f"P2 logística: coordina el recojo del pedido {number} para el {day} por la mañana. Consulta la agenda real y ofrece opciones calculadas para que elija. No canceles el pedido.",
        )
        options = value["case"]["proposal"].get("options", [])
        assert options
        selected = next(
            (o for o in options if str(o["day"]) == day and o["shift"] == "manana"), options[0]
        )
        value = await confirm(value, {"option_id": selected["id"]})
        assert value["case"]["status"] == "scheduled"
        record("P2", value)
        quality = await linked_case("QA calidad · evidencia humana SINTÉTICA", number)
        await event(
            quality,
            "inspection",
            "DEMO SINTÉTICO: operador verificó guía, lote de toallas de algodón y conteo; sin manchas ni daño observado. Evidencia de laboratorio, no inspección real.",
        )
        await event(
            quality,
            "conformity",
            "DEMO SINTÉTICO: el responsable de calidad documenta conformidad del lote tras inspección de guía, material y conteo; apto para liberación en esta prueba.",
        )
        value = await ask(
            quality,
            "P3: revisa la inspección y conformidad ya registradas por el operador. Contrasta el procedimiento vigente y propone liberar este lote sintético para decisión humana. No inventes químicos ni acciones físicas.",
        )
        value = await confirm(value)
        assert value["case"]["status"] == "released"
        record("P3", value)
        incident = await linked_case("QA incidencia · caso SINTÉTICO", number)
        await event(
            incident,
            "observation",
            "DEMO SINTÉTICO: guía indica tres bolsas recibidas; cliente dice faltar una toalla. El operador confirma que los conteos son afirmaciones distintas y falta cotejo físico. Contrato y procedimiento demo vigentes disponibles.",
        )
        value = await ask(
            incident,
            "P4: reconstruye los hechos de esta incidencia sintética. Propón como solución administrativa una verificación física del conteo y búsqueda de la toalla. No atribuyas responsabilidad ni montos. Solicita aprobación humana del plan y mantén abierto hasta cumplimiento.",
        )
        value = await confirm(value)
        assert value["case"]["status"] == "awaiting_customer_acceptance_and_fulfillment"
        record("P4-plan", value)
        await event(
            incident,
            "customer_acceptance",
            "DEMO SINTÉTICO: el cliente acepta expresamente el plan autorizado de cotejo y búsqueda de la toalla.",
        )
        await event(
            incident,
            "fulfillment",
            "DEMO SINTÉTICO: responsable hizo el cotejo, localizó la toalla etiquetada aparte y registró su entrega; no hubo compensación monetaria.",
        )
        await event(
            incident,
            "conformity",
            "DEMO SINTÉTICO: responsable documenta conformidad expresa del cliente con entrega y criterio de cierre del expediente; referencia a cumplimiento registrado.",
        )
        value = await ask(
            incident,
            "P4: revisa el plan previamente autorizado y la aceptación, cumplimiento y conformidad humanas posteriores. Propón el cierre documentado para aprobación administrativa, sin realizar otros efectos.",
        )
        value = await confirm(value)
        assert value["case"]["status"] == "closed"
        record("P4-cierre", value)
        results["status"] = "passed"
        Path("artifacts").mkdir(exist_ok=True)
        Path("artifacts/full-demo-real.json").write_text(
            json.dumps(results, ensure_ascii=False, indent=2)
        )
        print("Demostración real P1–P4 verificada.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--restart", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.restart))
