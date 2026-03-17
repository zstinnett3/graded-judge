"""
Schema and emptiness rules for Tier 0.
"""

import json
import logging
from graded_judge.models import EvaluationInput
from graded_judge.rules.base import BaseRule

logger = logging.getLogger(__name__)


def _validate_json_schema(data: object, schema: dict) -> tuple[bool, str]:
    """Validate data against JSON Schema. Returns (valid, error_message)."""
    # Minimal JSON Schema validation: type and required keys
    if "type" in schema:
        type_ = schema["type"]
        if type_ == "object" and not isinstance(data, dict):
            return (False, f"Expected object, got {type(data).__name__}")
        if type_ == "array" and not isinstance(data, list):
            return (False, f"Expected array, got {type(data).__name__}")
        if type_ == "string" and not isinstance(data, str):
            return (False, f"Expected string, got {type(data).__name__}")
        if type_ == "number" and not isinstance(data, (int, float)):
            return (False, f"Expected number, got {type(data).__name__}")
    if "required" in schema and isinstance(data, dict):
        for key in schema["required"]:
            if key not in data:
                return (False, f"Missing required key: {key}")
    if "properties" in schema and isinstance(data, dict):
        for key, prop_schema in schema["properties"].items():
            if key in data and isinstance(prop_schema, dict):
                ok, err = _validate_json_schema(data[key], prop_schema)
                if not ok:
                    return (False, f".{key}: {err}")
    return (True, "Valid")


class JsonSchemaRule(BaseRule):
    """Fails if output is not valid JSON matching the given schema."""

    def __init__(self, schema: dict) -> None:
        self._schema = schema

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        text = input.output.strip()
        try:
            data = json.loads(text)
        except json.JSONDecodeError as e:
            return (False, f"Invalid JSON: {e}")
        ok, msg = _validate_json_schema(data, self._schema)
        if not ok:
            return (False, msg)
        return (True, "JSON matches schema")

    @property
    def name(self) -> str:
        return "JsonSchemaRule"


class NonEmptyRule(BaseRule):
    """Fails if output is empty or whitespace only."""

    def check(self, input: EvaluationInput) -> tuple[bool, str]:
        if not input.output or not input.output.strip():
            return (False, "Output is empty or whitespace only")
        return (True, "Output is non-empty")

    @property
    def name(self) -> str:
        return "NonEmptyRule"
