# src/jsonschema_infer/to_schema_converter.py
from .pseudo_array_converter import PseudoArrayConverter
from .format import FormatConverter
from typing import Any


class JsonToSchemaConverter:
    """Главный конвертер, объединяющий функциональность псевдо-массивов и форматов."""
    
    def __init__(self, *, format_mode: str = "on") -> None:
        """
        Инициализация конвертера.
        
        Args:
            format_mode: Режим работы с форматами ("on", "off", "safe")
        """
        self._pseudo_array_converter = PseudoArrayConverter()
        self._format_converter = FormatConverter(format_mode=format_mode)
    
    def add_object(self, obj: Any) -> None:
        """
        Добавляет объект для анализа.
        
        Args:
            obj: Объект JSON для анализа
        """
        # Собираем информацию о форматах
        self._format_converter.add_object(obj)
        # Добавляем объект в псевдо-массив конвертер
        self._pseudo_array_converter.add_object(obj)
    
    def to_schema(self) -> dict[str, Any]:
        """
        Генерирует JSON Schema с учетом псевдо-массивов и форматов.
        
        Returns:
            Словарь с JSON Schema
        """
        # 1. Получаем схему с преобразованными псевдо-массивами
        schema = self._pseudo_array_converter.to_schema()
        
        # 2. Обогащаем схему форматами
        schema = self._format_converter.to_schema(schema)
        
        return schema