import io
from datetime import timedelta
from pathlib import Path
from uuid import uuid4

import httpx
import pytest
from PIL import Image
from pypdf import PdfWriter

from aquaclean.domain.entities import ORG
from aquaclean.domain.errors import DomainError
from aquaclean.infrastructure.media.validation import validate
from aquaclean.interfaces.api.app import app
from tests.helpers import approve, fields, stage


@pytest.fixture
def png():
    output = io.BytesIO()
    Image.new("RGB", (20, 20), "white").save(output, format="PNG")
    return output.getvalue()


@pytest.mark.parametrize(
    "filename,content",
    [
        ("fake.png", b"not an image"),
        ("fake.pdf", b"%PDF-invalid"),
        ("fake.mp3", b"bad"),
        ("fake.wav", b"RIFFbad"),
        ("fake.exe", b"executable"),
    ],
)
def test_M02_invalid_files(filename, content):
    from aquaclean.config import Settings

    with pytest.raises(DomainError):
        validate(content, filename, Settings())


async def test_M02_size_and_page_limits(rt):
    with pytest.raises(DomainError):
        validate(b"x" * (rt.settings.max_upload_mb * 1024 * 1024 + 1), "large.png", rt.settings)
    writer = PdfWriter()
    for _ in range(rt.settings.max_pdf_pages + 1):
        writer.add_blank_page(width=100, height=100)
    output = io.BytesIO()
    writer.write(output)
    with pytest.raises(DomainError):
        validate(output.getvalue(), "large.pdf", rt.settings)


async def test_M02_attachment_scope_and_magic(rt, case, png):
    saved = await rt.media.save(rt.actor, str(case["id"]), "../../test.png", png)
    assert saved["filename"] == "test.png"
    assert rt.media.path(saved).name == str(saved["id"])
    with pytest.raises(DomainError):
        await rt.media.save(rt.actor, str(case["id"]), "mismatch.jpg", png)
    foreign = await rt.repo.create_case(rt.actor, "Otro caso", "CLI-0001")
    with pytest.raises(DomainError):
        await rt.media.get(rt.actor, str(foreign["id"]), str(saved["id"]))


async def test_M03_idempotent_ingestion_and_dimensions(rt):
    before = await rt.repo.db.one(
        "SELECT count(*) n FROM app.chunks WHERE collection_id=%s", (rt.knowledge.collection,)
    )
    result = await rt.knowledge.ingest_demo()
    after = await rt.repo.db.one(
        "SELECT count(*) n FROM app.chunks WHERE collection_id=%s", (rt.knowledge.collection,)
    )
    assert before == after and result["written"] == 0
    rows = await rt.repo.db.all(
        "SELECT DISTINCT vector_dims(embedding) d FROM app.chunks WHERE collection_id=%s",
        (rt.knowledge.collection,),
    )
    assert rows == [{"d": 768}]
    import psycopg

    with pytest.raises(psycopg.Error):
        await rt.repo.db.execute(
            "UPDATE app.collections SET dimension=42 WHERE id=%s", (rt.knowledge.collection,)
        )


async def test_M04_organization_client_role_and_validity_filters(rt):
    docs = [
        ("alien-org", "other-org", None, ["attention"], False),
        ("alien-client", ORG, "CLI-0002", ["attention"], False),
        ("alien-role", ORG, None, ["unavailable-role"], False),
        ("expired", ORG, None, ["attention"], True),
    ]
    for label, org, client, roles, expired in docs:
        did = "TEST-" + label + "-" + str(uuid4())
        await rt.repo.db.execute(
            "INSERT INTO app.documents(id,organization_id,client_id,roles,title,version,hash,approved,valid_from,valid_until) VALUES(%s,%s,%s,%s,%s,'test','hash',true,%s,%s)",
            (
                did,
                org,
                client,
                roles,
                label,
                rt.clock.now() - timedelta(days=30),
                rt.clock.now() - timedelta(days=1) if expired else None,
            ),
        )
        vector = (await rt.knowledge.embeddings.embed(["calidad"], "RETRIEVAL_DOCUMENT"))[0]
        await rt.repo.db.execute(
            "INSERT INTO app.chunks(id,document_id,collection_id,section,content,hash,embedding) VALUES(%s,%s,%s,'1','calidad','hash',%s::vector)",
            (did, did, rt.knowledge.collection, str(vector)),
        )
    sources = await rt.knowledge.search(rt.actor, "calidad", "CLI-0001")
    assert sources and not any(s["title"] in {d[0] for d in docs} for s in sources)


async def test_U01_U09_api_actor_fixed_and_no_static_fallback(rt):
    app.state.runtime = rt
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/api/session", headers={"X-Role": "admin", "X-Organization": "foreign"}
        )
        assert response.json()["actor"]["id"] == "demo_operator"
        assert response.json()["actor"]["organization_id"] == ORG
        assert (await client.get("/api/nonexistent")).status_code == 404
        assert (
            await client.post("/api/cases", json={"title": "x", "role": "admin"})
        ).status_code == 422
        assert (
            await client.post(
                "/api/cases", json={"title": "x"}, headers={"Origin": "https://attacker.invalid"}
            )
        ).status_code == 403
        assert (
            await client.get("/api/session", headers={"Host": "attacker.invalid"})
        ).status_code == 400


async def test_U03_U05_sse_replay_is_read_only(rt, case):
    rid = str(uuid4())
    await rt.repo.enqueue(rt.actor, str(case["id"]), rid, {"text": "fixture"})
    await rt.repo.event(
        rid, str(case["id"]), "agent.started", {"agent": "fixture", "status": "started"}
    )
    await rt.repo.db.execute("UPDATE app.runs SET status='completed' WHERE id=%s", (rid,))
    app.state.runtime = rt
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        first = await client.get(f"/api/runs/{rid}/events")
        second = await client.get(f"/api/runs/{rid}/events")
        assert first.text == second.text and "agent.started" in first.text
        sequence = (
            await rt.repo.db.one("SELECT sequence FROM app.events WHERE run_id=%s", (rid,))
        )["sequence"]
        resumed = await client.get(
            f"/api/runs/{rid}/events", headers={"Last-Event-ID": str(sequence)}
        )
        assert "agent.started" not in resumed.text
    assert not (await rt.repo.snapshot(rt.actor, str(case["id"])))["orders"]


async def test_U07_approval_double_click(rt, case):
    a = await stage(rt, case["id"], {"action": "register", "fields": fields(rt)})
    decision_id, decision = await approve(rt, case["id"], a)
    replay = await rt.repo.resolve_approval(
        rt.actor, str(case["id"]), str(a["id"]), decision_id, decision
    )
    assert str(replay["decision_id"]) == decision_id
    with pytest.raises(DomainError):
        await approve(rt, case["id"], a)


async def test_U07_approval_and_resume_job_are_atomic(rt, case):
    cid, initial_run = str(case["id"]), str(uuid4())
    await rt.repo.enqueue(rt.actor, cid, initial_run, {"text": "Initial analysis fixture"})
    a = await stage(rt, cid, {"action": "register", "fields": fields(rt)})
    decision_id = str(uuid4())
    payload = {
        "decision_id": decision_id,
        "action": "approve",
        "proposal_hash": a["proposal_hash"],
        "case_version": a["case_version"],
        "selection": {},
    }
    app.state.runtime = rt
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        url = f"/api/cases/{cid}/approvals/{a['id']}"
        busy = await client.post(url, json=payload)
        assert busy.status_code == 409 and busy.json()["code"] == "run_active"
        pending = await rt.repo.db.one("SELECT * FROM app.approvals WHERE id=%s", (a["id"],))
        assert pending["status"] == "pending" and pending["decision_id"] is None
        assert not await rt.repo.db.one("SELECT id FROM app.runs WHERE id=%s", (decision_id,))

        await rt.repo.db.execute("UPDATE app.runs SET status='paused' WHERE id=%s", (initial_run,))
        accepted = await client.post(url, json=payload)
        assert accepted.status_code == 202 and accepted.json()["id"] == decision_id
        replay = await client.post(url, json=payload)
        assert replay.status_code == 202 and replay.json()["id"] == decision_id

    resolved = await rt.repo.db.one("SELECT * FROM app.approvals WHERE id=%s", (a["id"],))
    assert resolved["status"] == "approved" and str(resolved["decision_id"]) == decision_id
    events = await rt.repo.db.all(
        "SELECT * FROM app.events WHERE run_id=%s AND type='approval.resolved'", (decision_id,)
    )
    assert len(events) == 1


async def test_U06_public_events_no_private_fields(rt, case):
    from tests.integration.test_graphs import start

    snapshot = await start(rt, case["id"])
    for event in snapshot["events"]:
        assert (
            not {"system_prompt", "api_key", "reasoning", "chain_of_thought", "thoughts"}
            & event["payload"].keys()
        )


async def test_M01_fixture_media_validation(rt):
    for filename in [
        "guia-demo.png",
        "guia-demo.jpg",
        "guia-demo.webp",
        "guia-demo.pdf",
        "nota-demo.wav",
        "nota-demo.mp3",
    ]:
        path = Path("tests/fixtures") / filename
        if not path.exists():
            pytest.skip("Generar fixtures con scripts/create_demo_media.py --with-audio")
        assert validate(path.read_bytes(), filename, rt.settings)["mime"]
