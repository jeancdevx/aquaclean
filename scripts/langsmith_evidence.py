"""Read-only LangSmith discovery and redacted evidence projection. No model imports."""

import asyncio
from datetime import UTC, datetime, timedelta
from importlib.metadata import version
from urllib.parse import urlparse

from langsmith import Client

REGIONS = {
    "api.smith.langchain.com": "US",
    "eu.api.smith.langchain.com": "EU",
    "apac.api.smith.langchain.com": "APAC",
    "aws.api.smith.langchain.com": "AWS US",
}
FIELDS = [
    "ID",
    "TRACE_ID",
    "NAME",
    "RUN_TYPE",
    "STATUS",
    "START_TIME",
    "END_TIME",
    "PARENT_RUN_IDS",
    "METADATA",
    "EXTRA",
    "TOTAL_TOKENS",
    "PROMPT_TOKENS",
    "COMPLETION_TOKENS",
    "TOTAL_COST",
    "DOTTED_ORDER",
    "APP_PATH",
    "THREAD_ID",
]
METADATA = {
    "commit",
    "source_sha256",
    "prompt_version",
    "process",
    "app_run_id",
    "thread_id",
    "case_id",
    "resume",
    "synthetic",
    "approval_id",
    "application_status",
    "ls_provider",
    "ls_model_name",
    "ls_model_type",
}


def configuration(settings):
    parsed = urlparse(settings.langsmith_endpoint)
    return {
        "checked_at": datetime.now(UTC).isoformat(),
        "sdk": version("langsmith"),
        "api_key_present": bool(settings.langsmith_api_key.get_secret_value()),
        "tracing_enabled": settings.langsmith_tracing,
        "endpoint_host": parsed.hostname,
        "configured_region": REGIONS.get(parsed.hostname, "unverified"),
        "region_verified_against_account": False,
        "workspace_id_configured": settings.langsmith_workspace_id or None,
        "workspace_verified": False,
        "project_configured": settings.langsmith_project or None,
        "agent_id_configured": settings.langsmith_agent_id or None,
        "agent_environment": settings.langsmith_agent_environment
        if settings.langsmith_agent_id
        else None,
        "account_plan": "not_verified",
        "free_plan_required": True,
        "new_model_calls": False,
    }


def _metadata(run):
    extra = getattr(run, "extra", None) or {}
    return {**extra.get("metadata", {}), **(getattr(run, "metadata", None) or {})}


def summary(run):
    """No raw inputs/outputs/errors: export only IDs, public structure and reported metrics."""
    start, end = getattr(run, "start_time", None), getattr(run, "end_time", None)
    if isinstance(start, str):
        start = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if isinstance(end, str):
        end = datetime.fromisoformat(end.replace("Z", "+00:00"))
    meta = _metadata(run)
    parents = getattr(run, "parent_run_ids", None) or []
    return {
        "id": str(run.id),
        "trace_id": str(run.trace_id),
        "parent_run_ids": [str(p) for p in parents],
        "name": run.name,
        "type": str(run.run_type).lower(),
        "status": getattr(run, "status", None),
        "start_time": start.isoformat() if start else None,
        "end_time": end.isoformat() if end else None,
        "duration_ms": round((end - start).total_seconds() * 1000) if start and end else None,
        "total_tokens": getattr(run, "total_tokens", None),
        "input_tokens": getattr(run, "prompt_tokens", None),
        "output_tokens": getattr(run, "completion_tokens", None),
        "cost_usd": str(run.total_cost) if getattr(run, "total_cost", None) is not None else None,
        "metadata": {k: v for k, v in meta.items() if k in METADATA},
        "thread_id": getattr(run, "thread_id", None) or meta.get("thread_id"),
        "dotted_order": getattr(run, "dotted_order", None),
    }


async def resolve_destination(client, settings):
    if settings.langsmith_project and settings.langsmith_agent_id:
        raise ValueError("Configure project OR agent, not both")
    if settings.langsmith_agent_id:
        resolved = await client.sessions.resolve(
            kind="AGENT",
            id=settings.langsmith_agent_id,
            environment=settings.langsmith_agent_environment.upper(),
        )
        project = await asyncio.to_thread(client.read_project, project_id=str(resolved.session_id))
        kind = "agent/environment"
    elif settings.langsmith_project:
        project = await asyncio.to_thread(
            client.read_project, project_name=settings.langsmith_project
        )
        kind = "project"
    else:
        # A single explicitly Aqua Clean-named destination can be reused read-only.
        projects = await asyncio.to_thread(
            lambda: list(client.list_projects(name_contains="aquaclean", limit=20))
        )
        if len(projects) != 1:
            raise ValueError("No unique Aqua Clean destination; configure project or agent")
        project, kind = projects[0], "single_discovered_aquaclean_project"
    if not project.tenant_id:
        raise ValueError("Resolved destination did not identify a workspace")
    workspace = str(project.tenant_id)
    if settings.langsmith_workspace_id and workspace != settings.langsmith_workspace_id:
        raise ValueError("Configured workspace differs from resolved destination")
    return project, {
        "addressing": kind,
        "project_id": str(project.id),
        "project_name": project.name,
        "project_url": project.url,
        "workspace_id_verified": workspace,
    }


async def discover(settings, *, days=14, limit=20):
    result = configuration(settings)
    result.update(status="blocked", search_performed=False, traces=[], capture_targets=[])
    if not result["api_key_present"]:
        result["reason"] = "LANGSMITH_API_KEY absent; existing remote executions cannot be queried"
        return result
    parsed = urlparse(settings.langsmith_endpoint)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in REGIONS
        or parsed.username
        or parsed.password
    ):
        result["reason"] = "Verify the configured official cloud region endpoint"
        return result
    client = Client(
        api_key=settings.langsmith_api_key.get_secret_value(),
        api_url=settings.langsmith_endpoint,
        workspace_id=settings.langsmith_workspace_id or None,
        auto_batch_tracing=False,
        timeout_ms=20000,
    )
    try:
        project, destination = await resolve_destination(client, settings)
        result.update(
            destination=destination, workspace_verified=True, region_verified_against_account=True
        )
        roots = []
        async for run in client.runs.query(
            project_ids=[str(project.id)],
            is_root=True,
            min_start_time=datetime.now(UTC) - timedelta(days=days),
            filter='eq(name, "AquaClean.application_run")',
            selects=FIELDS,
            page_size=min(limit, 100),
        ):
            roots.append(run)
            if len(roots) >= limit:
                break
        result.update(search_performed=True, window_days=days, root_limit=limit)
        for root in roots:
            # Export only traces explicitly marked synthetic by Aqua Clean's instrumentation.
            if _metadata(root).get("synthetic") is not True:
                continue
            tree = await client.traces.list_runs(
                str(root.trace_id), project_id=str(project.id), selects=FIELDS
            )
            spans = [summary(r) for r in tree.items]
            root_summary = summary(root)
            url = (
                await client.runs.get_url(
                    str(root.id), project_id=str(project.id), trace_id=str(root.trace_id)
                )
            ).url
            result["traces"].append(
                {
                    "app_run_id": root_summary["metadata"].get("app_run_id"),
                    "case_id": root_summary["metadata"].get("case_id"),
                    "thread_id": root_summary["thread_id"],
                    "url": url,
                    "run": root_summary,
                    "spans": spans,
                }
            )
            result["capture_targets"].append(
                {"kind": "trace_tree", "url": url, "run_id": str(root.id)}
            )
            for span in spans:
                kind = (
                    "model"
                    if span["type"] == "llm"
                    else "deepagents"
                    if span["name"] == "P4.DeepAgents.investigation"
                    else "tool"
                    if span["type"] == "tool"
                    else None
                )
                if kind:
                    result["capture_targets"].append(
                        {
                            "kind": kind,
                            "url": (
                                await client.runs.get_url(
                                    span["id"],
                                    project_id=str(project.id),
                                    trace_id=span["trace_id"],
                                )
                            ).url,
                            "run_id": span["id"],
                        }
                    )
        groups = {}
        for trace in result["traces"]:
            if trace["thread_id"]:
                groups.setdefault(trace["thread_id"], []).append(
                    {
                        "app_run_id": trace["app_run_id"],
                        "langsmith_run_id": trace["run"]["id"],
                        "trace_id": trace["run"]["trace_id"],
                        "url": trace["url"],
                        "resume": trace["run"]["metadata"].get("resume"),
                        "approval_id": trace["run"]["metadata"].get("approval_id"),
                    }
                )
        result["thread_correlations"] = groups
        result["status"] = (
            "verified_existing_traces"
            if result["traces"]
            else "no_matching_traces_in_search_window"
        )
        result["new_execution_required"] = not bool(result["traces"])
        result["capture_targets"].insert(0, {"kind": "execution_list", "url": project.url})
        return result
    except Exception as exc:
        # Exception strings/HTTP bodies may contain credentials. Export only the class.
        result.update(
            status="blocked",
            reason="Region, workspace, destination or trace query failed",
            error_type=type(exc).__name__,
        )
        return result
    finally:
        client.close()
