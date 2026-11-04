from pydantic import SecretStr

from aquaclean.config import Settings
from aquaclean.infrastructure.observability.tracing import configure


def test_project_destination_does_not_set_partial_agent_address(monkeypatch):
    import os

    monkeypatch.setenv("LANGSMITH_AGENT_ENVIRONMENT", "local")
    monkeypatch.setenv("LANGSMITH_AGENT_ID", "")
    for key in [
        "LANGSMITH_TRACING",
        "LANGSMITH_PROJECT",
        "LANGSMITH_API_KEY",
        "LANGSMITH_ENDPOINT",
    ]:
        monkeypatch.setenv(key, "")
    settings = Settings(
        langsmith_tracing=True,
        langsmith_api_key=SecretStr("controlled-key-no-network"),
        langsmith_project="controlled-project",
        langsmith_agent_id="",
    )
    configure(settings)
    assert os.environ["LANGSMITH_PROJECT"] == "controlled-project"
    assert "LANGSMITH_AGENT_ENVIRONMENT" not in os.environ
    assert "LANGSMITH_AGENT_ID" not in os.environ


def test_pause_outcome_keeps_review_id_in_current_sdk_metadata(monkeypatch):
    from aquaclean.infrastructure.observability import tracing

    class Tree:
        def add_metadata(self, data):
            self.data = data

    tree = Tree()
    monkeypatch.setattr(tracing, "get_current_run_tree", lambda: tree)
    tracing.record_outcome("paused", "review-controlled")
    assert tree.data == {"application_status": "paused", "approval_id": "review-controlled"}


def test_empty_workspace_setting_clears_stale_sdk_environment(monkeypatch):
    import os

    monkeypatch.setenv("LANGSMITH_WORKSPACE_ID", "obsolete-workspace")
    settings = Settings(
        _env_file=None,
        langsmith_tracing=True,
        langsmith_api_key=SecretStr("controlled-key-no-network"),
        langsmith_project="controlled-project",
        langsmith_agent_id="",
        langsmith_workspace_id="",
    )
    configure(settings)
    assert "LANGSMITH_WORKSPACE_ID" not in os.environ
