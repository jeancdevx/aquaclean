import hashlib
import json
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.persistence.database import jsonb


async def import_history(db, path: Path = Path("reference_data/cpsc-recalls.json")) -> dict:
    content = path.read_bytes()
    checksum = hashlib.sha256(content).hexdigest()
    expected = path.with_suffix(".sha256").read_text().split()[0]
    if checksum != expected:
        raise DomainError(
            "El snapshot histórico no coincide con su checksum.", "source_integrity", 409
        )
    payload = json.loads(content)
    cutoff = date.fromisoformat(payload["cutoff_date"])
    import_id = "cpsc:" + checksum[:24]
    inserted = 0
    async with db.pool.connection() as conn, conn.transaction():
        await conn.execute(
            "INSERT INTO reference.imports(id,publisher,api_url,retrieved_at,cutoff_date,sha256,record_count,selection) VALUES(%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
            (
                import_id,
                payload["publisher"],
                payload["api_url"],
                payload["retrieved_at"],
                cutoff,
                checksum,
                len(payload["records"]),
                jsonb(payload["queries"]),
            ),
        )
        for item in payload["records"]:
            if date.fromisoformat(item["event_date"]) > cutoff or urlsplit(
                item["URL"]
            ).hostname not in {"cpsc.gov", "www.cpsc.gov"}:
                raise DomainError(
                    "Fecha o fuente del registro histórico inválida.", "source_integrity", 409
                )
            verify = {k: v for k, v in item.items() if k != "source_hash"}
            if (
                hashlib.sha256(
                    json.dumps(verify, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                != item["source_hash"]
            ):
                raise DomainError("Registro histórico alterado.", "source_integrity", 409)
            result = await conn.execute(
                "INSERT INTO reference.recalls(id,import_id,recall_number,event_date,title,source_url,products,hazards,remedies,source_hash,source_payload) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
                (
                    str(item["RecallID"]),
                    import_id,
                    item["RecallNumber"],
                    item["event_date"],
                    item["Title"],
                    item["URL"],
                    jsonb(item["Products"]),
                    jsonb(item["Hazards"]),
                    jsonb(item["Remedies"]),
                    item["source_hash"],
                    jsonb(item),
                ),
            )
            inserted += result.rowcount
    return {
        "status": "imported",
        "publisher": payload["publisher"],
        "records": len(payload["records"]),
        "inserted": inserted,
        "sha256": checksum,
        "synthetic": False,
        "scope": "Referencias externas; no operaciones de Aqua Clean",
    }


async def search_history(db, query: str) -> list[dict]:
    import re

    words = [word for word in re.findall(r"[\w-]+", query) if len(word) >= 4][:15]
    if not words:
        return []
    rows = await db.all(
        "SELECT * FROM reference.recalls WHERE title ILIKE ANY(%s::text[]) OR recall_number=ANY(%s::text[]) ORDER BY event_date DESC LIMIT 5",
        ([f"%{w}%" for w in words], words),
    )
    return [
        {
            "chunk_id": "historical:CPSC:" + r["id"],
            "document_id": "CPSC:" + r["recall_number"],
            "title": r["title"],
            "section": "public_recall",
            "version": str(r["event_date"]),
            "page": None,
            "content": json.dumps(
                {
                    "date": str(r["event_date"]),
                    "products": r["products"],
                    "hazards": r["hazards"],
                    "remedies": r["remedies"],
                },
                ensure_ascii=False,
            ),
            "source_url": r["source_url"],
            "hash": r["source_hash"],
            "source_kind": "external_historical_reference",
            "synthetic": False,
        }
        for r in rows
    ]
