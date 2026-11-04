from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from aquaclean.domain.errors import DomainError
from aquaclean.domain.retail import ReceptionInput, RetailOperation, calculate_quote
from tests.integration.test_retail import reception


def test_quote_is_decimal_versioned_and_requires_declared_weight(clock):
    import json
    from types import SimpleNamespace

    data = reception(SimpleNamespace())
    data["items"][0].update(service_code="wash_kg", weight_kg="1.235")
    tariff = json.loads(Path("config/retail-tariffs-v2.json").read_text())
    quote = calculate_quote(ReceptionInput.model_validate(data), tariff, clock)
    assert quote["total"] == "10.50"  # 1.235 * 8.50, ROUND_HALF_UP
    assert Decimal(quote["balance"]) == Decimal("5.50")
    assert quote["tariff_version"] == "synthetic-retail-2.0" and quote["tariff_hash"]
    del data["items"][0]["weight_kg"]
    with pytest.raises(DomainError, match="pesaje humano"):
        calculate_quote(ReceptionInput.model_validate(data), tariff, clock)


def test_monetary_float_is_rejected_and_no_physical_receipt_cannot_open_order():
    from uuid import uuid4

    with pytest.raises(ValidationError):
        RetailOperation(
            command_id=uuid4(),
            expected_version=1,
            action="payment",
            amount=0.1,
            evidence="Declaración sintética",
        )
    from types import SimpleNamespace

    data = reception(SimpleNamespace())
    data["advance"] = 0.1
    with pytest.raises(ValidationError):
        ReceptionInput.model_validate(data)
    data["advance"] = "0.00"
    data["received"] = False
    with pytest.raises(ValidationError):
        ReceptionInput.model_validate(data)
