"""Controlled SDK tests. These do not constitute real LangSmith traces."""

import json
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from aquaclean.config import Settings
from scripts import langsmith_evidence as evidence


def settings(**kw):
    return Settings(_env_file=None, langsmith_project="aquaclean-test", **kw)


def span(identifier="span-child", **kw):
    return SimpleNamespace(
        id=identifier,
        trace_id="trace-root",
        name="controlled-span",
        run_type="llm",
        start_time=datetime(2026, 11, 4, tzinfo=UTC),
        end_time=None,
        extra={},
        **kw,
    )


@pytest.mark.asyncio
async def test_missing_key_never_connects_or_claims_no_remote_runs(monkeypatch):
    monkeypatch.setattr(evidence, "Client", lambda **_: pytest.fail("No connection without key"))
    result = await evidence.discover(settings(langsmith_api_key=SecretStr("")))
    assert result["status"] == "blocked" and result["search_performed"] is False
    assert "new_execution_required" not in result
    assert result["traces"] == [] and result["new_model_calls"] is False


def test_summary_excludes_private_fields_and_preserves_unknown_metrics():
    r = span(
        inputs={"api_key": "SECRET"},
        outputs={"text": "PRIVATE"},
        metadata={"app_run_id": "app-local", "private": "DO-NOT-EXPORT"},
    )
    result = evidence.summary(r)
    assert result["duration_ms"] is result["total_tokens"] is result["cost_usd"] is None
    assert result["metadata"] == {"app_run_id": "app-local"}
    assert all(x not in json.dumps(result) for x in ["SECRET", "PRIVATE", "DO-NOT-EXPORT"])
    assert result["id"] != "app-local"


class FakeClient:
    def __init__(self, **kw):
        self.queries = []
        self.runs = SimpleNamespace(query=self.query, get_url=self.get_url)
        self.traces = SimpleNamespace(list_runs=self.tree)

    def read_project(self, **kw):
        return SimpleNamespace(
            id="project-id",
            tenant_id="workspace-id",
            name="aquaclean-test",
            url="https://smith.langchain.com/project-id",
        )

    async def query(self, **kw):
        self.queries.append(kw)
        for identifier, resume in [("root-before", False), ("root-after", True)]:
            r = span(
                identifier,
                metadata={
                    "synthetic": True,
                    "app_run_id": "app-" + identifier,
                    "case_id": "case-local",
                    "thread_id": "same-thread",
                    "approval_id": "same-review",
                    "resume": resume,
                },
            )
            r.trace_id = identifier
            yield r

    async def tree(self, trace_id, **kw):
        return SimpleNamespace(items=[span(parent_run_ids=[trace_id], total_tokens=12)])

    async def get_url(self, run_id, *, project_id, trace_id):
        return SimpleNamespace(url="https://smith.langchain.com/" + run_id)

    def close(self):
        pass


@pytest.mark.asyncio
async def test_remote_discovery_reads_existing_data_and_correlates_human_resume(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(evidence, "Client", lambda **_: fake)
    result = await evidence.discover(settings(langsmith_api_key=SecretStr("controlled-no-network")))
    assert result["status"] == "verified_existing_traces"
    assert result["search_performed"] and len(result["traces"]) == 2
    assert result["new_model_calls"] is False
    pair = result["thread_correlations"]["same-thread"]
    assert pair[0]["trace_id"] != pair[1]["trace_id"]
    assert pair[0]["approval_id"] == pair[1]["approval_id"] == "same-review"
    assert fake.queries[0]["filter"] == 'eq(name, "AquaClean.application_run")'
    assert fake.queries[0]["project_ids"] == ["project-id"]
    assert "INPUTS" not in fake.queries[0]["selects"]


@pytest.mark.asyncio
async def test_query_errors_do_not_export_secret_exception_text(monkeypatch):
    class Unavailable(FakeClient):
        def read_project(self, **kw):
            raise RuntimeError("SECRET-REQUEST-HEADERS")

    monkeypatch.setattr(evidence, "Client", Unavailable)
    result = await evidence.discover(settings(langsmith_api_key=SecretStr("controlled-no-network")))
    assert result["status"] == "blocked" and result["error_type"] == "RuntimeError"
    assert "SECRET" not in json.dumps(result)
    assert result["search_performed"] is False


@pytest.mark.asyncio
async def test_workspace_mismatch_prevents_query(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr(evidence, "Client", lambda **_: fake)
    result = await evidence.discover(
        settings(
            langsmith_api_key=SecretStr("controlled-no-network"),
            langsmith_workspace_id="other-workspace",
        )
    )
    assert result["status"] == "blocked" and fake.queries == []


@pytest.mark.asyncio
async def test_no_matching_runs_only_after_successful_remote_query(monkeypatch):
    class Empty(FakeClient):
        async def query(self, **kw):
            for _ in []:
                yield None

    monkeypatch.setattr(evidence, "Client", Empty)
    result = await evidence.discover(settings(langsmith_api_key=SecretStr("controlled-no-network")))
    assert result["search_performed"] and result["new_execution_required"]
    assert result["status"] == "no_matching_traces_in_search_window"


def test_query_and_url_arguments_match_installed_sdk_without_network():
    import inspect

    from langsmith import Client
    from langsmith.types.run_get_url_response import RunGetURLResponse

    client = Client(api_key="controlled-inspection-no-network", auto_batch_tracing=False)
    try:
        inspect.signature(client.runs.query).bind(
            project_ids=["project"],
            is_root=True,
            min_start_time=datetime(2026, 11, 4, tzinfo=UTC),
            filter='eq(name, "AquaClean.application_run")',
            selects=evidence.FIELDS,
            page_size=20,
        )
        inspect.signature(client.runs.get_url).bind("span", project_id="project", trace_id="trace")
        response = RunGetURLResponse(url="https://smith.langchain.com/controlled")
        assert response.url.startswith("https://smith.langchain.com/")
    finally:
        client.close()
