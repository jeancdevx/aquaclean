"""Verify destination and search existing traces read-only, without exposing credentials."""

import argparse
import asyncio
import json
from pathlib import Path

from langsmith_evidence import discover

from aquaclean.config import Settings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = asyncio.run(discover(Settings()))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(
        json.dumps(
            {
                k: v
                for k, v in report.items()
                if k not in {"traces", "capture_targets", "thread_correlations"}
            },
            ensure_ascii=False,
            default=str,
        )
    )
    print(
        json.dumps({"existing_exportable_traces": len(report["traces"]), "new_model_calls": False})
    )
    return 2 if report["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())
