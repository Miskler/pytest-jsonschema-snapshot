import json
from pytest_jsonschema_snapshot.tools.genson_addon import JsonToSchemaConverter

def print_schema(title: str, schema: dict) -> None:
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)
    print(json.dumps(schema, indent=2, ensure_ascii=False))
    print("\n")

# Helper to generate a schema from a single object
def generate_single_schema(obj: dict, format_mode: str = "on") -> dict:
    converter = JsonToSchemaConverter(format_mode=format_mode)
    converter.add_object(obj)
    return converter.to_schema()

# Сценарий 1: Форматы у обоих — объединяем в oneOf (демонстрация через генерацию и merge схем)
obj1_sc1 = {"field": "user@example.com"}  # Формат: email
obj2_sc1 = {"field": "2023-10-05"}        # Формат: date

# Генерация отдельных схем
schema1_sc1 = generate_single_schema(obj1_sc1)
schema2_sc1 = generate_single_schema(obj2_sc1)

# Merge схем
converter_sc1 = JsonToSchemaConverter(format_mode="on")
print(JsonToSchemaConverter().STRATEGIES)
print(type(schema1_sc1).__name__)
print(schema1_sc1)
print()
print(schema2_sc1)
converter_sc1.add_schema(schema1_sc1)
converter_sc1.add_schema(schema2_sc1)
merged_schema_sc1 = converter_sc1.to_schema()

print_schema("Сценарий 1: Отдельная генерация (obj1) — ожидается format: 'email'", schema1_sc1)
print_schema("Сценарий 1: Отдельная генерация (obj2) — ожидается format: 'date'", schema2_sc1)
print_schema("Сценарий 1: Merge схем — ожидается oneOf с 'email' и 'date'", merged_schema_sc1)

# Сценарий 2: Формат только у одного, другой тип — сохраняем типы и формат
obj1_sc2 = {"field": "user@example.com"}  # String с email
obj2_sc2 = {"field": 42}                  # Integer

schema1_sc2 = generate_single_schema(obj1_sc2)
schema2_sc2 = generate_single_schema(obj2_sc2)

converter_sc2 = JsonToSchemaConverter(format_mode="on")
converter_sc2.add_schema(schema1_sc2)
converter_sc2.add_schema(schema2_sc2)
merged_schema_sc2 = converter_sc2.to_schema()

print_schema("Сценарий 2: Отдельная генерация (obj1) — string с format: 'email'", schema1_sc2)
print_schema("Сценарий 2: Отдельная генерация (obj2) — integer", schema2_sc2)
print_schema("Сценарий 2: Merge схем — ожидается anyOf/oneOf с string:format='email' и integer", merged_schema_sc2)

# Сценарий 3: Нет формата, но пустая строка — объединяем как в 1
obj1_sc3 = {"field": "user@example.com"}  # Формат: email
obj2_sc3 = {"field": ""}                  # Пустая строка

schema1_sc3 = generate_single_schema(obj1_sc3)
schema2_sc3 = generate_single_schema(obj2_sc3)

converter_sc3 = JsonToSchemaConverter(format_mode="on")
converter_sc3.add_schema(schema1_sc3)
converter_sc3.add_schema(schema2_sc3)
merged_schema_sc3 = converter_sc3.to_schema()

print_schema("Сценарий 3: Отдельная генерация (obj1) — format: 'email'", schema1_sc3)
print_schema("Сценарий 3: Отдельная генерация (obj2) — maxLength: 0", schema2_sc3)
print_schema("Сценарий 3: Merge схем — ожидается oneOf с 'email' и maxLength=0", merged_schema_sc3)

# Сценарий 4: Нет формата и не пустая строка — отбрасываем форматы для string
obj1_sc4 = {"field": "user@example.com"}  # Формат: email
obj2_sc4 = {"field": "plain text"}        # Строка без формата

schema1_sc4 = generate_single_schema(obj1_sc4)
schema2_sc4 = generate_single_schema(obj2_sc4)

converter_sc4 = JsonToSchemaConverter(format_mode="on")
converter_sc4.add_schema(schema1_sc4)
converter_sc4.add_schema(schema2_sc4)
merged_schema_sc4 = converter_sc4.to_schema()

print_schema("Сценарий 4: Отдельная генерация (obj1) — format: 'email'", schema1_sc4)
print_schema("Сценарий 4: Отдельная генерация (obj2) — string без format", schema2_sc4)
print_schema("Сценарий 4: Merge схем — ожидается string без format (отброшен)", merged_schema_sc4)

# Демонстрация для псевдомассивов (основана на текущей реализации; для полных требований нужна CustomObject)
# Пример: Одинаковые псевдомассивы (требование 1) — оставляем как есть
obj1_pseudo = {"pseudo": {"0": "val1", "1": "val2", "2": "val3"}}  # Псевдомассив
obj2_pseudo = {"pseudo": {"3": "val4", "4": "val5", "5": "val6"}}  # Аналогичный

schema1_pseudo = generate_single_schema(obj1_pseudo)
schema2_pseudo = generate_single_schema(obj2_pseudo)

converter_pseudo = JsonToSchemaConverter(format_mode="on")
converter_pseudo.add_schema(schema1_pseudo)
converter_pseudo.add_schema(schema2_pseudo)
merged_pseudo = converter_pseudo.to_schema()

print_schema("Псевдомассивы: Отдельная генерация (obj1) — ожидается patternProperties", schema1_pseudo)
print_schema("Псевдомассивы: Отдельная генерация (obj2) — ожидается patternProperties", schema2_pseudo)
print_schema("Псевдомассивы: Merge схем (требование 1) — ожидается объединенный patternProperties", merged_pseudo)

# Пример с пустым (требование 2/3) — текущая реализация не конвертирует пустой как псевдомассив; после изменений ожидается maxProperties=0 в oneOf
obj3_empty = {"pseudo": {}}  # Пустой dict

schema3_empty = generate_single_schema(obj3_empty)

converter_empty = JsonToSchemaConverter(format_mode="on")
converter_empty.add_schema(schema1_pseudo)  # Псевдомассив
converter_empty.add_schema(schema3_empty)   # Пустой
merged_empty = converter_empty.to_schema()

print_schema("Псевдомассивы: Merge с пустым (текущая реализация) — ожидается object без паттерна; после изменений — oneOf с maxProperties=0", merged_empty)