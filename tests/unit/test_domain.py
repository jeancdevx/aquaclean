from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from aquaclean.agents.schemas import RequestDraft
from aquaclean.domain.entities import Actor, digest
from aquaclean.domain.errors import DomainError
from aquaclean.domain.policies import (
    validate_action,
    validate_fulfillment,
    validate_request,
)


def valid(clock):
    return dict(
        cliente_id="CLI-0001",
        solicitante="Demo sintético",
        correo="demo@example.invalid",
        fecha_recojo=str(clock.now().date()),
        turno="manana",
        tipo_ropa="mixto",
        bolsas=2,
    )


def test_A01_lima_midnight(clock):
    instant = datetime(2026, 10, 17, 1, 0, tzinfo=UTC)
    assert instant.astimezone(ZoneInfo("America/Lima")).date().isoformat() == "2026-10-16"
    assert validate_request(valid(clock), clock)["fecha_recojo"] == "2026-10-16"


@pytest.mark.parametrize(
    "key,value",
    [
        ("correo", "bad"),
        ("bolsas", True),
        ("bolsas", 41),
        ("fecha_recojo", "2026-12-01"),
        ("fecha_recojo", "mañana"),
        ("turno", "noche"),
        ("tipo_ropa", "desconocido"),
    ],
)
def test_A02_invalid_fields(clock, key, value):
    data = valid(clock)
    data[key] = value
    with pytest.raises(DomainError):
        validate_request(data, clock)


def test_A02_missing_fields(clock):
    data = valid(clock)
    del data["bolsas"]
    with pytest.raises(DomainError, match="bolsas"):
        validate_request(data, clock)


def test_A09_no_silent_conformity():
    with pytest.raises(DomainError):
        validate_fulfillment("P4", [{"kind": "silence"}])


def test_A12_role_and_action_boundaries():
    with pytest.raises(DomainError):
        Actor("client", "org", frozenset({"attention"})).require("admin")
    for process, action in [
        ("P3", "register"),
        ("P1", "release"),
        ("P2", "close_incident"),
        ("P4", "cancel"),
    ]:
        with pytest.raises(DomainError):
            validate_action(process, action)


def test_A12_contract_rejects_role_injection():
    with pytest.raises(ValidationError):
        RequestDraft.model_validate(
            {
                "role": "admin",
                "organization_id": "another",
                "action": "register",
                "response": "x",
                "rationale_summary": "x",
                "fields": {},
            }
        )


def test_hash_is_order_invariant():
    assert digest({"a": 1, "b": 2}) == digest({"b": 2, "a": 1})
