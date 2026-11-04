import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from aquaclean.domain.errors import DomainError

ORG = "org_demo_aquaclean"
POLICY = "pilot-1"


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, default=str, ensure_ascii=False).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Actor:
    id: str
    organization_id: str
    roles: frozenset[str]
    client_id: str | None = None

    def require(self, role: str) -> None:
        if role not in self.roles:
            raise DomainError("El actor no tiene esa capacidad.", "forbidden", 403)

    def scope(self, organization_id: str, client_id: str | None = None) -> None:
        if organization_id != self.organization_id or (
            self.client_id and client_id != self.client_id
        ):
            raise DomainError("Recurso no disponible en este contexto.", "not_found", 404)


DEMO_ACTOR = Actor("demo_operator", ORG, frozenset({"attention", "logistics", "quality", "admin"}))


class Clock(Protocol):
    def now(self) -> datetime: ...


class LimaClock:
    def now(self) -> datetime:
        return datetime.now(ZoneInfo("America/Lima"))
