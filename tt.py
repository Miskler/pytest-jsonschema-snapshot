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
    "email": "john.doe@example.com",
    "created_at": "2025-11-28T14:22:19.123Z",
    "ff": [
        "john.doe@example.com",
        "2025-11-28T14:22:19.123Z",
        "",
        1
    ],
    "birth_date": "1990-05-15",
    "website": "https://example.com/profile/123",
    "ip": "192.168.1.42",
    "tags": ["premium", "beta", "eu"],
    "metadata": {
        "source": "web",
        "referrer": None
    },
    # Псевдо-массив: часто встречается в старых API вместо настоящего массива
    "orders": {
        "0": {"order_id": 1001, "amount": 299.99, "status": "completed", "t": "john.doe@example.com"},
        "1": {"order_id": 1002, "amount": 149.50, "status": "pending", "t": [{"da": [1]}]},
        "3": {"order_id": 1004, "amount": 89.00,  "status": "completed", "t": {"da": [1]}},
        "4": {"order_id": 1004, "amount": 89.00,  "status": "completed", "t": {}},
    },
    # Специально для демонстрации неоднозначного формата
    "mixed_format_field": [
        "2021-01-01",
        "2021-01-01T12:00:00Z",
        "not-a-date"
    ]
}


def demo_mode(mode: str) -> None:
    print(f"\n{'='*60}")
    print(f"Режим format_mode = \"{mode}\"".center(60))
    print(f"{'='*60}")

    converter = JsonToSchemaConverter(format_mode=mode)  # type: ignore[arg-type]
    converter.add_object(SAMPLE_DATA)

    schema = converter.to_schema()

    print(json.dumps(schema, indent=2, ensure_ascii=False))
    print("\nКлючевые моменты:\n")

    if mode == "on":
        print("• format используется для строгой валидации (email, uuid, date-time и т.д.)")
        print("• orders корректно преобразован в объект-массив с patternProperties")
    elif mode == "off":
        print("• Все ключи format полностью отсутствуют в схеме")
    elif mode == "safe":
        print("• format присутствует, но валидация отключена через $vocabulary")
        print("• Поле mixed_format_field имеет локальный format-annotation: true")


if __name__ == "__main__":
    print("Демонстрация JsonToSchemaConverter\n")

    demo_mode("on")
    #demo_mode("off")
    #demo_mode("safe")

    # Дополнительно: только один объект с неоднозначным форматом
    print("\n\n" + "="*60)
    print("Демонстрация локального format-annotation".center(60))
    print("="*60)

    conv = JsonToSchemaConverter(format_mode="on")
    conv.add_object({"values": SAMPLE_DATA["mixed_format_field"]})
    schema_part = conv.to_schema()
    print(json.dumps(schema_part, indent=2, ensure_ascii=False))
    print("\n→ Видно, что для пути #/values включён только format-annotation (без строгого формата)")