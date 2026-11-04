"""Read-only verification after restart, using the actual captured case and bytes."""

import asyncio
import hashlib
import json
import os
import subprocess
from pathlib import Path

import httpx
from local_environment import local_env

from aquaclean.config import Settings
from aquaclean.infrastructure.persistence.database import Database


async def main():
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip())
    flow = json.loads((root / "07-aplicacion/recorrido-proveedor-real.json").read_text())
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000", timeout=10) as client:
        for _ in range(60):
            try:
                if (await client.get("/health/ready")).is_success:
                    break
            except httpx.HTTPError:
                pass
            await asyncio.sleep(0.5)
        response = await client.get("/api/cases/" + flow["reception_case_id"])
        response.raise_for_status()
        snapshot = response.json()
        assert (
            snapshot["orders"][0]["status"] == "CLOSED" and snapshot["retail"]["balance"] == "0.00"
        )
        media = []
        for attachment in snapshot["attachments"]:
            original = await client.get(
                f"/api/cases/{flow['reception_case_id']}/attachments/{attachment['id']}"
            )
            original.raise_for_status()
            current_hash = hashlib.sha256(original.content).hexdigest()
            assert current_hash == attachment["hash"]
            media.append(
                {
                    "id": attachment["id"],
                    "mime": attachment["mime"],
                    "sha256": current_hash,
                    "perception_status": attachment["perception_status"],
                }
            )
    os.environ.update(local_env())
    db = Database(Settings())
    await db.open()
    try:
        collections = await db.all(
            "SELECT c.model,c.dimension,count(ch.id) chunks FROM app.collections c JOIN app.chunks ch ON ch.collection_id=c.id WHERE c.model NOT LIKE 'fake%%' GROUP BY c.model,c.dimension"
        )
        legacy = await db.one(
            "SELECT count(*) orders,count(*) FILTER(WHERE total IS NULL AND received_at IS NULL) without_fabricated_retail_fields FROM app.orders WHERE kind='legacy_v1'"
        )
        legacy_items = await db.one(
            "SELECT count(*) n FROM app.order_items i JOIN app.orders o ON o.id=i.order_id WHERE o.kind='legacy_v1'"
        )
        notices = await db.all(
            "SELECT status,attempts FROM app.outbox WHERE case_id=%s AND payload->>'type'='order_ready'",
            (flow["reception_case_id"],),
        )
        assert len(notices) == 1 and notices[0]["status"] == "delivered_local"
        assert legacy_items["n"] == 0
        state = {
            "kind": "actual_post_restart_read_verification",
            "case_id": flow["reception_case_id"],
            "order_id": flow["service_order_id"],
            "order_status": "CLOSED",
            "balance": "0.00",
            "originals_sha256_verified": media,
            "real_embedding_collections": collections,
            "legacy_current_snapshot": legacy,
            "legacy_items": legacy_items["n"],
            "ready_local_notice": notices,
            "image_id": subprocess.check_output(
                ["docker", "image", "inspect", "aquaclean-local:0.1.0", "--format", "{{.Id}}"],
                text=True,
            ).strip(),
            "limitation": "Current legacy snapshot only; no fabricated row-by-row pre-migration checksum baseline",
        }
        (root / "08-pruebas/persistencia-tras-reinicio.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2)
        )
        print(
            json.dumps(
                {
                    "status": "passed",
                    "media": len(media),
                    "collections": collections,
                    "ready_notices": len(notices),
                }
            )
        )
    finally:
        await db.close()


if __name__ == "__main__":
    asyncio.run(main())
