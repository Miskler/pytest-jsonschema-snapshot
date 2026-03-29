"""
Core logic of the plugin.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Literal, Optional

import pathvalidate

if TYPE_CHECKING:
    from jsonschema_diff import JsonSchemaDiff

import pytest
from genschema import Converter, PseudoArrayHandler
from genschema.comparators import (
    DeleteElement,
    EmptyComparator,
    EnumComparator,
    FormatComparator,
    RequiredComparator,
    SchemaVersionComparator,
)
from genschema.postprocessing import (
    SchemaReferenceExtractionConfig,
    SchemaReferencePostprocessor,
)
from jsonschema import FormatChecker, ValidationError, validate

from .stats import GLOBAL_STATS
from .tools import NameMaker


class SchemaShot:
    def __init__(
        self,
        root_dir: Path,
        differ: "JsonSchemaDiff",
        callable_regex: str = "{class_method=.}",
        format_mode: str = "on",
        update_mode: bool = False,
        ci_cd_mode: bool = False,
        reset_mode: bool = False,
        update_actions: Optional[dict[str, bool]] = {},
        save_original: bool = False,
        debug_mode: bool = False,
        snapshot_dir_name: str = "__snapshots__",
    ):
        """
        Initializes SchemaShot.

        Args:
            root_dir: Project root directory
            update_mode: Update mode (--schema-update)
            snapshot_dir_name: Name of the directory for snapshots
        """
        self.root_dir: Path = root_dir
        self.differ: "JsonSchemaDiff" = differ
        self.callable_regex: str = callable_regex
        self.format_mode: str = format_mode.lower()
        self.ci_cd_mode: bool = ci_cd_mode
        # self.examples_limit: int = examples_limit
        self.update_mode: bool = update_mode
        self.reset_mode: bool = reset_mode
        self.update_actions: dict[str, bool] = dict(update_actions or {})
        self.save_original: bool = save_original
        self.debug_mode: bool = debug_mode
        self.snapshot_dir: Path = root_dir / snapshot_dir_name
        self.used_schemas: set[str] = set()

        if self.format_mode not in {"on", "safe", "off"}:
            raise ValueError(
                "Invalid jsss_format_mode value. Expected one of: 'on', 'safe', 'off'."
            )

        self.conv = Converter(
            pseudo_handler=PseudoArrayHandler(),
            base_of="anyOf",
        )
        if self._is_format_annotation_enabled():
            self.conv.register(FormatComparator())
        self.conv.register(EnumComparator())
        self.conv.register(RequiredComparator())
        # self.conv.register(EmptyComparator())
        self.conv.register(SchemaVersionComparator())
        self.conv.register(DeleteElement())
        self.conv.register(DeleteElement("isPseudoArray"))
        self.reference_extraction_config = SchemaReferenceExtractionConfig(
            merge_base_of="anyOf",
            merge_pseudo_handler=PseudoArrayHandler(),
            merge_comparator_factories=self._make_reference_extraction_comparator_factories(),
        )

        self.logger = logging.getLogger(__name__)
        # добавляем вывод в stderr
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
        self.logger.addHandler(handler)
        # и поднимаем уровень, чтобы INFO/DEBUG прошли через handler
        self.logger.setLevel(logging.INFO)

        # Создаем директорию для снэпшотов, если её нет
        if not self.snapshot_dir.exists():
            self.snapshot_dir.mkdir(parents=True)
        cicd = self.snapshot_dir / "ci.cd"
        if cicd.exists():
            shutil.rmtree(cicd)
        cicd.mkdir(parents=True)

    def _is_format_annotation_enabled(self) -> bool:
        return self.format_mode in {"on", "safe"}

    def _is_format_validation_enabled(self) -> bool:
        return self.format_mode == "on"

    def _make_reference_extraction_comparator_factories(self) -> tuple[Callable[[], Any], ...]:
        factories: list[Callable[[], Any]] = []
        if self._is_format_annotation_enabled():
            factories.append(FormatComparator)
        factories.extend(
            (
                EnumComparator,
                RequiredComparator,
                EmptyComparator,
                DeleteElement,
                lambda: DeleteElement("isPseudoArray"),
            )
        )
        return tuple(factories)

    def _finalize_generated_schema(self, schema: dict[str, Any]) -> dict[str, Any]:
        return SchemaReferencePostprocessor.process(schema, self.reference_extraction_config)

    def _validate_instance(self, instance: Any, schema: dict[str, Any]) -> None:
        validate_kwargs: dict[str, Any] = {}
        if self._is_format_validation_enabled():
            validate_kwargs["format_checker"] = FormatChecker()
        validate(instance=instance, schema=schema, **validate_kwargs)

    def _process_name(self, name: str | int | Callable | list[str | int | Callable]) -> str:
        """
        1. Converts callable to string
        2. Checks for validity

        Returns:
            str
        Raises:
            ValueError
        """

        __tracebackhide__ = not self.debug_mode  # прячем из стека pytest

        def process_name_part(part: str | int | Callable) -> str:
            if callable(part):
                return NameMaker.format(part, self.callable_regex)
            else:
                return str(part)

        if isinstance(name, (list, tuple)):
            name = ".".join([process_name_part(part) for part in name])
        else:
            name = process_name_part(name)

        if not isinstance(name, str) or not name:
            raise ValueError("Schema name must be a non-empty string")

        try:
            # auto подберёт правила под текущую ОС
            pathvalidate.validate_filename(
                name, platform="auto"
            )  # allow_reserved=False по умолчанию
        except pathvalidate.ValidationError as e:
            raise ValueError(f"Invalid schema name: {e}") from None

        return name

    def _save_process_original(self, real_name: str, status: Optional[bool], data: dict) -> None:
        json_name = f"{real_name}.json"
        schema_name = f"{real_name}.schema.json"
        base_j_path = self.snapshot_dir / json_name
        base_s_path = self.snapshot_dir / json_name
        if not self.ci_cd_mode:
            json_path = base_j_path
            schema_path = base_s_path
        else:
            json_path = self.snapshot_dir / "ci.cd" / json_name
            schema_path = self.snapshot_dir / "ci.cd" / schema_name

        if self.save_original:
            available_to_create = (
                (not json_path.exists() or status is None) and not self.ci_cd_mode
            ) or (schema_path.exists() and not base_s_path.exists() and self.ci_cd_mode)
            available_to_update = (status is True and not self.ci_cd_mode) or (
                schema_path.exists() and base_s_path.exists() and self.ci_cd_mode
            )

            if (available_to_create and self.update_actions.get("add")) or (
                available_to_update and self.update_actions.get("update")
            ):
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)

                if available_to_create:
                    GLOBAL_STATS.add_created(json_name)
                elif available_to_update:
                    GLOBAL_STATS.add_updated(json_name)
                else:
                    raise ValueError(f"Unexpected status: {status}")
        elif not self.ci_cd_mode and json_path.exists() and self.update_actions.get("delete"):
            # удаляем
            json_path.unlink()
            GLOBAL_STATS.add_deleted(json_name)

    def assert_json_match(
        self,
        data: dict,
        name: str | int | Callable | list[str | int | Callable],
    ) -> Optional[bool]:
        """
        Asserts for JSON, converts it to schema and then compares.

        Returns:
            True  – the schema has been updated,
            False – the schema has not changed,
            None  – a new schema has been created.
        """

        real_name = self._process_name(name)

        real_name, status = self._base_match(data, data, "json", real_name)

        if self.update_mode or self.reset_mode or self.ci_cd_mode:
            self._save_process_original(real_name=real_name, status=status, data=data)

        return status

    def assert_schema_match(
        self,
        schema: dict[str, Any],
        name: str | int | Callable | list[str | int | Callable],
        *,
        data: Optional[dict] = None,
    ) -> Optional[bool]:
        """
        Accepts a JSON-schema directly and compares it immediately.

        Returns:
            True  – the schema has been updated,
            False – the schema has not changed,
            None  – a new schema has been created.
        """

        real_name = self._process_name(name)

        real_name, status = self._base_match(data, schema, "schema", real_name)

        if self.update_mode and data is not None:
            self._save_process_original(real_name=real_name, status=status, data=data)

        return status

    def _base_match(
        self,
        data: Optional[dict],
        current_data: dict,
        type_data: Literal["json", "schema"],
        name: str,
    ) -> tuple[str, Optional[bool]]:
        """
        Checks if data matches the JSON schema, creates/updates it if needed,
        and writes statistics to GLOBAL_STATS.

        Returns:
            True  – the schema has been updated,
            False – the schema has not changed,
            None  – a new schema has been created.
        """
        __tracebackhide__ = not self.debug_mode  # прячем из стека pytest

        # Проверка имени
        name = self._process_name(name)

        base_path = self.snapshot_dir / f"{name}.schema.json"
        if not self.ci_cd_mode:
            schema_path = base_path
        else:
            schema_path = self.snapshot_dir / "ci.cd" / f"{name}.schema.json"
        self.used_schemas.add(schema_path.name)

        # --- состояние ДО проверки ---
        schema_exists_before = base_path.exists()

        def make_schema(current_data: dict | list, type_data: Literal["json", "schema"]) -> dict:
            if type_data == "schema":
                return dict(current_data)
            elif type_data == "json":
                self.conv.clear_data()
                self.conv.add_json(current_data)
                return self._finalize_generated_schema(self.conv.run())
            else:
                raise ValueError("Not correct type argument")

        # --- когда схемы ещё нет ---
        if not schema_exists_before:
            if not self.update_mode and not self.reset_mode and not self.ci_cd_mode:
                raise pytest.fail.Exception(
                    f"Schema `{name}` not found."
                    "Run the test with the --schema-update option to create it."
                )
            elif not self.update_actions.get("add"):
                raise pytest.fail.Exception(
                    f"Schema `{name}` not found and adding new schemas is disabled."
                )

            current_schema = make_schema(current_data, type_data)

            with open(schema_path, "w", encoding="utf-8") as f:
                json.dump(current_schema, f, indent=2, ensure_ascii=False)

            self.logger.info(f"New schema `{name}` has been created.")
            GLOBAL_STATS.add_created(schema_path.name)  # статистика «создана»
            return name, None
        else:
            with open(base_path, "r", encoding="utf-8") as f:
                existing_schema = json.load(f)

            # --- схема уже была: сравнение и валидация --------------------------------
            schema_updated = False

            def merge_schemas(
                old: dict, new: dict | list, type_data: Literal["json", "schema"]
            ) -> dict:
                self.conv.clear_data()
                self.conv.add_schema(old)
                if type_data == "schema":
                    self.conv.add_schema(dict(new))
                elif type_data == "json":
                    self.conv.add_json(new)
                else:
                    raise ValueError("Not correct type argument")
                result = self.conv.run()
                if type_data == "json":
                    result = self._finalize_generated_schema(result)
                return result

            if (
                type_data == "json" or existing_schema != current_data
            ):  # есть отличия или могут быть
                if (
                    self.update_mode or self.ci_cd_mode or self.reset_mode
                ) and self.update_actions.get("update"):
                    # обновляем файл
                    if self.reset_mode and not self.update_mode and not self.ci_cd_mode:
                        current_schema = make_schema(current_data, type_data)

                        if existing_schema != current_schema:
                            differences = self.differ.compare(
                                dict(existing_schema), current_schema
                            ).render()
                            GLOBAL_STATS.add_updated(schema_path.name, differences)

                            with open(schema_path, "w", encoding="utf-8") as f:
                                json.dump(current_schema, f, indent=2, ensure_ascii=False)
                            self.logger.warning(f"Schema `{name}` reseted.\n\n{differences}")
                    elif self.update_mode or self.ci_cd_mode and not self.reset_mode:
                        merged_schema = merge_schemas(existing_schema, current_data, type_data)

                        if existing_schema != merged_schema:
                            differences = self.differ.compare(
                                dict(existing_schema), merged_schema
                            ).render()
                            GLOBAL_STATS.add_updated(schema_path.name, differences)

                            with open(schema_path, "w", encoding="utf-8") as f:
                                json.dump(merged_schema, f, indent=2, ensure_ascii=False)

                            self.logger.warning(f"Schema `{name}` updated.\n\n{differences}")
                    else:  # both update_mode and reset_mode are True
                        raise ValueError(
                            "update_mode, ci_cd_mode and reset_mode"
                            " cannot be True at the same time."
                        )
                    schema_updated = True
                elif data is not None:
                    merged_schema = merge_schemas(existing_schema, current_data, type_data)

                    differences = ""
                    if existing_schema != merged_schema:
                        differences = self.differ.compare(
                            dict(existing_schema), merged_schema
                        ).render()
                        GLOBAL_STATS.add_uncommitted(schema_path.name, differences)

                    # только валидируем по старой схеме
                    try:
                        self._validate_instance(instance=data, schema=existing_schema)
                    except ValidationError as e:
                        pytest.fail(
                            f"\n\n{differences}\n\nValidation error in `{name}`: {e.message}"
                        )
            elif data is not None and type_data == "schema":
                # схемы совпали – всё равно валидируем на случай формальных ошибок
                try:
                    self._validate_instance(instance=data, schema=existing_schema)
                except ValidationError as e:
                    merged_schema = merge_schemas(existing_schema, current_data, type_data)

                    differences = ""
                    if existing_schema != merged_schema:
                        differences = self.differ.compare(
                            dict(existing_schema), merged_schema
                        ).render()
                    pytest.fail(f"\n\n{differences}\n\nValidation error in `{name}`: {e.message}")

            return name, schema_updated
