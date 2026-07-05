from __future__ import annotations

from app.schemas.generation import GeneratedDeckPayload


def validate_generated_deck(value: object) -> GeneratedDeckPayload:
    # Pydantic validation is the backend gate before any generated JSON is returned or persisted.
    return GeneratedDeckPayload.model_validate(value)
