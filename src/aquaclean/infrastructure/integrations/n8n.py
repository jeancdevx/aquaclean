"""Explicit V1/n8n boundary. No webhook dispatch, Sheets write or second authority."""

from aquaclean.domain.policies import validate_request
from aquaclean.domain.retail import PickupInput


def legacy_request(fields, clock, max_bags=40, max_pickup_days=30):
    """Validate the retained corporate seven-field payload, labelled legacy_v1."""
    return validate_request(fields, clock, max_bags, max_pickup_days)


def to_pickup_request(fields, clock):
    """Translate a verified legacy payload to a P1R proposal, never a ServiceOrder."""
    value = legacy_request(fields, clock)
    return PickupInput(
        customer={"existing_id": value["cliente_id"]},
        address=value.get("direccion_recojo", ""),
        day=value["fecha_recojo"],
        shift=value["turno"],
        declared_volume=f"{value['bolsas']} bolsas de {value['tipo_ropa']} declaradas",
        contact=f"{value['solicitante']} · {value['correo']}",
    )
