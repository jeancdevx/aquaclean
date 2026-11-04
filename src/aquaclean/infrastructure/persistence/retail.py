"""Retail reception and reads; all business writes require an existing transaction."""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid5

from aquaclean.domain.errors import DomainError
from aquaclean.domain.retail import PickupInput, ReceptionInput, calculate_quote
from aquaclean.infrastructure.persistence.database import jsonb


class RetailRepository:
    def __init__(self, db, clock, tariff_path=Path("config/retail-tariffs-v2.json")):
        self.db, self.clock, self.tariff_path = db, clock, tariff_path

    def tariff(self):
        return json.loads(self.tariff_path.read_text())

    async def prepare(self, actor, case, proposal):
        actor.require("attention")
        action = proposal["action"]
        model = ReceptionInput if action == "receive" else PickupInput
        key = "reception" if action == "receive" else "pickup"
        data = model.model_validate(proposal[key])
        customer = data.customer
        if case["client_id"] and customer.existing_id != case["client_id"]:
            raise DomainError("Cliente distinto del caso.", "forbidden", 403)
        if customer.existing_id:
            row = await self.db.one(
                "SELECT * FROM app.customers WHERE organization_id=%s AND id=%s",
                (actor.organization_id, customer.existing_id),
            )
            if not row:
                raise DomainError("Cliente no disponible.", "not_found", 404)
            actor.scope(row["organization_id"], row["id"])
            if row["blocked"]:
                raise DomainError(
                    "Cliente bloqueado: requiere gestión comercial fuera de esta recepción.",
                    "blocked_customer",
                    409,
                )
        elif actor.client_id:
            raise DomainError("Este alcance no permite registrar otros clientes.", "forbidden", 403)
        if case["order_id"] or (action == "request_pickup" and case["pickup_request_id"]):
            raise DomainError("Este caso ya tiene el registro solicitado.", "existing_order", 409)
        if action == "receive":
            quote = calculate_quote(data, self.tariff(), self.clock)
            data = data.model_copy(
                update={
                    "promised_at": __import__("datetime").datetime.fromisoformat(
                        quote["promised_at"]
                    )
                }
            )
            for item in data.items:
                for ref in item.evidence_refs:
                    if not await self.db.one(
                        "SELECT id FROM app.attachments WHERE id=%s AND case_id=%s",
                        (ref, case["id"]),
                    ):
                        raise DomainError("Evidencia de recepción ajena al caso.", "forbidden", 403)
            if data.pickup_request_id:
                pickup = await self.pickup(actor, str(data.pickup_request_id))
                if pickup["status"] != "PICKED_UP" or pickup["client_id"] != customer.existing_id:
                    raise DomainError(
                        "Falta recojo humano o cliente coincidente.", "invalid_phase", 409
                    )
            proposal["quote"] = quote
        else:
            try:
                day = date.fromisoformat(data.day)
            except ValueError as exc:
                raise DomainError("Fecha de recojo debe ser AAAA-MM-DD.") from exc
            if not self.clock.now().date() <= day <= self.clock.now().date() + timedelta(days=30):
                raise DomainError("Recojo fuera de ventana de laboratorio de 30 días.")
        proposal[key] = data.model_dump(mode="json", exclude_none=True)
        proposal["missing_fields"] = []
        return proposal

    async def pickup(self, actor, pickup_id):
        actor.require("logistics")
        row = await self.db.one(
            "SELECT * FROM app.pickup_requests WHERE id=%s AND organization_id=%s",
            (pickup_id, actor.organization_id),
        )
        if not row:
            raise DomainError("Solicitud no disponible.", "not_found", 404)
        actor.scope(row["organization_id"], row["client_id"])
        return row

    async def snapshot(self, actor, case):
        if not case["order_id"]:
            return {
                "pickup_request": await self.db.one(
                    "SELECT * FROM app.pickup_requests WHERE id=%s", (case["pickup_request_id"],)
                ),
                "items": [],
                "payments": [],
                "receipts": [],
                "balance": None,
                "delivery": None,
            }
        oid = case["order_id"]
        order = await self.db.one("SELECT * FROM app.orders WHERE id=%s", (oid,))
        actor.scope(order["organization_id"], order["client_id"])
        payments = await self.db.all(
            "SELECT * FROM app.payment_records WHERE order_id=%s ORDER BY declared_at,id", (oid,)
        )
        return {
            "pickup_request": None,
            "items": await self.db.all(
                "SELECT * FROM app.order_items WHERE order_id=%s ORDER BY position", (oid,)
            ),
            "payments": payments,
            "receipts": await self.db.all(
                "SELECT * FROM app.demo_receipts WHERE order_id=%s ORDER BY created_at", (oid,)
            ),
            "balance": str(order["total"] - sum((p["amount"] for p in payments), Decimal("0.00")))
            if order["total"] is not None
            else None,
            "delivery": await self.db.one(
                "SELECT * FROM app.delivery_evidence WHERE order_id=%s", (oid,)
            ),
            "incidents": await self.db.all(
                "SELECT id,status,parent_case_id FROM app.cases WHERE order_id=%s AND process='P4' ORDER BY created_at",
                (oid,),
            ),
        }

    async def execute_attention(self, conn, actor, case, proposal, approval, command_id):
        actor.require("attention")
        if approval["kind"] != "confirmation":
            raise DomainError(
                "Se requiere confirmación de recepción o recojo.", "confirmation_required", 409
            )
        # Revalidate tariff, evidence, scope and phase immediately before the effect.
        checked = await self.prepare(actor, case, dict(proposal))
        if checked != proposal:
            raise DomainError(
                "Cotización o recepción cambió; confirme otra vez.", "stale_quote", 409
            )
        key = "reception" if proposal["action"] == "receive" else "pickup"
        data = proposal[key]
        customer = data["customer"]
        client_id = customer.get("existing_id")
        if client_id:
            current = await (
                await conn.execute(
                    "SELECT * FROM app.customers WHERE organization_id=%s AND id=%s FOR SHARE",
                    (actor.organization_id, client_id),
                )
            ).fetchone()
            if not current or current["blocked"]:
                raise DomainError("Cliente no habilitado.", "blocked_customer", 409)
        else:
            client_id = "CUS-" + uuid5(UUID(str(case["id"])), "customer").hex[:12].upper()
            await conn.execute(
                "INSERT INTO app.customers(organization_id,id,name,email,contact,address) VALUES(%s,%s,%s,NULL,%s,'')",
                (actor.organization_id, client_id, customer["name"], customer["contact"]),
            )
        actor.scope(actor.organization_id, client_id)
        if key == "pickup":
            pid = str(uuid5(UUID(str(case["id"])), "pickup-request"))
            await conn.execute(
                "INSERT INTO app.pickup_requests(id,organization_id,client_id,request_id,fields) VALUES(%s,%s,%s,%s,%s)",
                (pid, actor.organization_id, client_id, case["id"], jsonb(data)),
            )
            await conn.execute(
                "UPDATE app.cases SET pickup_request_id=%s,pickup_version=1,client_id=%s WHERE id=%s",
                (pid, client_id, case["id"]),
            )
            return {
                "status": "pickup_requested",
                "pickup_request_id": pid,
                "customer_id": client_id,
            }
        oid = str(uuid5(UUID(str(case["id"])), "service-order"))
        number, quote = "DET-" + UUID(oid).hex[:10].upper(), proposal["quote"]
        if data.get("pickup_request_id"):
            pickup = await (
                await conn.execute(
                    "SELECT * FROM app.pickup_requests WHERE id=%s FOR UPDATE",
                    (data["pickup_request_id"],),
                )
            ).fetchone()
            if not pickup or pickup["status"] != "PICKED_UP":
                raise DomainError("Recojo no disponible para recepción.", "invalid_phase", 409)
        await conn.execute(
            "INSERT INTO app.orders(id,organization_id,client_id,request_id,number,fields,status,kind,received_at,promised_at,currency,total,quote,pickup_request_id) VALUES(%s,%s,%s,%s,%s,%s,'RECEIVED','retail_v2',%s,%s,'PEN',%s,%s,%s)",
            (
                oid,
                actor.organization_id,
                client_id,
                case["id"],
                number,
                jsonb(data),
                self.clock.now(),
                quote["promised_at"],
                quote["total"],
                jsonb(quote),
                data.get("pickup_request_id"),
            ),
        )
        for index, (item, price) in enumerate(zip(data["items"], quote["lines"], strict=True)):
            await conn.execute(
                "INSERT INTO app.order_items(id,order_id,position,garment,quantity,weight_kg,service_code,observations,evidence_refs,unit_price,amount) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                (
                    str(uuid5(UUID(oid), str(index))),
                    oid,
                    index + 1,
                    item["garment"],
                    item["quantity"],
                    item.get("weight_kg"),
                    item["service_code"],
                    item["observations"],
                    jsonb(item["evidence_refs"]),
                    price["unit_price"],
                    price["amount"],
                ),
            )
        if Decimal(quote["advance"]):
            await conn.execute(
                "INSERT INTO app.payment_records VALUES(%s,%s,%s,'advance',%s,%s,%s)",
                (
                    str(uuid5(UUID(command_id), "advance")),
                    oid,
                    quote["advance"],
                    data["payment_evidence"],
                    actor.id,
                    self.clock.now(),
                ),
            )
        receipt = {
            "label": "DEMOSTRACIÓN · SIN VALIDEZ FISCAL · COBRO DECLARADO",
            "number": number,
            "quote": quote,
            "bank_payment_executed": False,
        }
        await conn.execute(
            "INSERT INTO app.demo_receipts(id,order_id,kind,payload) VALUES(%s,%s,'reception',%s)",
            (str(uuid5(UUID(oid), "receipt-reception")), oid, jsonb(receipt)),
        )
        await conn.execute(
            "UPDATE app.cases SET order_id=%s,order_version=1,client_id=%s WHERE id=%s",
            (oid, client_id, case["id"]),
        )
        if data.get("pickup_request_id"):
            await conn.execute(
                "UPDATE app.pickup_requests SET status='RECEIVED',version=version+1 WHERE id=%s",
                (data["pickup_request_id"],),
            )
        return {
            "status": "RECEIVED",
            "order_id": oid,
            "number": number,
            "customer_id": client_id,
            "quote": quote,
            "version": 1,
        }
