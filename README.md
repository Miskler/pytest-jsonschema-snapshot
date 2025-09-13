
<div align="center">

# 🔍 Pytest JsonSchema SnapShot (JSSS)

<img src="https://raw.githubusercontent.com/Miskler/pytest-jsonschema-snapshot/refs/heads/main/assets/logo.png" width="70%" alt="logo.png" />

***Plugin for pytest that automatically / manually generates JSON Schemas tests with validates data.***

[![Tests](https://miskler.github.io/pytest-jsonschema-snapshot/tests-badge.svg)](https://miskler.github.io/pytest-jsonschema-snapshot/tests/tests-report.html)
[![Coverage](https://miskler.github.io/pytest-jsonschema-snapshot/coverage.svg)](https://miskler.github.io/pytest-jsonschema-snapshot/coverage/)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](https://python.org)
[![PyPI - Package Version](https://img.shields.io/pypi/v/pytest-jsonschema-snapshot?color=blue)](https://pypi.org/project/pytest-jsonschema-snapshot/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)
[![BlackCode](https://img.shields.io/badge/code%20style-black-black)](https://github.com/psf/black)
[![Imports: isort](https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336)](https://pycqa.github.io/isort/)
[![mypy](https://img.shields.io/badge/type--checked-mypy-blue?logo=python)](https://mypy.readthedocs.io/en/stable/index.html)
[![Discord](https://img.shields.io/discord/792572437292253224?label=Discord&labelColor=%232c2f33&color=%237289da)](https://discord.gg/UnJnGHNbBp)
[![Telegram](https://img.shields.io/badge/Telegram-24A1DE)](https://t.me/miskler_dev)


**[⭐ Star us on GitHub](https://github.com/Miskler/pytest-jsonschema-snapshot)** | **[📚 Read the Docs](https://miskler.github.io/pytest-jsonschema-snapshot/basic/quick_start.html)** | **[🐛 Report Bug](https://github.com/Miskler/pytest-jsonschema-snapshot/issues)**

## ✨ Features

</div>

![image](https://github.com/user-attachments/assets/2faa2548-5af2-4dc9-8d8d-b32db1d87be8)

* Automatic JSON Schema generation from data examples (using the `genson` library).
* **Format detection**: Automatic detection and validation of string formats (email, UUID, date, date-time, URI, IPv4).
* Schema storage and management.
* Validation of data against saved schemas.
* Schema update via `--schema-update` (create new schemas, remove unused ones, update existing).
* Support for both `async` and synchronous functions.
* Support for `Union` types and optional fields.
* Built-in diff comparison of changes via [jsonschema-diff](https://github.com/Miskler/jsonschema-diff).

<div align="center">

## 🚀 Quick Start

</div>

### Installation

```bash
pip install pytest-jsonschema-snapshot
```

### Usage

1. Use the `schemashot` fixture in your tests
  ```python
  from you_lib import API
  from typed_schema_shot import SchemaShot

  @pytest.mark.asyncio
  async def test_something(schemashot: SchemaShot):
      data = await API.get_data()
      # There are data - need to validate through the schema
      schemashot.assert_json_match(
          data, # data for validation / convert to schema
          "test_name"       # name of the schema
      )

      schema = await API.get_schema()
      # There is a schema (data is optional) - validate by what is
      schemashot.assert_schema_match(
          schema,
          (API.get_schema, "test_name", 1) # == `API.get_schema.test_name.1` filename
          data=data # data for validation (optional)
      )
  ```

2. On first run, generate schemas with the `--schema-update` or `--schema-reset` (what is the difference? see the documentation) flag
   ```bash
   pytest --schema-update --save-original
   ```

   **--save-original**: save the original data on which the validation was performed. Saving occurs when `--schema-update` or `--schema-reset`, if you run the schema update without this attribute, the old original data will be deleted without saving new ones.

3. On subsequent runs, tests will validate data against saved schemas
   ```bash
   pytest
   ```

<div align="center">

## 👀 Key Capabilities

</div>

* **Union Types**: support multiple possible types for fields
* **Optional Fields**: automatic detection of required and optional fields
* **Format Detection**: automatic detection of string formats including:

  | Format | Example | JSON Schema |
  | --- | --- | --- |
  | Email | `user@example.com` | `{"format": "email"}` |
  | UUID | `550e8400-e29b-41d4-a716-446655440000` | `{"format": "uuid"}` |
  | Date | `2023-01-15` | `{"format": "date"}` |
  | Date-Time | `2023-01-01T12:00:00Z` | `{"format": "date-time"}` |
  | URI | `https://example.com` | `{"format": "uri"}` |
  | IPv4 | `192.168.1.1` | `{"format": "ipv4"}` |
* **Cleanup**: automatic removal of unused schemas when running in update mode
* **Schema Summary**: colored terminal output showing created, updated, deleted and unused schemas

## Advanced Usage? Check the [docs](https://miskler.github.io/pytest-jsonschema-snapshot/basic/quick_start.html#then-you-need-to-configure-the-library)!

### Best Practices

1. **Commit schemas to version control**: Schemas should be part of your repository
2. **Review schema changes**: When schemas change, review the diffs carefully without `--schema-update` resets.
3. **Clean up regularly**: Use `--schema-update` periodically to remove unused schemas
4. **Descriptive names**: Use clear, descriptive names for your schemas


<div align="center">

## 🤝 Contributing

### ***We welcome contributions!***

### Quick Contribution Setup

</div>

```bash
# Fork the repo, then:
git clone https://github.com/Miskler/pytest-jsonschema-snapshot.git
cd jsonschema-diff
# Install
make reinstall
# Ensure everything works
make test
make lint
make type-check
# After code editing
make format
```

<div align="center">

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

*Made with ❤️ for developers working with evolving JSON schemas*

</div>
