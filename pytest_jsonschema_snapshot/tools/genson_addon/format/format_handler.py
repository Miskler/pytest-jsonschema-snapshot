# src/jsonschema_infer/format_handler.py
from collections import defaultdict
from typing import Any, Dict, Set

from .format_detector import FormatDetector

class FormatAnalyzer:
    """Анализатор форматов строк в объектах."""
    
    def __init__(self):
        # path -> набор форматов для этого пути
        self._path_formats: Dict[str, Set[str]] = {}
        # path -> есть ли пустые строки
        self._path_empty: Dict[str, bool] = {}
        # path -> есть ли строки без формата
        self._path_no_format: Dict[str, bool] = {}
    
    def analyze(self, obj: Any, path: str = "#") -> None:
        """Анализирует объект и собирает информацию о форматах строк."""
        if isinstance(obj, str):
            self._analyze_string(obj, path)
        elif isinstance(obj, dict):
            # Проверяем, является ли словарь псевдо-массивом
            is_pseudo_array = (
                obj and 
                all(isinstance(k, str) and k.isdigit() for k in obj.keys())
            )
            
            for key, value in obj.items():
                child_path = f"{path}/{key}"
                self.analyze(value, child_path)
                
                # Для псевдо-массивов агрегируем информацию
                if is_pseudo_array:
                    star_path = f"{path}/*/{key}"
                    self._aggregate_path_info(child_path, star_path)
        
        elif isinstance(obj, (list, tuple)):
            for i, item in enumerate(obj):
                self.analyze(item, f"{path}/{i}")
            
            # Агрегируем информацию об элементах массива
            if obj:
                array_elem_path = f"{path}[]"
                for i, item in enumerate(obj):
                    child_path = f"{path}/{i}"
                    self._aggregate_path_info(child_path, array_elem_path)
    
    def _aggregate_path_info(self, source_path: str, target_path: str) -> None:
        """Агрегирует информацию о форматах из одного пути в другой."""
        # Форматы
        if source_path in self._path_formats:
            if target_path not in self._path_formats:
                self._path_formats[target_path] = set()
            self._path_formats[target_path].update(self._path_formats[source_path])
        
        # Пустые строки
        if source_path in self._path_empty and self._path_empty[source_path]:
            self._path_empty[target_path] = True
        
        # Строки без формата
        if source_path in self._path_no_format and self._path_no_format[source_path]:
            self._path_no_format[target_path] = True
    
    def _analyze_string(self, value: str, path: str) -> None:
        """Анализирует строку на предмет форматов."""
        if value == "":
            self._path_empty[path] = True
        else:
            format_name = FormatDetector.detect(value, type_hint="string")
            if format_name:
                if path not in self._path_formats:
                    self._path_formats[path] = set()
                self._path_formats[path].add(format_name)
            else:
                self._path_no_format[path] = True
    
    def get_formats(self, path: str) -> Set[str]:
        """Возвращает форматы для указанного пути."""
        return self._path_formats.get(path, set())
    
    def has_empty(self, path: str) -> bool:
        """Проверяет, есть ли пустые строки на указанном пути."""
        return self._path_empty.get(path, False)
    
    def has_no_format(self, path: str) -> bool:
        """Проверяет, есть ли строки без формата на указанном пути."""
        return self._path_no_format.get(path, False)


class SchemaFormatEnhancer:
    """Улучшает схему, добавляя информацию о форматах."""

    def __init__(self, analyzer: FormatAnalyzer):
        self._analyzer = analyzer

    def enhance(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Рекурсивно добавляет форматы к схеме."""
        import copy

        result = copy.deepcopy(schema)
        self._enhance_node(result, "#")
        return result

    def _enhance_node(self, node: Dict[str, Any], path: str) -> None:
        """Добавляет форматы к узлу схемы."""
        node_type = node.get("type")

        # Если это строка, добавляем форматы
        if node_type == "string" and "oneOf" not in node:
            self._add_string_formats(node, path)

        # Если это массив типов, обрабатываем каждый тип
        elif isinstance(node_type, list):
            self._enhance_multitype_node(node, path)

        # Если это oneOf/anyOf/allOf, обрабатываем каждый вариант
        # Используем тот же путь для всех вариантов в anyOf/oneOf
        for combinator in ["oneOf", "anyOf", "allOf"]:
            if combinator in node and isinstance(node[combinator], list):
                for variant in node[combinator]:
                    if isinstance(variant, dict):
                        self._enhance_node(variant, path)

        # Рекурсивно обрабатываем вложенные структуры
        if node_type == "object":
            if "properties" in node:
                for prop_name, prop_schema in node["properties"].items():
                    if isinstance(prop_schema, dict):
                        self._enhance_node(prop_schema, f"{path}/{prop_name}")

            if "patternProperties" in node:
                for pattern, sub_schema in node["patternProperties"].items():
                    if isinstance(sub_schema, dict):
                        # Для patternProperties используем путь с *
                        self._enhance_node(sub_schema, f"{path}/*")

        elif node_type == "array" and "items" in node:
            items = node["items"]
            if isinstance(items, dict):
                self._enhance_node(items, f"{path}[]")
            elif isinstance(items, list):
                for i, item_schema in enumerate(items):
                    if isinstance(item_schema, dict):
                        self._enhance_node(item_schema, f"{path}/{i}")

    def _enhance_multitype_node(self, node: Dict[str, Any], path: str) -> None:
        """Обрабатывает узел с несколькими типами."""
        node_type = node["type"]

        # Если среди типов есть строка, нужно добавить форматы
        if "string" in node_type:
            # Преобразуем массив типов в oneOf
            variants = []
            string_variant_added = False

            for type_name in node_type:
                if type_name == "string":
                    # Создаем строковый вариант с форматами
                    string_variant = {"type": "string"}
                    self._add_string_formats(string_variant, path)
                    variants.append(string_variant)
                    string_variant_added = True
                else:
                    variants.append({"type": type_name})

            # Если строка была добавлена, заменяем узел на oneOf
            if string_variant_added:
                # Сохраняем другие свойства узла
                other_props = {k: v for k, v in node.items() if k != "type"}
                node.clear()
                node.update(other_props)
                node["oneOf"] = variants

    def _add_string_formats(self, node: Dict[str, Any], path: str) -> None:
        """Добавляет форматы к строковому узлу."""
        formats = self._analyzer.get_formats(path)
        has_empty = self._analyzer.has_empty(path)
        has_no_format = self._analyzer.has_no_format(path)

        # Если есть строки без формата (не пустые), не добавляем форматы вообще
        if has_no_format:
            return

        # Если есть только пустые строки
        if not formats and has_empty:
            node["maxLength"] = 0
            return

        # Если есть только один формат и нет пустых строк
        if len(formats) == 1 and not has_empty:
            node["format"] = next(iter(formats))
            return

        # Несколько форматов или смесь форматов и пустых строк
        format_variants: Dict[str, Any] = []

        for fmt in sorted(formats):
            format_variants.append({"format": fmt})

        if has_empty:
            format_variants.append({"maxLength": 0})

        # Если вариантов больше 1, создаем oneOf
        if len(format_variants) > 1:
            # Добавляем oneOf, сохраняя существующие свойства
            existing_props = {k: v for k, v in node.items() if k != "format"}
            node.clear()
            node.update(existing_props)
            node["oneOf"] = format_variants
        elif len(format_variants) == 1:
            # Если остался только один вариант, используем его напрямую
            node.update(format_variants[0])


class FormatConverter:
    """Конвертер форматов строк для JSON Schema."""

    def __init__(self, *, format_mode: str = "on") -> None:
        self.format_mode = format_mode
        self._analyzer = FormatAnalyzer()

    def add_object(self, obj: Any) -> None:
        """Добавляет объект для анализа форматов."""
        self._analyzer.analyze(obj)

    def to_schema(self, base_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Добавляет форматы к схеме."""
        if self.format_mode == "off":
            return base_schema

        # Улучшаем схему форматами
        enhancer = SchemaFormatEnhancer(self._analyzer)
        schema = enhancer.enhance(base_schema)

        # Добавляем vocabulary в безопасном режиме
        if self.format_mode == "safe":
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
