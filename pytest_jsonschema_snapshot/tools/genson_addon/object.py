# [file name]: pattern_object_strategy.py
from typing import Any, Dict, Set, List, Optional
from genson.schema.strategies import Object
from .pseudo_arrays.orchestrator import KeyPatternOrchestrator


class PatternObjectStrategy(Object):
    """Стратегия для объектов, которая автоматически определяет и объединяет псевдо-массивы."""
    
    def __init__(self, node_class):
        super().__init__(node_class)
        self.orchestrator = KeyPatternOrchestrator()
        
        # Храним информацию о каждом добавленном объекте/схеме
        self.object_datas: List[Dict] = []
        self.schema_datas: List[Dict] = []
        self.added_objects: List[dict] = []
        self.added_schemas: List[Dict[str, Any]] = []
        self.blacklisted_patterns: Set[str] = set()
    
    def add_object(self, obj: dict) -> None:
        super().add_object(obj)
        self.added_objects.append(obj)
        
        # Анализируем объект
        keys = set(obj.keys())
        is_empty = len(obj) == 0
        has_pattern = False
        detected_pattern = None
        wrapper_key = None
        values_source = obj
        
        # Проверяем на вложенный псевдо-массив
        if len(keys) == 1 and not is_empty:
            wrapper_key = next(iter(keys))
            inner_obj = obj[wrapper_key]
            if isinstance(inner_obj, dict):
                inner_keys = set(inner_obj.keys())
                if len(inner_keys) >= 3:
                    pattern_info, rejected_patterns = self.orchestrator.detect_pattern_with_rejects(
                        inner_keys, exclude_patterns=self.blacklisted_patterns)
                    if pattern_info:
                        has_pattern = True
                        detected_pattern = pattern_info['pattern_regex']
                        values_source = inner_obj
                    # Обновляем черный список
                    self.blacklisted_patterns.update(rejected_patterns)
        
        # Если не вложенный - проверяем корень
        if not has_pattern and len(keys) >= 3 and not is_empty:
            pattern_info, rejected_patterns = self.orchestrator.detect_pattern_with_rejects(
                keys, exclude_patterns=self.blacklisted_patterns)
            if pattern_info:
                has_pattern = True
                detected_pattern = pattern_info['pattern_regex']
                wrapper_key = None
            self.blacklisted_patterns.update(rejected_patterns)
        
        # Сохраняем информацию об объекте
        self.object_datas.append({
            'type': 'object',
            'keys': keys,
            'is_empty': is_empty,
            'has_pattern': has_pattern,
            'detected_pattern': detected_pattern,
            'values_source': values_source if has_pattern else None,
            'wrapper_key': wrapper_key if has_pattern else None,
            'is_pseudo_array': has_pattern and len(values_source) >= 3
        })
        print(f"Adding object: keys={keys}, has_pattern={has_pattern}, detected_pattern={detected_pattern}, wrapper_key={wrapper_key}")
    
    def add_schema(self, schema: Dict[str, Any]) -> None:
        super().add_schema(schema)
        self.added_schemas.append(schema)
        
        # Извлекаем excludePatterns из схемы
        if "excludePatterns" in schema:
            self.blacklisted_patterns.update(schema["excludePatterns"])
        
        # Анализируем схему
        is_empty = False
        has_pattern = False
        detected_pattern = None
        wrapper_key = None
        inner_schema = schema
        
        # Проверяем пустой объект
        if schema.get("maxProperties") == 0:
            is_empty = True
        
        # Проверяем wrapped схему
        if schema.get("type") == "object" and "properties" in schema and len(schema["properties"]) == 1:
            wrapper_key = next(iter(schema["properties"]))
            inner_schema = schema["properties"][wrapper_key]
            if "excludePatterns" in inner_schema:
                self.blacklisted_patterns.update(inner_schema["excludePatterns"])
            
            if "propertyNames" in inner_schema and "pattern" in inner_schema["propertyNames"]:
                detected_pattern = self.orchestrator.detect_pattern_from_schema(inner_schema)
                if detected_pattern and f"^{detected_pattern}$" not in self.blacklisted_patterns:
                    has_pattern = True
                else:
                    detected_pattern = None
        
        # Проверяем корневой паттерн
        elif "propertyNames" in schema and "pattern" in schema["propertyNames"]:
            detected_pattern = self.orchestrator.detect_pattern_from_schema(schema)
            if detected_pattern and f"^{detected_pattern}$" not in self.blacklisted_patterns:
                has_pattern = True
                wrapper_key = None
            else:
                detected_pattern = None
        
        # Сохраняем информацию о схеме
        self.schema_datas.append({
            'type': 'schema',
            'is_empty': is_empty,
            'has_pattern': has_pattern,
            'detected_pattern': detected_pattern,
            'inner_schema': inner_schema if has_pattern else schema,
            'wrapper_key': wrapper_key if has_pattern else None,
            'is_pseudo_array': has_pattern
        })
        print(f"Adding schema: has_pattern={has_pattern}, detected_pattern={detected_pattern}, wrapper_key={wrapper_key}")
    
    def _should_use_pattern_properties(self) -> bool:
        """Определяет, нужно ли использовать patternProperties."""
        all_datas = self.object_datas + self.schema_datas
        if not all_datas:
            return False
        
        # Если хотя бы один не имеет паттерна (и не пустой) - отбрасываем все паттерны
        non_pattern_items = [
            data for data in all_datas 
            if not data['is_empty'] and not data['has_pattern']
        ]
        
        if non_pattern_items:
            print(f"Non-pattern items count: {len(non_pattern_items)}")
            return False
        
        # Проверяем, что все с паттернами имеют псевдо-массивы
        pattern_items = [data for data in all_datas if data['has_pattern']]
        
        if not pattern_items:
            return False
            
        if not all(data['is_pseudo_array'] for data in pattern_items):
            return False
        
        # Проверяем однородность wrapper_key
        wrappers = {data['wrapper_key'] for data in pattern_items}
        if len(wrappers) > 1:
            print("Mixed wrappers detected, discarding patterns")
            return False
        
        return True
    
    def _get_unified_pattern(self) -> Optional[str]:
        """Получает объединенный паттерн для всех."""
        pattern_schemas = []
        
        # Добавляем из объектов
        for data in self.object_datas:
            if data['has_pattern']:
                pattern_schemas.append({
                    "propertyNames": {"pattern": f"^{data['detected_pattern']}$"}
                })
        
        # Добавляем из схем
        for data in self.schema_datas:
            if data['has_pattern']:
                pattern_schemas.append(data['inner_schema'])
        
        if not pattern_schemas:
            return None
        
        pattern_info = self.orchestrator.find_best_pattern_for_schemas(
            pattern_schemas, self.blacklisted_patterns
        )
        
        if pattern_info:
            return pattern_info['pattern_regex']
        
        return None
    
    def _get_value_schema(self) -> Dict[str, Any]:
        """Получает схему для значений объектов."""
        from genson import SchemaBuilder
        builder = SchemaBuilder()
        
        # Собираем все значения из всех объектов с паттернами
        for data in self.object_datas:
            if data['has_pattern'] and data['values_source']:
                for value in data['values_source'].values():
                    builder.add_object(value)
        
        # Добавляем значения из схем
        for data in self.schema_datas:
            if data['has_pattern'] and "patternProperties" in data['inner_schema']:
                for pattern, value_schema in data['inner_schema']["patternProperties"].items():
                    builder.add_schema(value_schema)
        
        return builder.to_schema()
    
    def to_schema(self) -> Dict[str, Any]:
        # Проверяем, нужно ли использовать patternProperties
        if self._should_use_pattern_properties():
            unified_pattern = self._get_unified_pattern()
            
            all_datas = self.object_datas + self.schema_datas
            wrapper_key = all_datas[0]['wrapper_key'] if all_datas else None  # All same from check
            print(f"Unified pattern: {unified_pattern}, wrapper: {wrapper_key}")
            
            if unified_pattern:
                value_schema = self._get_value_schema()
                
                schema = {
                    "type": "object",
                    "propertyNames": {"pattern": f"^{unified_pattern}$"},
                    "patternProperties": {
                        f"^{unified_pattern}$": value_schema
                    },
                    "additionalProperties": False
                }
                
                # Добавляем информацию о детекторе
                detector = self.orchestrator.get_detector_for_pattern(unified_pattern)
                if detector and hasattr(detector, 'COMMENT'):
                    schema["patternComment"] = detector.COMMENT
                
                # Добавляем черный список, если он есть
                if self.blacklisted_patterns:
                    schema["excludePatterns"] = sorted(list(self.blacklisted_patterns))
                
                # Оборачиваем, если wrapper
                if wrapper_key:
                    schema = {
                        "type": "object",
                        "properties": {wrapper_key: schema},
                        "required": [wrapper_key],
                        "additionalProperties": False
                    }
                
                # Обрабатываем пустые объекты
                if any(data['is_empty'] for data in all_datas):
                    empty_schema = {"maxProperties": 0}
                    if wrapper_key:
                        empty_schema = {
                            "type": "object",
                            "properties": {wrapper_key: {"maxProperties": 0}},
                            "required": [wrapper_key],
                            "additionalProperties": False
                        }
                    schema = {
                        "oneOf": [schema, empty_schema]
                    }
                
                return schema
        
        # Возвращаем обычную схему объекта
        base_schema = super().to_schema()
        # Добавляем черный список, если он есть
        if self.blacklisted_patterns:
            base_schema["excludePatterns"] = sorted(list(self.blacklisted_patterns))
        return base_schema