from __future__ import annotations

from typing import Any, Dict, List, Set
from genson import SchemaBuilder
from .orchestrator import KeyPatternOrchestrator


class PseudoArrayConverter(SchemaBuilder):
    """
    Исправленный конвертер без утечек памяти.
    """
    
    MAX_DEPTH = 1000  # Ограничение глубины рекурсии

    def __init__(
        self,
        schema_uri: str = "https://json-schema.org/draft/2020-12/schema",
    ) -> None:
        super().__init__()
        # Храним ТОЛЬКО ключи по путям (никаких значений!)
        self._path_keys: Dict[str, Set[str]] = {}
        # Храним объекты псевдо-массивов по путям
        self._pseudo_arrays: Dict[str, List[Dict[str, Any]]] = {}
        self._key_pattern_orchestrator = KeyPatternOrchestrator()

    def add_object(self, obj: Any) -> None:
        """Добавляет объект для анализа."""
        # Собираем информацию о псевдо-массивах
        self._collect_pseudo_arrays(obj, "#")
        # Затем передаем в родительский класс
        super().add_object(obj)

    def _collect_pseudo_arrays(self, obj: Any, path: str, depth: int = 0) -> None:
        """
        Собирает псевдо-массивы для последующей обработки.
        """
        if depth > self.MAX_DEPTH:
            return
            
        if isinstance(obj, dict):
            # Собираем ключи для этого пути
            if path not in self._path_keys:
                self._path_keys[path] = set()
            self._path_keys[path].update(obj.keys())
            
            # Проверяем, является ли словарь псевдо-массивом
            if len(obj) >= 3:
                pattern_info = self._key_pattern_orchestrator.detect_pattern(set(obj.keys()))
                if pattern_info:
                    # Сохраняем словарь как псевдо-массив
                    if path not in self._pseudo_arrays:
                        self._pseudo_arrays[path] = []
                    self._pseudo_arrays[path].append(obj)
                    # Не углубляемся дальше в этот словарь
                    return
            
            # Рекурсивно обходим вложенные объекты
            for key, value in obj.items():
                self._collect_pseudo_arrays(value, f"{path}/{key}", depth + 1)
        
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                self._collect_pseudo_arrays(item, f"{path}/{i}", depth + 1)

    def to_schema(self) -> Dict[str, Any]:
        """Генерирует схему с преобразованными псевдо-массивами."""
        schema = super().to_schema()
        self._convert_pseudo_arrays_in_schema(schema, "#")
        return schema

    def _convert_pseudo_arrays_in_schema(self, node: Dict[str, Any], path: str, depth: int = 0) -> None:
        """
        Преобразует псевдо-массивы в схеме.
        """
        if depth > self.MAX_DEPTH:
            return
            
        # Проверяем, есть ли псевдо-массив для этого пути
        if path in self._pseudo_arrays:
            # Получаем все объекты псевдо-массива
            pseudo_array_objects = self._pseudo_arrays[path]
            
            # Создаем отдельный FormatConverter(SchemaBuilder) для объединения схем элементов
            from ..to_schema_converter import JsonToSchemaConverter
            builder = JsonToSchemaConverter()
            for obj in pseudo_array_objects:
                for value in obj.values():
                    builder.add_object(value)
            
            # Получаем объединенную схему элемента
            element_schema = builder.to_schema()
            
            # Получаем паттерн ключей
            keys = self._path_keys.get(path, set())
            pattern_info = self._key_pattern_orchestrator.detect_pattern(keys)
            
            if pattern_info:
                # Преобразуем узел в patternProperties
                node.clear()
                node.update({
                    "type": "object",
                    "propertyNames": {"pattern": f"^{pattern_info['pattern_regex']}$"},
                    "patternProperties": {
                        f"^{pattern_info['pattern_regex']}$": element_schema
                    },
                    "additionalProperties": False
                })
                return
        
        # Рекурсивно обходим дочерние узлы
        if node.get("type") == "object":
            if "properties" in node:
                for key, sub_schema in node["properties"].items():
                    self._convert_pseudo_arrays_in_schema(sub_schema, f"{path}/{key}", depth + 1)
            
            if "patternProperties" in node:
                for pattern, sub_schema in node["patternProperties"].items():
                    self._convert_pseudo_arrays_in_schema(sub_schema, f"{path}/*", depth + 1)
        
        elif node.get("type") == "array" and "items" in node:
            items = node["items"]
            if isinstance(items, dict):
                self._convert_pseudo_arrays_in_schema(items, f"{path}/0", depth + 1)
            elif isinstance(items, list):
                for i, item_schema in enumerate(items):
                    self._convert_pseudo_arrays_in_schema(item_schema, f"{path}/{i}", depth + 1)
        
        # Обрабатываем oneOf/anyOf/allOf
        for combinator in ['oneOf', 'anyOf', 'allOf']:
            if combinator in node and isinstance(node[combinator], list):
                for variant in node[combinator]:
                    self._convert_pseudo_arrays_in_schema(variant, path, depth + 1)
