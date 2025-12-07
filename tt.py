#!/usr/bin/env python3
# demo.py
"""
Демонстрация работы JsonToSchemaConverter

Показывает:
1. Автоматическое определение форматов (email, uuid, date-time и т.д.)
2. Три режима работы с format:
   - "on"   → строгие форматы (по умолчанию)
   - "off"  → форматы полностью игнорируются
   - "safe" → форматы остаются как аннотации, но валидация отключена
3. Корректное преобразование "псевдо-массивов" вида {"0": {...}, "1": {...}}
4. Локальное включение format-annotation только при неоднозначных форматах
"""

import json
from pprint import pprint

from pytest_jsonschema_snapshot.tools.genson_addon import JsonToSchemaConverter


# Пример данных, максимально похожий на реальные ответы API
SAMPLE_DATA = {
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Test Data",
  
  "uuid_objects": {
    "550e8400-e29b-41d4-a716-446655440000": {"status": "active", "score": 95},
    "6ba7b810-9dad-11d1-80b4-00c04fd430c8": {"status": "inactive", "score": 42},
    "6ba7b811-9dad-11d1-80b4-00c04fd430c8": {"status": "active", "score": 78}
  },
  
  "daily_metrics": {
    "2024-01-15": {"visitors": 1500, "conversion": 2.3},
    "2024-01-16": {"visitors": 1680, "conversion": 2.5},
    "2024-01-17": {"visitors": 1420, "conversion": 2.1},
    "2024-01-18": {"visitors": 1750, "conversion": 2.7}
  },
  
  "event_logs": {
    "2024-01-15T10:30:00Z": {"event": "login", "user": "john"},
    "2024-01-15T10:32:15Z": {"event": "purchase", "user": "alice"},
    "2024-01-15T10:35:22Z": {"event": "logout", "user": "john"}
  },
  
  "country_data": {
    "US": {"population": 331900000, "capital": "Washington"},
    "GB": {"population": 67860000, "capital": "London"},
    "DE": {"population": 83240000, "capital": "Berlin"},
    "FR": {"population": 67410000, "capital": "Paris"}
  },
  
  "language_stats": {
    "en-US": {"speakers": 250000000, "native": True},
    "es-ES": {"speakers": 47000000, "native": True},
    "fr-FR": {"speakers": 76000000, "native": True},
    "de-DE": {"speakers": 95000000, "native": True}
  },
  
  "color_palette": {
    "0xFF5733": {"name": "Vibrant Orange", "rgb": [255, 87, 51]},
    "0x33FF57": {"name": "Electric Green", "rgb": [51, 255, 87]},
    "0x3357FF": {"name": "Bright Blue", "rgb": [51, 87, 255]},
    "0xFF33F5": {"name": "Hot Pink", "rgb": [255, 51, 245]},
    "0xF5FF33": {"name": "Lemon Yellow", "rgb": [245, 255, 51]}
  },
  
  "memory_addresses": {
    "0x1A3F": {"value": 6719, "description": "Buffer start"},
    "0x1A40": {"value": 6720, "description": "Buffer offset 1"},
    "0x1A41": {"value": 6721, "description": "Buffer offset 2"},
    "0x1A42": {"value": 6722, "description": "Buffer offset 3"}
  },
  
  "grade_book": {
    "a": {"student": "Alice", "score": 95, "grade": "A"},
    "b": {"student": "Bob", "score": 87, "grade": "B"},
    "c": {"student": "Charlie", "score": 92, "grade": "A-"},
    "d": {"student": "Diana", "score": 78, "grade": "C+"}
  },
  
  "categorized_items": {
    "alpha": {"count": 10, "category": "primary"},
    "beta": {"count": 15, "category": "secondary"},
    "gamma": {"count": 8, "category": "tertiary"},
    "delta": {"count": 12, "category": "secondary"}
  },
  
  "negative_indexes": {
    "-3": {"value": "three steps back", "index": -3},
    "-2": {"value": "two steps back", "index": -2},
    "-1": {"value": "one step back", "index": -1}
  },
  
  "temperature_ranges": {
    "-10": {"description": "Very cold", "fahrenheit": 14},
    "-5": {"description": "Cold", "fahrenheit": 23},
    "0": {"description": "Freezing point", "fahrenheit": 32},
    "5": {"description": "Chilly", "fahrenheit": 41}
  },
  
  "array_like": {
    "0": {"id": 1001, "product": "Laptop", "price": 999.99},
    "1": {"id": 1002, "product": "Mouse", "price": 29.99},
    "2": {"id": 1003, "product": "Keyboard", "price": 79.99},
    "3": {"id": 1004, "product": "Monitor", "price": 299.99}
  },
  
  "sequential_data": {
    "10": {"step": "initialization", "status": "completed"},
    "20": {"step": "processing", "status": "in_progress"},
    "30": {"step": "validation", "status": "pending"},
    "40": {"step": "finalization", "status": "pending"}
  },
  
  "mixed_but_mostly_numeric": {
    "1": {"type": "numeric", "note": "Regular numeric key"},
    "2": {"type": "numeric", "note": "Another numeric"},
    "3": {"type": "numeric", "note": "Third numeric"},
    "a": {"type": "alphabetic", "note": "Should be ignored in pattern"}
  },
  
  "sparse_numeric_keys": {
    "1": {"data": "first"},
    "3": {"data": "third"},
    "5": {"data": "fifth"},
    "7": {"data": "seventh"}
  },
  
  "not_array_like": {
    "first": {"value": 1},
    "second": {"value": 2}
  },
  
  "mixed_types": {
    "1": {"type": "number"},
    "a": {"type": "letter"},
    "2024-01-01": {"type": "date"}
  },
  
  "metadata": {
    "created": "2024-01-15T10:00:00Z",
    "version": "1.0.0",
    "author": "system"
  }
}


def demo_mode(mode: str) -> None:
    print(f"\n{'='*60}")
    print(f"Режим format_mode = \"{mode}\"".center(60))
    print(f"{'='*60}")

    converter = JsonToSchemaConverter(format_mode=mode)  # type: ignore[arg-type]
    converter.add_object(SAMPLE_DATA)

    schema = converter.to_schema()

    print(json.dumps(schema, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    print("Демонстрация JsonToSchemaConverter\n")

    demo_mode("on")
    #demo_mode("off")
    #demo_mode("safe")

    # Дополнительно: только один объект с неоднозначным форматом
    #print("\n\n" + "="*60)
    #print("Демонстрация локального format-annotation".center(60))
    #print("="*60)

    #conv = JsonToSchemaConverter(format_mode="on")
    #conv.add_object({"values": SAMPLE_DATA["mixed_format_field"]})
    #schema_part = conv.to_schema()
    #print(json.dumps(schema_part, indent=2, ensure_ascii=False))
    #print("\n→ Видно, что для пути #/values включён только format-annotation (без строгого формата)")

# 1. алфавитник срабатывает и на слова (неправильно)
# 2. добавить паттерн с отрицательными числами
# 3. переименовать цветовой паттерн в хекс
# 4. добавить проперти "комментарий" для быстрого считывания цели паттерна
# 5. добавить тег это не паттерн который может только дополняться. нужно чтобы предотвратить паразитный свитч
