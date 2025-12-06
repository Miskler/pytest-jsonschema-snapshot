# src/jsonschema_infer/pseudo_array_converter.py
from __future__ import annotations

from typing import Any, Dict, List

from genson import SchemaBuilder


class PseudoArrayConverter(SchemaBuilder):
    """
    Специализированный SchemaBuilder для преобразования псевдо-массивов
    (словарей с последовательными числовыми строковыми ключами) в patternProperties.
    """

    def __init__(
        self,
        schema_uri: str = "https://json-schema.org/draft/2020-12/schema",
    ) -> None:
        super().__init__()
        # Храним сырые объекты по путям для анализа псевдо-массивов
        self._raw_at_path: Dict[str, Any] = {}
        # Храним все добавленные объекты целиком
        self._all_objects: List[Any] = []

    # ------------------------------------------------------------------ #
    # Сбор сырых данных
    # ------------------------------------------------------------------ #
    def add_object(self, obj: Any) -> None:
        """Добавляет объект для анализа."""
        self._all_objects.append(obj)
        self._collect_raw(obj, "#")
        super().add_object(obj)

    def _collect_raw(self, obj: Any, path: str) -> None:
        """Рекурсивно собирает сырые данные по путям."""
        self._raw_at_path[path] = obj

        if isinstance(obj, dict):
            for k, v in obj.items():
                self._collect_raw(v, f"{path}/{k}")
        elif isinstance(obj, (list, tuple)):
            for i, v in enumerate(obj):
                self._collect_raw(v, f"{path}/{i}")

    # ------------------------------------------------------------------ #
    # Генерация схемы с преобразованием псевдо-массивов
    # ------------------------------------------------------------------ #
    def to_schema(self) -> Dict[str, Any]:
        """Генерирует схему с преобразованными псевдо-массивами."""
        schema = super().to_schema()
        self._convert_pseudo_arrays(schema, "#")
        return schema

    # ------------------------------------------------------------------ #
    # Логика преобразования псевдо-массивов
    # ------------------------------------------------------------------ #
    def _convert_pseudo_arrays(self, node: Dict[str, Any], path: str) -> None:
        """
        Рекурсивно преобразует псевдо-массивы в patternProperties.
        Теперь использует все добавленные объекты для правильного определения типов.
        """
        if not (node.get("type") == "object" and "properties" in node):
            self._recurse(node, self._convert_pseudo_arrays, path)
            return

        # Получаем все значения для этого пути из всех объектов
        values_at_path = self._get_all_values_at_path(path)

        if not values_at_path:
            self._recurse(node, self._convert_pseudo_arrays, path)
            return

        # Проверяем, являются ли все значения словарями с числовыми ключами
        all_have_numeric_keys = all(
            isinstance(v, dict) and all(isinstance(k, str) and k.isdigit() for k in v.keys())
            for v in values_at_path
            if v is not None
        )

        if not all_have_numeric_keys:
            self._recurse(node, self._convert_pseudo_arrays, path)
            return

        # Собираем все числовые ключи из всех объектов
        all_keys = set()
        for value in values_at_path:
            if isinstance(value, dict):
                all_keys.update(value.keys())

        if not all_keys:
            return

        # Проверяем условия для преобразования в псевдо-массив
        if self._should_convert_to_pseudo_array(all_keys):
            # Собираем все вложенные объекты для объединения схем
            nested_objects = []
            for value in values_at_path:
                if isinstance(value, dict):
                    for k in sorted(value.keys(), key=int):
                        nested_objects.append(value[k])

            # Создаем схему для вложенных объектов
            item_schema = self._create_schema_for_objects(nested_objects)

            # Преобразуем в patternProperties
            node.clear()
            node.update(
                {
                    "type": "object",
                    "propertyNames": {"pattern": "^[0-9]+$"},
                    "patternProperties": {"^[0-9]+$": item_schema},
                    "additionalProperties": False,
                }
            )
            return

        self._recurse(node, self._convert_pseudo_arrays, path)

    def _get_all_values_at_path(self, path: str) -> List[Any]:
        """Получает все значения по указанному пути из всех объектов."""
        values = []

        # Если есть значение в _raw_at_path (последний добавленный объект)
        if path in self._raw_at_path:
            values.append(self._raw_at_path[path])

        # Также ищем в предыдущих объектах
        for obj in self._all_objects[:-1]:  # Все кроме последнего
            value = self._extract_value_from_path(obj, path)
            if value is not None:
                values.append(value)

        return values

    def _extract_value_from_path(self, obj: Any, path: str) -> Any:
        """Извлекает значение по пути из объекта."""
        if path == "#":
            return obj

        # Пропускаем начальный #
        parts = path[2:].split("/") if path.startswith("#/") else path.split("/")

        current = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, (list, tuple)) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return None
            else:
                return None

        return current

    def _should_convert_to_pseudo_array(self, keys: set) -> bool:
        """Определяет, следует ли преобразовать в псевдо-массив."""
        return all(k.isdigit() for k in keys)

    def _create_schema_for_objects(self, objects: List[Any]) -> Dict[str, Any]:
        """Создает схему для списка объектов, объединяя их типы."""
        if not objects:
            return {"type": "object"}

        # Используем genson для объединения типов
        from .to_schema_converter import JsonToSchemaConverter

        builder = JsonToSchemaConverter()
        for obj in objects:
            builder.add_object(obj)

        return builder.to_schema()

    # ------------------------------------------------------------------ #
    # Вспомогательные методы
    # ------------------------------------------------------------------ #
    def _recurse(self, node: Dict[str, Any], func: callable, path: str) -> None:
        """Рекурсивно обходит схему."""
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
