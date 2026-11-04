"""Gemini wire schema. Full Pydantic/domain constraints are revalidated locally."""


def wire_schema(schema: type) -> dict:
    # Gemini rejects some large bounded-array/optional-field grammar combinations.
    # Decimal is a JSON string in serialization mode; no money is decoded as float.
    # Remove generation-only bounds, never required/enum/type/extra-field rules.
    constraints = {
        "maxItems",
        "minItems",
        "maxLength",
        "minLength",
        "pattern",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "default",
    }

    def simplify(value):
        if isinstance(value, dict):
            return {k: simplify(v) for k, v in value.items() if k not in constraints}
        if isinstance(value, list):
            return [simplify(v) for v in value]
        return value

    return simplify(schema.model_json_schema(mode="serialization"))
