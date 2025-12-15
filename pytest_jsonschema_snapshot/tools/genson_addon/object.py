# src/jsonschema_infer/custom_object_strategy.py
from typing import Any, Dict

from genson.schema.strategies import Object

class CustomObject(Object):
    """Custom object strategy to handle empty objects and pseudo-array merging with maxProperties=0 for empty cases."""

    def __init__(self, node_class):
        super().__init__(node_class)
        self.has_empty: bool = False  # Track if empty dict {} was encountered
        self.has_non_empty: bool = False  # Track if non-empty objects were seen

    def add_object(self, obj: dict) -> None:
        super().add_object(obj)
        if not obj:  # obj == {}
            self.has_empty = True
        else:
            self.has_non_empty = True

    def add_schema(self, schema: Dict[str, Any]) -> None:
        super().add_schema(schema)
        # Detect empty indicators in schema
        if "maxProperties" in schema and schema["maxProperties"] == 0:
            self.has_empty = True
        elif "properties" in schema or "patternProperties" in schema:
            self.has_non_empty = True
        # Handle oneOf/anyOf
        if "oneOf" in schema:
            for variant in schema["oneOf"]:
                if isinstance(variant, dict):
                    if "maxProperties" in variant and variant["maxProperties"] == 0:
                        self.has_empty = True
                    else:
                        self.has_non_empty = True

    def merge(self, other: "CustomObject") -> None:
        super().merge(other)
        self.has_empty |= other.has_empty
        self.has_non_empty |= other.has_non_empty

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()

        if self.has_empty and not self.has_non_empty:
            # Only empty objects
            schema["maxProperties"] = 0
            if "minProperties" in schema:
                del schema["minProperties"]
            if "properties" in schema:
                del schema["properties"]
            if "patternProperties" in schema:
                del schema["patternProperties"]
            return schema

        if self.has_empty and self.has_non_empty:  
            non_empty_variant = {k: v for k, v in schema.items() if k != "maxProperties"}  
            if 'minProperties' not in non_empty_variant or non_empty_variant['minProperties'] <= 0:  
                # Empty is compatible; drop maxProperties variant and return non-empty  
                return non_empty_variant  
            else:  
                # Otherwise, use oneOf  
                empty_variant = {"type": "object", "maxProperties": 0}  
                schema.clear()  
                schema["oneOf"] = [non_empty_variant, empty_variant]  
                return schema

        # No changes if no empties
        return schema