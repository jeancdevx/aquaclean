"""Search LangSmith first; export genuine SDK data without inference or raw inputs."""

import argparse
import asyncio
import json
from pathlib import Path

from langsmith_evidence import discover

from aquaclean.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=14, choices=range(1, 402))
    parser.add_argument("--limit", type=int, default=20, choices=range(1, 101))
    args = parser.parse_args()
    target = Path(Path("artifacts/semana10/CURRENT").read_text().strip()) / "05-langsmith"
    target.mkdir(parents=True, exist_ok=True)
    result = asyncio.run(discover(Settings(), days=args.days, limit=args.limit))
    output = target / "trazas.json"
    if (
        output.exists()
        and json.loads(output.read_text()).get("traces")
        and result["status"] == "blocked"
    ):
        output = target / "intento-exportacion-bloqueado.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    if result["status"] == "blocked":
        (target / "PENDIENTE.md").write_text(
            "# LangSmith requerido: acceso pendiente\n\nLa consulta remota no se pudo realizar. No se deduce que no existan trazas. No hay nuevas llamadas al proveedor ni capturas fabricadas. Motivo y comprobaciones saneadas en trazas.json. Ver documentacion-activa/docs/LANGSMITH.md para el recorrido y comandos preparados. Los logs locales solo son auxiliares.\n"
        )
    print(
        json.dumps(
            {
                "status": result["status"],
                "search_performed": result["search_performed"],
                "verified_traces": len(result["traces"]),
                "new_model_calls": False,
                "output": str(output),
            }
        )
    )
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
