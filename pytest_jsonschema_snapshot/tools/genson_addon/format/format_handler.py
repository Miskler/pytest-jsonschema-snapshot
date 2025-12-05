# src/jsonschema_infer/format_handler.py
from typing import Any, Dict, Set, List, Optional, Union
from collections import defaultdict
from dataclasses import dataclass, field
from .format_detector import FormatDetector


@dataclass
class TypeInfo:
    """Информация о типе узла."""
    path: str
    types: Set[str] = field(default_factory=set)
    formats: Set[str] = field(default_factory=set)
    has_empty_string: bool = False
    
    def merge(self, other: 'TypeInfo') -> None:
        """Объединяет информацию из другого узла."""
        self.types.update(other.types)
        self.formats.update(other.formats)
        self.has_empty_string = self.has_empty_string or other.has_empty_string
    
    def normalize_types(self) -> Set[str]:
        """Нормализует типы (убирает integer если есть number)."""
        types = set(self.types)
        if 'number' in types and 'integer' in types:
            types.discard('integer')
        return types


class TypeCollector:
    """Собирает информацию о типах в объекте."""
    
    def __init__(self):
        self._nodes: Dict[str, TypeInfo] = {}
        self._pattern_aggregates: Dict[str, Dict[str, TypeInfo]] = defaultdict(dict)
    
    def collect(self, obj: Any, path: str = "#") -> None:
        """Рекурсивно собирает информацию об объекте."""
        self._collect_node(obj, path)
    
    def get_info(self, path: str) -> Optional[TypeInfo]:
        """Возвращает информацию о типе по пути."""
        # Прямой путь
        if path in self._nodes:
            return self._nodes[path]
        
        # Попытка найти через pattern path (/*/)
        if '/*/' in path:
            # Разбираем путь на родительскую часть и имя поля
            parts = path.split('/*/')
            if len(parts) == 2:
                parent_path, field_name = parts[0], parts[1]
                if parent_path in self._pattern_aggregates and field_name in self._pattern_aggregates[parent_path]:
                    return self._pattern_aggregates[parent_path][field_name]
        
        return None
    
    def _collect_node(self, obj: Any, path: str) -> TypeInfo:
        """Собирает информацию для одного узла."""
        info = TypeInfo(path)
        self._determine_type(obj, info)
        
        if isinstance(obj, dict):
            self._collect_dict(obj, path, info)
        elif isinstance(obj, (list, tuple)):
            self._collect_array(obj, path, info)
        
        self._nodes[path] = info
        return info
    
    def _determine_type(self, obj: Any, info: TypeInfo) -> None:
        """Определяет тип объекта и его форматы."""
        if obj is None:
            info.types.add('null')
        elif isinstance(obj, bool):
            info.types.add('boolean')
        elif isinstance(obj, int):
            info.types.add('integer')
        elif isinstance(obj, float):
            info.types.add('number')
        elif isinstance(obj, str):
            info.types.add('string')
            if obj == "":
                info.has_empty_string = True
            else:
                format_name = FormatDetector.detect(obj, type_hint="string")
                if format_name:
                    info.formats.add(format_name)
        elif isinstance(obj, dict):
            info.types.add('object')
        elif isinstance(obj, (list, tuple)):
            info.types.add('array')
    
    def _collect_dict(self, obj: Dict[str, Any], path: str, info: TypeInfo) -> None:
        """Собирает информацию для словаря."""
        # Проверяем, является ли это псевдо-массивом
        keys = list(obj.keys())
        is_pseudo_array = (
            keys and 
            all(isinstance(k, str) and k.isdigit() for k in keys)
        )
        
        # Собираем информацию о дочерних узлах
        for key, value in obj.items():
            child_path = f"{path}/{key}"
            child_info = self._collect_node(value, child_path)
            
            # Если это псевдо-массив и значение - объект, агрегируем информацию по полям
            if is_pseudo_array and isinstance(value, dict):
                self._aggregate_pattern_fields(path, key, value)
    
    def _aggregate_pattern_fields(self, parent_path: str, numeric_key: str, obj: Dict[str, Any]) -> None:
        """Агрегирует информацию по полям для patternProperties."""
        for field_name, field_value in obj.items():
            field_path = f"{parent_path}/{numeric_key}/{field_name}"
            
            # Собираем информацию о поле
            field_info = TypeInfo(field_path)
            self._determine_type(field_value, field_info)
            
            # Для вложенных структур рекурсивно собираем информацию
            if isinstance(field_value, dict):
                self._collect_dict(field_value, field_path, field_info)
            elif isinstance(field_value, (list, tuple)):
                self._collect_array(field_value, field_path, field_info)
            
            # Сохраняем информацию о поле
            self._nodes[field_path] = field_info
            
            # Агрегируем информацию для pattern path
            pattern_path = f"{parent_path}/*/{field_name}"
            if field_name not in self._pattern_aggregates[parent_path]:
                self._pattern_aggregates[parent_path][field_name] = TypeInfo(pattern_path)
            
            # Объединяем информацию из всех числовых ключей
            self._pattern_aggregates[parent_path][field_name].merge(field_info)
    
    def _collect_array(self, arr: List[Any], path: str, info: TypeInfo) -> None:
        """Собирает информацию для массива."""
        for i, item in enumerate(arr):
            child_path = f"{path}/{i}"
            self._collect_node(item, child_path)
        
        # Агрегируем информацию об элементах массива
        if arr:
            array_elem_path = f"{path}[]"
            array_info = TypeInfo(array_elem_path)
            
            for i, item in enumerate(arr):
                child_path = f"{path}/{i}"
                child_info = self._nodes.get(child_path)
                if child_info:
                    array_info.merge(child_info)
            
            self._nodes[array_elem_path] = array_info


class SchemaEnhancer:
    """Улучшает схему информацией о типах и форматах."""
    
    def __init__(self, collector: TypeCollector):
        self._collector = collector
    
    def enhance(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """Улучшает схему информацией о типах."""
        import copy
        result = copy.deepcopy(schema)
        self._enhance_node(result, "#")
        return result
    
    def _enhance_node(self, node: Dict[str, Any], path: str) -> None:
        """Рекурсивно улучшает узел схемы."""
        # Получаем информацию о типе
        info = self._collector.get_info(path)
        
        if info:
            self._apply_type_info(node, info)
        
        # Рекурсивно обрабатываем дочерние узлы
        self._process_children(node, path)
    
    def _apply_type_info(self, node: Dict[str, Any], info: TypeInfo) -> None:
        """Применяет информацию о типах к узлу схемы."""
        # Если у узла уже есть oneOf или anyOf, пропускаем
        if 'oneOf' in node or 'anyOf' in node:
            return
        
        # Получаем текущий тип из узла
        current_type = node.get('type')
        
        if current_type is None:
            # У узла нет типа, создаем на основе информации
            self._create_type_from_info(node, info)
        else:
            # Узел уже имеет тип, улучшаем его
            self._enhance_existing_type(node, info, current_type)
    
    def _create_type_from_info(self, node: Dict[str, Any], info: TypeInfo) -> None:
        """Создает тип на основе информации."""
        types = info.normalize_types()
        
        if not types:
            return
        
        if len(types) == 1:
            self._apply_single_type(node, info, next(iter(types)))
        else:
            self._create_oneof(node, info, types)
    
    def _enhance_existing_type(self, node: Dict[str, Any], info: TypeInfo, current_type: Union[str, List[str]]) -> None:
        """Улучшает существующий тип информацией."""
        if isinstance(current_type, list):
            # Уже массив типов
            current_types = set(current_type)
            info_types = info.normalize_types()
            all_types = current_types.union(info_types)
            
            if len(all_types) == 1:
                node['type'] = next(iter(all_types))
                if node['type'] == 'string':
                    self._apply_string_formats(node, info)
            elif len(all_types) > 1:
                self._create_oneof(node, info, all_types)
        else:
            # Один тип
            current_types = {current_type}
            info_types = info.normalize_types()
            all_types = current_types.union(info_types)
            
            if len(all_types) == 1:
                # Тип не изменился
                if current_type == 'string':
                    self._apply_string_formats(node, info)
            else:
                # Добавились новые типы
                self._create_oneof(node, info, all_types)
    
    def _apply_single_type(self, node: Dict[str, Any], info: TypeInfo, type_name: str) -> None:
        """Применяет одиночный тип к узлу."""
        node['type'] = type_name
        
        if type_name == 'string':
            self._apply_string_formats(node, info)
    
    def _create_oneof(self, node: Dict[str, Any], info: TypeInfo, types: Set[str]) -> None:
        """Создает oneOf для нескольких типов."""
        # Сохраняем текущую схему
        current_schema = node.copy()
        
        # Проверяем, имеет ли текущая схема контент
        current_type = current_schema.get('type')
        if isinstance(current_type, list):
            # Если текущий тип - список, проверяем пересечение с типами
            current_type_set = set(current_type)
            has_content = len(current_schema) > 1 or bool(current_type_set.intersection(types))
        else:
            # Если текущий тип - строка или None
            has_content = len(current_schema) > 1 or (current_type in types)
        
        variants = []
        
        # Если текущая схема имеет контент и её тип входит в список, добавляем её
        if has_content and current_type is not None:
            if isinstance(current_type, list):
                # Разбиваем на отдельные варианты
                for t in current_type:
                    variant = {'type': t}
                    if t == 'string':
                        self._apply_string_formats(variant, info)
                    variants.append(variant)
            elif current_type in types:
                if current_type == 'string':
                    self._apply_string_formats(current_schema, info)
                variants.append(current_schema)
        
        # Добавляем остальные типы
        for type_name in sorted(types):
            if has_content and current_type == type_name:
                continue
            
            variant = {'type': type_name}
            
            if type_name == 'string':
                self._apply_string_formats(variant, info)
            
            variants.append(variant)
        
        if len(variants) == 1:
            node.clear()
            node.update(variants[0])
        elif variants:
            # Сохраняем только структурные поля
            for key in list(node.keys()):
                if key not in ['properties', 'items', 'patternProperties', 'required']:
                    del node[key]
            node['oneOf'] = variants
    
    def _apply_string_formats(self, node: Dict[str, Any], info: TypeInfo) -> None:
        """Применяет форматы к строковому узлу."""
        if not info.formats and not info.has_empty_string:
            return
        
        format_variants = []
        
        for fmt in sorted(info.formats):
            format_variants.append({'format': fmt})
        
        if info.has_empty_string:
            format_variants.append({'maxLength': 0})
        
        if len(format_variants) == 1:
            node.update(format_variants[0])
        elif format_variants:
            node['oneOf'] = format_variants
    
    def _process_children(self, node: Dict[str, Any], path: str) -> None:
        """Обрабатывает дочерние узлы схемы."""
        # Обработка объектов
        if node.get('type') == 'object':
            if 'properties' in node:
                for prop_name, prop_schema in node['properties'].items():
                    if isinstance(prop_schema, dict):
                        self._enhance_node(prop_schema, f"{path}/{prop_name}")
            
            if 'patternProperties' in node:
                for pattern, sub_schema in node['patternProperties'].items():
                    if isinstance(sub_schema, dict):
                        self._enhance_node(sub_schema, f"{path}/*")
        
        # Обработка массивов
        elif node.get('type') == 'array' and 'items' in node:
            items = node['items']
            if isinstance(items, dict):
                self._enhance_node(items, f"{path}[]")
            elif isinstance(items, list):
                for i, item_schema in enumerate(items):
                    if isinstance(item_schema, dict):
                        self._enhance_node(item_schema, f"{path}/{i}")
        
        # Обработка комбинаторов
        for combinator in ['anyOf', 'allOf', 'oneOf']:
            if combinator in node and isinstance(node[combinator], list):
                for i, sub_schema in enumerate(node[combinator]):
                    if isinstance(sub_schema, dict):
                        self._enhance_node(sub_schema, f"{path}/{combinator}/{i}")


class FormatConverter:
    """Конвертер форматов строк для JSON Schema."""
    
    def __init__(self, *, format_mode: str = "on") -> None:
        self.format_mode = format_mode
        self._collector = TypeCollector()
    
    def add_object(self, obj: Any) -> None:
        """Добавляет объект для анализа форматов."""
        self._collector.collect(obj)
    
    def to_schema(self, base_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Обогащает схему информацией о форматах."""
        if self.format_mode == "off":
            return base_schema
        
        # Улучшаем схему
        enhancer = SchemaEnhancer(self._collector)
        schema = enhancer.enhance(base_schema)
        
        # Добавляем vocabulary в безопасном режиме
        if self.format_mode == "safe":
            schema.setdefault('$vocabulary', {
                'https://json-schema.org/draft/2020-12/vocab/core': True,
                'https://json-schema.org/draft/2020-12/vocab/applicator': True,
                'https://json-schema.org/draft/2020-12/vocab/format-annotation': True,
                'https://json-schema.org/draft/2020-12/vocab/format-assertion': False,
            })
        
        return schema