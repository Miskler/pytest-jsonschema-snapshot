import re
from typing import Optional, Any


class FormatDetector:
    """Глобальный детектор форматов. Расширяем — просто добавляем в _registry."""

    _registry = {
        "string": {
            re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"): "email",
            re.compile(
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
                re.I,
            ): "uuid",
            re.compile(r"^\d{4}-\d{2}-\d{2}$"): "date",
            re.compile(
                r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$"
            ): "date-time",
            re.compile(r"^https?://[^\s/$.?#].[^\s]*$", re.I): "uri",
            re.compile(
                r"^(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}"
                r"(?:25[0-5]|2[0-4]\d|[01]?\d\d?)$"
            ): "ipv4",
        }
    }

    @classmethod
    def detect(cls, value: Any, type_hint: str = "string") -> Optional[str]:
        patterns = cls._registry.get(type_hint, {})
        for pattern, name in patterns.items():
            if pattern.fullmatch(str(value)):
                return name
        return None
