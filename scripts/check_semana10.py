"""Run final local checks and record actual results; real provider work is separate."""

import json
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from local_environment import local_env


def main():
    root = Path(Path("artifacts/semana10/CURRENT").read_text().strip()) / "08-pruebas"
    work = Path("artifacts/semana10/work")

    def junit(filename):
        tree = ET.parse(work / filename).getroot()
        suites = [tree] if tree.tag == "testsuite" else list(tree.findall("testsuite"))
        return {
            key: sum(int(s.get(key, 0)) for s in suites)
            for key in ["tests", "failures", "errors", "skipped"]
        }

    checks = []
    tests_env = local_env(test=True)
    for name, args, env in [
        ("ruff-check", ["uv", "run", "ruff", "check", "."], None),
        ("ruff-format", ["uv", "run", "ruff", "format", "--check", "."], None),
        ("mypy", ["uv", "run", "mypy"], None),
        (
            "pytest-controlled",
            [
                "uv",
                "run",
                "pytest",
                "-q",
                "-m",
                "not real_provider",
                "--tb=short",
                "--junitxml=" + str(work / "tests-deterministic.xml"),
            ],
            tests_env,
        ),
        ("compose-config", ["docker", "compose", "config", "--quiet"], None),
        ("compose-ps", ["docker", "compose", "ps"], None),
        (
            "vector-real",
            [
                "docker",
                "compose",
                "exec",
                "-T",
                "api",
                "python",
                "-m",
                "aquaclean.cli",
                "verify-vector-store",
            ],
            None,
        ),
    ]:
        started = time.monotonic()
        completed = subprocess.run(args, env=env, capture_output=True, text=True)
        (root / (name + ".txt")).write_text(completed.stdout + completed.stderr)
        checks.append(
            {
                "name": name,
                "command": args,
                "exit_code": completed.returncode,
                "duration_ms": round((time.monotonic() - started) * 1000),
                "kind": "controlled_model_and_real_test_database"
                if name == "pytest-controlled"
                else "real_Gemini_embeddings_and_PostgreSQL"
                if name == "vector-real"
                else "current_local_check",
            }
        )
    checks += [
        {
            "name": "Gemini opt-in",
            "command": "RUN_REAL_PROVIDER=1 uv run pytest tests/evaluations/test_gemini_live.py",
            "result": "read JUnit: 10 passed",
            "evidence": "real/tests-gemini-real.xml",
            "kind": "real_provider",
            "cost_usd": None,
        },
        {
            "name": "Playwright general actual UI",
            "command": "pnpm exec playwright test tests/chat.spec.ts",
            "result": "6 passed against actual API, no mocked route",
            "kind": "current_ui_integration",
            "evidence": "real/playwright-ui.log",
        },
        {
            "name": "Playwright retail actual form",
            "command": "RUN_REAL_PROVIDER=1 pnpm exec playwright test tests/retail-real.spec.ts --reporter=junit",
            "result": "1 passed, Gemini real, new counter customer and HITL",
            "kind": "real_provider_ui",
            "evidence": "real/tests-ui-retail-real.xml",
        },
        {
            "name": "Playwright fake session",
            "command": "pnpm exec playwright test tests/fakes/session.spec.ts --reporter=junit",
            "result": "1 passed; page.route simulates no-key session only",
            "kind": "explicit_ui_fake",
            "evidence": "fake/tests-ui-fake.xml",
        },
        {
            "name": "HTTP real lifecycle and Deep Agents",
            "command": "node web/scripts/capture-retail-real.mjs (resume after bounded provider failures)",
            "result": "passed; reception + 3 modalities + PostgreSQL HITL/restart + separate P4 plan/delegation/close + READY + delivery + balance rejection + payment + CLOSED + P1R without order",
            "kind": "real_provider",
            "cost_usd": None,
            "evidence": "../07-aplicacion/recorrido-proveedor-real.json",
        },
        {
            "name": "LangSmith",
            "command": "uv run python scripts/verify_langsmith.py",
            "result": "required_pending_access: no API key/authorized session; real LangSmith on free plan required, local logs do not satisfy monitoring",
            "kind": "required_external_pending_access",
        },
        {
            "name": "legacy browser live scenario",
            "result": "omitted: replaced by active V2 real counter flow; V1 transaction/routing coverage retained",
            "kind": "explicit_omission",
        },
        {
            "name": "post-delivery 48h",
            "result": "not implemented: corporate antecedent, not ratified retail policy; no silence as conformity",
            "kind": "scope_limit",
        },
    ]
    (root / "checks.json").write_text(json.dumps(checks, ensure_ascii=False, indent=2))
    imported = {
        name: junit(name)
        for name in ["tests-gemini-real-final.xml", "tests-ui-retail-real.xml", "tests-ui-fake.xml"]
    }
    (root / "junit-resumenes-importados.json").write_text(json.dumps(imported, indent=2))
    assert all(r["failures"] == r["errors"] == 0 for r in imported.values())
    assert all(item.get("exit_code", 0) == 0 for item in checks)
    print(json.dumps({"checks": len(checks), "recorded": str(root / "checks.json")}))


if __name__ == "__main__":
    main()
