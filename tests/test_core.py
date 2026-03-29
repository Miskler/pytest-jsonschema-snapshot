from pathlib import Path

from jsonschema_diff import ConfigMaker, JsonSchemaDiff
from jsonschema_diff.color import HighlighterPipeline
from jsonschema_diff.color.stages import (
    MonoLinesHighlighter,
    PathHighlighter,
    ReplaceGenericHighlighter,
)

import pytest_jsonschema_snapshot.core as core_module
from pytest_jsonschema_snapshot.core import SchemaShot


def make_differ() -> JsonSchemaDiff:
    return JsonSchemaDiff(
        ConfigMaker.make(),
        HighlighterPipeline(
            [MonoLinesHighlighter(), PathHighlighter(), ReplaceGenericHighlighter()]
        ),
    )


def test_constructor_does_not_touch_cicd_dir_when_disabled(tmp_path: Path, monkeypatch) -> None:
    cicd = tmp_path / "__snapshots__" / "ci.cd"
    cicd.mkdir(parents=True)

    def fail_rmtree(*args, **kwargs):
        raise AssertionError("ci.cd must not be removed outside CI/CD mode")

    monkeypatch.setattr(core_module.shutil, "rmtree", fail_rmtree)

    SchemaShot(root_dir=tmp_path, differ=make_differ(), ci_cd_mode=False)

    assert cicd.exists()


def test_constructor_recreates_cicd_dir_when_enabled(tmp_path: Path) -> None:
    cicd = tmp_path / "__snapshots__" / "ci.cd"
    cicd.mkdir(parents=True)
    (cicd / "stale.schema.json").write_text("{}", encoding="utf-8")

    SchemaShot(root_dir=tmp_path, differ=make_differ(), ci_cd_mode=True)

    assert cicd.exists()
    assert list(cicd.iterdir()) == []
