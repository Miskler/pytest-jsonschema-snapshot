# src/jsonschema_infer/custom_string_strategy.py
from typing import Any, Dict, Set

from genson.schema.strategies import String
from .format.format_detector import FormatDetector

class CustomString(String):
    """Custom string strategy that fully incorporates format analysis, aggregation, and enhancement logic from FormatHandler."""

    def __init__(self, node_class):
        super().__init__(node_class)
        self.formats: Set[str] = set()
        self.has_empty: bool = False
        self.has_no_format: bool = False

    def add_object(self, obj: str) -> None:
        super().add_object(obj)
        if obj == "":
            self.has_empty = True
        else:
            format_name = FormatDetector.detect(obj, type_hint="string")
            if format_name:
                self.formats.add(format_name)
            else:
                self.has_no_format = True

    def add_schema(self, schema: Dict[str, Any]) -> None:
        super().add_schema(schema)
        # Extract and aggregate formats, empties, and no-formats from the added schema
        # Handles oneOf variants as in SchemaFormatEnhancer
        if "oneOf" in schema and isinstance(schema["oneOf"], list):
            for variant in schema["oneOf"]:
                if isinstance(variant, dict):
                    if "format" in variant:
                        self.formats.add(variant["format"])
                    elif "maxLength" in variant and variant.get("maxLength") == 0:
                        self.has_empty = True
                    # If variant has no format and not empty, consider as no_format
                    elif "format" not in variant and "maxLength" not in variant:
                        self.has_no_format = True
        elif "format" in schema:
            self.formats.add(schema["format"])
        elif "maxLength" in schema and schema.get("maxLength") == 0:
            self.has_empty = True
        elif "format" not in schema and "maxLength" not in schema:
            self.has_no_format = True

    def merge(self, other: "CustomString") -> None:
        """Merge state from another CustomString instance, aggregating formats, empties, and no-formats."""
        super().merge(other)
        self.formats.update(other.formats)
        self.has_empty |= other.has_empty
        self.has_no_format |= other.has_no_format

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        # Integrate enhancement logic from SchemaFormatEnhancer._add_string_formats
        if self.has_no_format:
            # If there are strings without format (not empty), discard formats
            if "format" in schema:
                del schema["format"]
            return schema

        if not self.formats and self.has_empty:
            # Only empty strings
            schema["maxLength"] = 0
            if "minLength" in schema:
                del schema["minLength"]
            return schema

        if len(self.formats) == 1 and not self.has_empty:
            # Single format, no empties
            schema["format"] = next(iter(self.formats))
            return schema

        # Multiple formats or mix with empties: create oneOf
        variants = [{"format": fmt} for fmt in sorted(self.formats)]
        if self.has_empty:
            variants.append({"maxLength": 0})

        # Preserve existing properties outside of format
        existing_props = {k: v for k, v in schema.items() if k != "format"}
        schema.clear()
        schema.update(existing_props)
        if len(variants) > 1:
            schema["oneOf"] = variants
        elif len(variants) == 1:
            schema.update(variants[0])

        return schema