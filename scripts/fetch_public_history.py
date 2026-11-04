"""Download public CPSC records. No Aqua Clean operational history is inferred.

This standalone ingestion fetches only official endpoints and discards contact information.
The reviewed snapshot is versioned and can be loaded offline with import-public-history.
"""

import asyncio
import hashlib
import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

import httpx

API = "https://www.saferproducts.gov/RestWebServices/Recall"
TERMS = [
    "washing",
    "laundry",
    "clothes dryer",
    "garment steamer",
    "clothing",
    "sleepwear",
    "pajamas",
    "bathrobe",
    "towel",
    "blanket",
]
CUTOFF = date(2026, 10, 16)


async def main():
    records = {}
    query_results = []
    async with httpx.AsyncClient(timeout=60, follow_redirects=True) as client:
        for term in TERMS:
            response = await client.get(API, params={"format": "json", "ProductName": term})
            response.raise_for_status()
            payload = response.json()
            query_results.append(
                {
                    "term": term,
                    "url": str(response.url),
                    "response_sha256": hashlib.sha256(response.content).hexdigest(),
                    "returned": len(payload),
                }
            )
            for item in payload:
                event_date = date.fromisoformat(item["RecallDate"][:10])
                if event_date > CUTOFF or urlsplit(item["URL"]).hostname not in {
                    "www.cpsc.gov",
                    "cpsc.gov",
                }:
                    continue
                # Store only public product/recall facts; not contacts, addresses or individual injury reports.
                clean = {
                    key: item[key]
                    for key in [
                        "RecallID",
                        "RecallNumber",
                        "RecallDate",
                        "Title",
                        "URL",
                        "Products",
                        "Hazards",
                        "Remedies",
                    ]
                }
                clean["event_date"] = str(event_date)
                clean["source_hash"] = hashlib.sha256(
                    json.dumps(clean, sort_keys=True, ensure_ascii=False).encode()
                ).hexdigest()
                records[str(item["RecallID"])] = clean
    result = {
        "publisher": "U.S. Consumer Product Safety Commission",
        "api_url": API,
        "documentation_url": "https://www.cpsc.gov/Recalls/CPSC-Recalls-Application-Program-Interface-API-Information",
        "license_metadata": "https://catalog.data.gov/dataset/recalls-api",
        "retrieved_at": datetime.now(ZoneInfo("America/Lima")).isoformat(),
        "cutoff_date": str(CUTOFF),
        "scope": "Referencias públicas externas de seguridad de productos/textiles; NO son incidentes, clientes ni políticas de Aqua Clean.",
        "queries": query_results,
        "records": sorted(records.values(), key=lambda x: (x["event_date"], x["RecallNumber"])),
    }
    path = Path("reference_data/cpsc-recalls.json")
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    Path("reference_data/cpsc-recalls.sha256").write_text(
        hashlib.sha256(path.read_bytes()).hexdigest() + "  cpsc-recalls.json\n"
    )
    print(
        json.dumps(
            {
                "path": str(path),
                "records": len(records),
                "first": result["records"][0]["event_date"],
                "last": result["records"][-1]["event_date"],
            }
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
