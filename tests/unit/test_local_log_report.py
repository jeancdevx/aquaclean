"""Controlled inputs test the exporter, not a claimed provider/production execution."""

from copy import deepcopy

import pytest

from scripts.local_log_report import build_report, render_html


def snapshot():
    def event(sequence, rid, kind, payload, second):
        return {
            "event_id": f"event-{sequence}",
            "sequence": sequence,
            "case_id": "case-1",
            "run_id": rid,
            "type": kind,
            "payload": payload,
            "created_at": f"2026-11-04T00:00:{second:02d}+00:00",
        }

    return {
        "case": {
            "id": "case-1",
            "organization_id": "org-test",
            "status": "closed",
            "process": "P4",
        },
        "runs": [
            {"id": "run-1", "status": "paused", "created_at": "2026-11-04T00:00:00+00:00"},
            {"id": "run-2", "status": "completed", "created_at": "2026-11-04T00:00:10+00:00"},
        ],
        "events": [
            event(1, "run-1", "run.started", {}, 0),
            event(
                2,
                "run-1",
                "agent.completed",
                {
                    "agent": "P4",
                    "usage": {
                        "tokens": [{"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}]
                    },
                },
                1,
            ),
            event(3, "run-1", "approval.requested", {"approval_id": "review-1"}, 2),
            event(4, "run-1", "run.completed", {"status": "paused"}, 3),
            event(
                5,
                "run-2",
                "approval.resolved",
                {"approval_id": "review-1", "action": "approve"},
                10,
            ),
            event(6, "run-2", "run.started", {}, 11),
            event(7, "run-2", "run.completed", {"status": "completed"}, 12),
        ],
    }


def report(snapshots=None, deep=None):
    return build_report(
        snapshots or [snapshot()],
        deep or [],
        exported_at="2026-11-04T06:00:00-05:00",
        provenance={"mode": "controlled test"},
    )


def test_human_wait_is_correlated_without_becoming_model_run_time():
    result = report()
    assert result["runs"][0]["duration_ms_from_events"] == 3000
    assert result["runs"][1]["duration_ms_from_events"] == 1000
    assert result["approvals"][0]["pause_to_decision_ms_from_events"] == 8000
    assert (
        result["approvals"][0]["request_app_run_id"] != result["approvals"][0]["resume_app_run_id"]
    )
    assert result["events"][0]["created_at"] == "2026-11-04T00:00:00+00:00"


def test_deep_usage_not_double_counted_from_echoed_agent_event():
    result = report(
        deep=[
            {
                "app_run_id": "run-1",
                "result": {
                    "model_calls": 1,
                    "usage": [{"input_tokens": 10, "output_tokens": 2, "total_tokens": 12}, {}],
                    "proposal": {},
                    "journal": [],
                },
            }
        ]
    )
    assert result["runs"][0]["agent_usage"] == []
    assert result["runs"][0]["deep_agents"]["tokens_reported"]["total_tokens"] == 12


def test_missing_usage_duration_cost_are_unknown_and_no_fake_langsmith_ids():
    s = snapshot()
    s["events"] = []
    result = report([s], deep=[{"app_run_id": "run-1", "result": {"journal": []}}])
    run = result["runs"][0]
    assert run["duration_ms_from_events"] is None
    assert run["deep_agents"]["tokens_reported"] is None
    assert run["deep_agents"]["cost_usd_reported"] is None
    assert result["langsmith"]["trace_ids"] == []


def test_duplicate_snapshots_deduplicate_immutable_events():
    s = snapshot()
    assert len(report([s, deepcopy(s)])["events"]) == len(s["events"])


def test_conflicting_event_id_rejected():
    s, changed = snapshot(), snapshot()
    changed["events"][0]["payload"] = {"status": "different"}
    with pytest.raises(ValueError, match="Conflicting"):
        report([s, changed])


def test_payload_contacts_secrets_and_message_text_not_exported():
    s = snapshot()
    s["case"]["contact"] = "PRIVATE-CONTACT"
    s["events"][0]["payload"] = {
        "api_key": "SECRET-KEY",
        "text": "PRIVATE-MESSAGE",
        "rationale_summary": "PRIVATE-REASONING",
    }
    html = render_html(report([s]))
    assert all(
        value not in html
        for value in ["PRIVATE-CONTACT", "SECRET-KEY", "PRIVATE-MESSAGE", "PRIVATE-REASONING"]
    )


def test_embedded_report_data_cannot_break_out_of_script_tag():
    r = report()
    r["provenance"]["mode"] = "</script><img src=x onerror=alert(1)>"
    html = render_html(r)
    assert "</script><img" not in html
    assert "\\u003c/script\\u003e" in html
