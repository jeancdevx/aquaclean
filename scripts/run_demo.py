"""V2 real HTTP/Playwright lifecycle demo. Never substitutes a fake provider.

Requires the local Compose stack, web pnpm dependencies, and Gemini configured.
The V1 corporate script is preserved under docs/antecedentes/v1/scripts/.
"""

import argparse
import asyncio
import subprocess
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def main():
    parser = argparse.ArgumentParser(
        description="Recorrido V2 real con datos sintéticos; llamadas Gemini facturables."
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Compatibilidad: V2 siempre verifica reinicio durante HITL, conservando volúmenes.",
    )
    parser.parse_args()
    pointer = Path("artifacts/semana10/CURRENT")
    if not pointer.exists():
        revision = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()
        directory = Path("artifacts/semana10") / (
            datetime.now(ZoneInfo("America/Lima")).strftime("%Y-%m-%d-%H%M")
            + "-"
            + revision
            + "-working"
        )
        for name in [
            "01-lcel",
            "02-langgraph",
            "03-bpmn",
            "04-hitl",
            "05-langsmith",
            "06-deepagents",
            "07-aplicacion",
            "08-pruebas",
            "09-ecosistema",
        ]:
            (directory / name).mkdir(parents=True, exist_ok=True)
        pointer.write_text(str(directory))
    if not Path("artifacts/semana10/media/recepcion-sintetica.wav").exists():
        from create_retail_media import main as create_media

        asyncio.run(create_media())
    return subprocess.call(["node", "web/scripts/capture-retail-real.mjs"])


if __name__ == "__main__":
    raise SystemExit(main())
