# src/jsonschema_infer/to_schema_converter.py
from typing import Any, Dict

from .pseudo_arrays import PseudoArrayConverter  # Assuming this is the file name for the provided code
from genson import SchemaBuilder

class JsonToSchemaConverter(SchemaBuilder):
    """Main converter combining pseudo-array functionality with integrated format handling in custom string strategy."""

    def __init__(self, *, format_mode: str = "on") -> None:
        """
        Initialization of the converter.

        Args:
            format_mode: Mode for formats ("on", "off", "safe").
        """
        self.format_mode = format_mode
        self._pseudo_array_converter = PseudoArrayConverter()

    def add_object(self, obj: Any) -> None:
        """
        Adds an object for analysis.

        Args:
            obj: JSON object for analysis.
        """
        # Only add to pseudo-array converter (it handles addition internally with now-custom node strategies)
        self._pseudo_array_converter.add_object(obj)

    def add_schema(self, schema: Dict[str, Any]) -> None:
        """
        Adds a schema for merging.

        Args:
            schema: JSON schema to merge.
        """
        # Redirect to pseudo-array converter to ensure consistent merging with pseudo-array and format handling
        self._pseudo_array_converter.add_schema(schema)

    def to_schema(self) -> dict[str, Any]:
        """
        Generates JSON Schema considering pseudo-arrays and integrated formats.

        Returns:
            Dictionary with JSON Schema.
        """
        # Get schema from pseudo converter (with custom strategies applied via updated NODE_CLASS)
        schema = self._pseudo_array_converter.to_schema()

        # Handle format_mode
        if self.format_mode == "off":
            self._strip_formats(schema)
        elif self.format_mode == "safe":
            schema.setdefault(
                "$vocabulary",
                {
                    "https://json-schema.org/draft/2020-12/vocab/core": True,
                    "https://json-schema.org/draft/2020-12/vocab/applicator": True,
                    "https://json-schema.org/draft/2020-12/vocab/format-annotation": True,
                    "https://json-schema.org/draft/2020-12/vocab/format-assertion": False,
                },
            )

        return schema
