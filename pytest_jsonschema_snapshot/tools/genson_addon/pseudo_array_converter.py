from __future__ import annotations

import re
from typing import Any, Dict, List

from genson import SchemaBuilder  # type: ignore[import-untyped]


class PseudoArrayConverter(SchemaBuilder):
    """
    A specialized SchemaBuilder extension for converting pseudo-array objects
    (dictionaries with sequential numeric string keys) into proper JSON Schema
    representations using patternProperties.
    """

    def __init__(
        self,
        schema_uri: str = "https://json-schema.org/draft/2020-12/schema",
    ) -> None:
        super().__init__()#schema_uri=schema_uri or None)
        # path → raw object (for pseudo-array analysis)
        self._raw_at_path: Dict[str, Any] = {}

    # ------------------------------------------------------------------ #
    # Collection of raw data during object addition
    # ------------------------------------------------------------------ #
    def add_object(self, obj: Any) -> None:
        self._collect_raw(obj, "#")
        super().add_object(obj)

    def _collect_raw(self, obj: Any, path: str) -> None:
        self._raw_at_path[path] = obj

        if isinstance(obj, dict):
            for k, v in obj.items():
                self._collect_raw(v, f"{path}/{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                self._collect_raw(v, f"{path}/{i}")

    # ------------------------------------------------------------------ #
    # Schema generation with pseudo-array conversion
    # ------------------------------------------------------------------ #
    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        self._convert_pseudo_arrays(schema, "#")
        return schema

    # ------------------------------------------------------------------ #
    # Pseudo-array conversion logic
    # ------------------------------------------------------------------ #
    def _convert_pseudo_arrays(self, node: Dict[str, Any], path: str) -> None:
        if not (node.get("type") == "object" and "properties" in node):
            self._recurse(node, self._convert_pseudo_arrays, path)
            return

        raw = self._raw_at_path.get(path)
        if not isinstance(raw, dict):
            self._recurse(node, self._convert_pseudo_arrays, path)
            return

        keys = list(raw.keys())
        if not keys:
            return

        if all(re.fullmatch(r"\d+", k) for k in keys):
            int_keys = {int(k) for k in keys}
            min_k, max_k = min(int_keys), max(int_keys)
            expected = set(range(min_k, max_k + 1))

            # Consider it a pseudo-array if gaps are no more than 50%
            if len(int_keys) >= 3 and len(expected - int_keys) / len(expected) <= 0.5:
                merged_item_schema = self._merge_object_schemas([
                    subschema for name, subschema in node["properties"].items()
                    if re.fullmatch(r"\d+", name)
                ])

                node.clear()
                node.update({
                    "type": "object",
                    "propertyNames": {"pattern": "^[0-9]+$"},
                    "patternProperties": {
                        "^[0-9]+$": merged_item_schema
                    },
                    "additionalProperties": False
                })
                return

        self._recurse(node, self._convert_pseudo_arrays, path)

    def _merge_object_schemas(self, schemas: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not schemas:
            return {"type": "object"}
        result = {"type": "object", "properties": {}, "required": []}
        for sch in schemas:
            result["properties"].update(sch.get("properties", {}))
            if "required" in sch:
                result["required"].extend(sch["required"])
        result["required"] = list(dict.fromkeys(result["required"]))  # Ensure uniqueness
        result["additionalProperties"] = False
        return result

    # ------------------------------------------------------------------ #
    # Recursion helper
    # ------------------------------------------------------------------ #
    def _recurse(self, node: Dict[str, Any], func: callable, path: str) -> None:
        if node.get("type") == "object" and "properties" in node:
            for k, sub in node["properties"].items():
                func(sub, f"{path}/{k}")

        if node.get("type") == "array":
            items = node.get("items", {})
            if isinstance(items, dict):
                func(items, f"{path}/0")
            elif isinstance(items, list):
                for i, sub in enumerate(items):
                    func(sub, f"{path}/{i}")

        if "anyOf" in node:
            for sub in node["anyOf"]:
                func(sub, path)