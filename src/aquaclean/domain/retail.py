"""Retail contracts and pure rules. Prices and balances never come from a model."""

from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from aquaclean.domain.entities import Clock, digest
from aquaclean.domain.errors import DomainError


class RetailContract(BaseModel):
    model_config = ConfigDict(extra="forbid")


class CustomerInput(RetailContract):
    existing_id: str | None = Field(default=None, max_length=80)
    name: str | None = Field(default=None, min_length=2, max_length=120)
    contact: str | None = Field(default=None, min_length=3, max_length=160)

    @model_validator(mode="after")
    def sufficient(self):
        if not self.existing_id and not (self.name and self.contact):
            raise ValueError("Cliente nuevo requiere nombre y contacto necesario; correo opcional.")
        return self


class OrderItemInput(RetailContract):
    garment: str = Field(min_length=2, max_length=120)
    quantity: int = Field(ge=1, le=500, strict=True)
    weight_kg: Decimal | None = Field(default=None, gt=0, le=500, decimal_places=3)
    service_code: str = Field(max_length=40)
    observations: str = Field(min_length=3, max_length=1500)
    evidence_refs: list[UUID] = Field(default_factory=list, max_length=10)


class ReceptionInput(RetailContract):
    customer: CustomerInput
    received: bool = Field(strict=True)
    receipt_evidence: str = Field(min_length=8, max_length=2000)
    channel: Literal["counter", "pickup"] = "counter"
    pickup_request_id: UUID | None = None
    items: list[OrderItemInput] = Field(min_length=1, max_length=50)
    promised_at: datetime | None = None
    advance: Decimal = Field(default=Decimal("0.00"), ge=0, decimal_places=2)
    payment_evidence: str | None = Field(default=None, max_length=2000)

    @field_validator("advance", mode="before")
    @classmethod
    def no_float_advance(cls, value):
        if isinstance(value, float):
            raise ValueError("Envíe adelanto como cadena decimal, sin flotantes.")
        return value

    @model_validator(mode="after")
    def check_receipt(self):
        if self.received is not True:
            raise ValueError("La orden exige prendas efectivamente recibidas.")
        if (self.channel == "pickup") != bool(self.pickup_request_id):
            raise ValueError("Recepción desde recojo exige solicitud; mostrador no la requiere.")
        if self.advance and (not self.payment_evidence or len(self.payment_evidence) < 8):
            raise ValueError("El adelanto declarado necesita evidencia del operador.")
        if self.promised_at and self.promised_at.tzinfo is None:
            raise ValueError("Fecha prometida requiere zona horaria.")
        return self


class PickupInput(RetailContract):
    customer: CustomerInput
    address: str = Field(min_length=8, max_length=500)
    day: str
    shift: Literal["manana", "tarde"]
    declared_volume: str = Field(min_length=3, max_length=300)
    contact: str = Field(min_length=3, max_length=160)


class RetailOperation(RetailContract):
    command_id: UUID
    expected_version: int = Field(ge=1)
    action: Literal[
        "start_processing",
        "finish_processing",
        "delivery_pending",
        "deliver",
        "payment",
        "close",
        "pickup_completed",
        "confirm_delivery",
    ]
    evidence: str = Field(min_length=8, max_length=2000)
    amount: Decimal | None = Field(default=None, gt=0, decimal_places=2)
    receiver: str | None = Field(default=None, min_length=2, max_length=120)
    conformity: bool = False

    @field_validator("amount", mode="before")
    @classmethod
    def no_float_money(cls, value):
        if isinstance(value, float):
            raise ValueError("Envíe moneda como cadena decimal, sin flotantes.")
        return value


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_quote(reception: ReceptionInput, tariff: dict, clock: Clock) -> dict:
    if tariff.get("currency") != "PEN" or tariff.get("synthetic") is not True:
        raise DomainError("Tarifario de demostración PEN requerido.")
    lines, total = [], Decimal("0.00")
    for item in reception.items:
        rate = tariff["services"].get(item.service_code)
        if not rate:
            raise DomainError("Servicio ausente del tarifario configurado.")
        if not isinstance(rate["price"], str) or rate["unit"] not in {"kg", "piece"}:
            raise DomainError("Tarifa requiere precio como cadena decimal y unidad kg/piece.")
        price = Decimal(rate["price"])
        if not price.is_finite() or price <= 0:
            raise DomainError("Tarifa requiere importe positivo finito.")
        if rate["unit"] == "kg" and item.weight_kg is None:
            raise DomainError("El servicio por kilo requiere pesaje humano declarado.")
        units = item.weight_kg if rate["unit"] == "kg" else Decimal(item.quantity)
        assert units is not None
        amount = money(price * units)
        total += amount
        lines.append({"unit_price": rate["price"], "unit": rate["unit"], "amount": str(amount)})
    if reception.advance > total:
        raise DomainError("Adelanto mayor al importe calculado.")
    promised = reception.promised_at or (clock.now() + timedelta(hours=tariff["promise_hours"]))
    if promised <= clock.now():
        raise DomainError("La fecha prometida debe ser futura.")
    return {
        "tariff_version": tariff["version"],
        "tariff_hash": digest(tariff),
        "currency": "PEN",
        "synthetic": True,
        "lines": lines,
        "total": str(money(total)),
        "advance": str(money(reception.advance)),
        "balance": str(money(total - reception.advance)),
        "promised_at": promised.isoformat(),
    }


TRANSITIONS = {
    "start_processing": ({"RECEIVED"}, "IN_PROCESSING"),
    "finish_processing": ({"IN_PROCESSING"}, "QUALITY_PENDING"),
    "delivery_pending": ({"READY"}, "DELIVERY_PENDING"),
    "deliver": ({"READY", "DELIVERY_PENDING"}, "DELIVERED"),
    "close": ({"DELIVERED"}, "CLOSED"),
}


def next_status(status: str, action: str) -> str:
    allowed, target = TRANSITIONS[action]
    if status not in allowed:
        raise DomainError(f"{action} no procede desde {status}.", "invalid_phase", 409)
    return target
