"""Optional LangSmith tracing; application IDs never masquerade as span IDs."""

import json
import os
import subprocess
from pathlib import Path

from langsmith import get_current_run_tree

from aquaclean.agents.prompts import PROMPT_VERSION
from aquaclean.domain.errors import DomainError


def configure(settings):
    if not settings.langsmith_tracing:
        os.environ["LANGSMITH_TRACING"] = "false"
        return
    if not settings.langsmith_api_key.get_secret_value():
        raise DomainError(
            "LANGSMITH_TRACING exige LANGSMITH_API_KEY local.", "tracing_configuration", 503
        )
    if bool(settings.langsmith_project) == bool(settings.langsmith_agent_id):
        raise DomainError(
            "Seleccione proyecto O agente según el tipo de workspace; no ambos.",
            "tracing_configuration",
            503,
        )
    if settings.langsmith_agent_id:
        os.environ.pop("LANGSMITH_PROJECT", None)
    else:
        os.environ.pop("LANGSMITH_AGENT_ID", None)
        os.environ.pop("LANGSMITH_AGENT_ENVIRONMENT", None)
    for key in ["tracing", "project", "agent_id", "agent_environment", "endpoint", "workspace_id"]:
        value = getattr(settings, "langsmith_" + key)
        if value and (key != "agent_environment" or settings.langsmith_agent_id):
            os.environ["LANGSMITH_" + key.upper()] = (
                str(value).lower() if isinstance(value, bool) else str(value)
            )
        else:
            os.environ.pop("LANGSMITH_" + key.upper(), None)
    os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key.get_secret_value()


def metadata(runtime, run):
    build = (
        json.loads(Path("config/build-revision.json").read_text())
        if Path("config/build-revision.json").exists()
        else {}
    )
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], stderr=subprocess.DEVNULL, text=True
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = build.get("commit", os.environ.get("APP_REVISION", "working-tree-unavailable"))
    cid = str(run["case_id"])
    return {
        "commit": commit,
        "source_sha256": build.get("source_sha256", "unavailable"),
        "prompt_version": PROMPT_VERSION,
        "app_run_id": str(run["id"]),
        "case_id": cid,
        "thread_id": f"org:{runtime.actor.organization_id}:case:{cid}",
        "synthetic": True,
        "process": "supervisor",
        "resume": bool(run["input"].get("resume")),
        "approval_id": run["input"].get("approval_id"),
    }


def record_outcome(status, approval_id=None):
    """Keep application pause/failure distinct from the SDK transport span status."""
    tree = get_current_run_tree()
    if tree is not None:
        details = {"application_status": status}
        if approval_id:
            details["approval_id"] = str(approval_id)
        tree.add_metadata(details)


async def correlate(runtime, run):
    tree = get_current_run_tree()
    if not runtime.settings.langsmith_tracing or tree is None:
        return
    meta = metadata(runtime, run)
    tree.add_metadata(meta)
    # These IDs come from the SDK's actual RunTree, not app UUIDs.
    await runtime.repo.db.execute(
        "INSERT INTO app.trace_links(app_run_id,span_id,trace_id,thread_id,url) VALUES(%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING",
        (run["id"], tree.id, tree.trace_id, meta["thread_id"], tree.get_url()),
    )
