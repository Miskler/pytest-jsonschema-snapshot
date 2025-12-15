from typing import Any, Dict, Set

from genson.schema.strategies import String
from .format.format_detector import FormatDetector

class CustomString(String):
    """Custom string strategy that incorporates format detection and merging per specified rules."""

    jsonschema_type = 'string'

    @classmethod
    def match_schema(cls, schema):
        return schema.get('type') == cls.jsonschema_type  # Переопределение для совместимости с 'format'

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
        if "oneOf" in schema and isinstance(schema["oneOf"], list):
            for variant in schema["oneOf"]:
                if isinstance(variant, dict):
                    if "format" in variant:
                        self.formats.add(variant["format"])
                    elif "maxLength" in variant and variant.get("maxLength") == 0:
                        self.has_empty = True
                    elif "format" not in variant and "maxLength" not in variant:
                        self.has_no_format = True
        elif "format" in schema:
            self.formats.add(schema["format"])
        elif "maxLength" in schema and schema.get("maxLength") == 0:
            self.has_empty = True
        elif "format" not in schema and "maxLength" not in schema:
            self.has_no_format = True

    def to_schema(self) -> Dict[str, Any]:
        schema = super().to_schema()
        if self.has_no_format:
            return schema
        if not self.formats and self.has_empty:
            schema["maxLength"] = 0
            if "minLength" in schema:
                del schema["minLength"]
            return schema
        if len(self.formats) == 1 and not self.has_empty:
            schema["format"] = next(iter(self.formats))
            return schema
        variants = [{"format": fmt} for fmt in sorted(self.formats)]
        if self.has_empty:
            variants.append({"maxLength": 0})
        existing_props = {k: v for k, v in schema.items() if k != "format"}
        schema.clear()
        schema.update(existing_props)
        schema["oneOf"] = variants
        return schema