"""
Module for collecting and displaying statistics about schemas.
"""

from typing import Dict, Generator, List, Optional

import pytest


class SchemaStats:
    """Class for collecting and displaying statistics about schemas"""

    def __init__(self) -> None:
        self.created: List[str] = []
        self.updated: List[str] = []
        self.updated_diffs: Dict[str, str] = {}  # schema_name -> diff
        self.uncommitted: List[str] = []  # New category for uncommitted changes
        self.uncommitted_diffs: Dict[str, str] = {}  # schema_name -> diff
        self.deleted: List[str] = []
        self.unused: List[str] = []

    def add_created(self, schema_name: str) -> None:
        """Adds created schema"""
        self.created.append(schema_name)

    def add_updated(self, schema_name: str, diff: Optional[str] = None) -> None:
        """Adds updated schema"""
        # Generate diff if both schemas are provided
        if diff and diff.strip():
            self.updated.append(schema_name)
            self.updated_diffs[schema_name] = diff
        else:
            # If schemas are not provided, assume it was an update
            self.updated.append(schema_name)

    def add_uncommitted(self, schema_name: str, diff: Optional[str] = None) -> None:
        """Adds schema with uncommitted changes"""
        # Add only if there are real changes
        if diff and diff.strip():
            self.uncommitted.append(schema_name)
            self.uncommitted_diffs[schema_name] = diff

    def add_deleted(self, schema_name: str) -> None:
        """Adds deleted schema"""
        self.deleted.append(schema_name)

    def add_unused(self, schema_name: str) -> None:
        """Adds unused schema"""
        self.unused.append(schema_name)

    def has_changes(self) -> bool:
        """Returns True if any schema has changes"""
        return bool(self.created or self.updated or self.deleted)

    def has_any_info(self) -> bool:
        """Is there any information about schemas"""
        return bool(self.created or self.updated or self.deleted or self.unused or self.uncommitted)

    def __str__(self) -> str:
        parts = []
        if self.created:
            parts.append(
                f"Created schemas ({len(self.created)}): "
                + ", ".join(f"`{s}`" for s in self.created)
            )
        if self.updated:
            parts.append(
                f"Updated schemas ({len(self.updated)}): "
                + ", ".join(f"`{s}`" for s in self.updated)
            )
        if self.deleted:
            parts.append(
                f"Deleted schemas ({len(self.deleted)}): "
                + ", ".join(f"`{s}`" for s in self.deleted)
            )
        if self.unused:
            parts.append(
                f"Unused schemas ({len(self.unused)}): " + ", ".join(f"`{s}`" for s in self.unused)
            )

        return "\n".join(parts)

    def _iter_schemas(self, names: List[str]) -> Generator[tuple[str, Optional[str]], None, None]:
        """
        Iterates over schema displays: (display, schema_key)
        - display: string to display (may have " + original")
        - schema_key: file name of the schema (<name>.schema.json) to find diffs,
          or None if it's not a schema.
        Preserves the original list order: merging happens at .schema.json
        position; skips .json if paired with schema.
        """
        names = list(names)  # order matters
        schema_sfx = ".schema.json"
        json_sfx = ".json"

        # sets of bases
        # bases_with_schema = {n[: -len(schema_sfx)] for n in names if n.endswith(schema_sfx)}
        bases_with_original = {
            n[: -len(json_sfx)]
            for n in names
            if n.endswith(json_sfx) and not n.endswith(schema_sfx)
        }

        for n in names:
            if n.endswith(schema_sfx):
                base = n[: -len(schema_sfx)]
                if base in bases_with_original:
                    yield f"{n} + original", n  # display, schema_key
                else:
                    yield n, n
            # if .json, skip if paired
            # if other, yield n, n (but assume all are .json or .schema.json)

    def _iter_only_originals(self, names: List[str]) -> Generator[str, None, None]:
        """
        Iterates over only unpaired .json files, in the order they appear.
        """
        names = list(names)  # order matters
        schema_sfx = ".schema.json"
        json_sfx = ".json"

        bases_with_schema = {n[: -len(schema_sfx)] for n in names if n.endswith(schema_sfx)}

        for n in names:
            if n.endswith(json_sfx) and not n.endswith(schema_sfx):
                base = n[: -len(json_sfx)]
                if base not in bases_with_schema:
                    yield n

    def print_summary(self, terminalreporter: pytest.TerminalReporter, update_mode: bool) -> None:
        """
        Prints schema summary to pytest terminal output.
        Pairs of "<name>.schema.json" + "<name>.json" are merged into one line:
        "<name>.schema.json + original" (if original is present).
        Unpaired .json are shown in separate "only originals" sections.
        """

        if not self.has_any_info():
            return

        terminalreporter.write_sep("=", "Schema Summary")

        # Created
        if self.created:
            schemas = list(self._iter_schemas(self.created))
            only_originals = list(self._iter_only_originals(self.created))
            if schemas:
                terminalreporter.write_line(f"Created schemas ({len(schemas)}):", green=True)
                for display, _key in schemas:
                    terminalreporter.write_line(f"  - {display}", green=True)
            if only_originals:
                terminalreporter.write_line(
                    f"Created only originals ({len(only_originals)}):", green=True
                )
                for display in only_originals:
                    terminalreporter.write_line(f"  - {display}", green=True)

        # Updated
        if self.updated:
            schemas = list(self._iter_schemas(self.updated))
            only_originals = list(self._iter_only_originals(self.updated))
            if schemas:
                terminalreporter.write_line(f"Updated schemas ({len(schemas)}):", yellow=True)
                for display, key in schemas:
                    terminalreporter.write_line(f"  - {display}", yellow=True)
                    # Show diff if available for schema
                    if key and key in self.updated_diffs:
                        diff = self.updated_diffs[key]
                        if diff.strip():
                            terminalreporter.write_line("    Changes:", yellow=True)
                            for line in diff.split("\n"):
                                if line.strip():
                                    terminalreporter.write_line(f"      {line}")
                            terminalreporter.write_line("")  # separation
                        else:
                            terminalreporter.write_line(
                                "    (Schema unchanged - no differences detected)", cyan=True
                            )
            if only_originals:
                terminalreporter.write_line(
                    f"Updated only originals ({len(only_originals)}):", yellow=True
                )
                for display in only_originals:
                    terminalreporter.write_line(f"  - {display}", yellow=True)

        # Uncommitted
        if self.uncommitted:
            terminalreporter.write_line(
                f"Uncommitted minor updates ({len(self.uncommitted)}):", bold=True
            )
            for display, key in self._iter_schemas(self.uncommitted):  # assuming mostly schemas
                terminalreporter.write_line(f"  - {display}", cyan=True)
                # Show diff if available
                if key and key in self.uncommitted_diffs:
                    terminalreporter.write_line("    Detected changes:", cyan=True)
                    for line in self.uncommitted_diffs[key].split("\n"):
                        if line.strip():
                            terminalreporter.write_line(f"      {line}")
                    terminalreporter.write_line("")  # separation
            terminalreporter.write_line("Use --schema-update to commit these changes", cyan=True)

        # Deleted
        if self.deleted:
            schemas = list(self._iter_schemas(self.deleted))
            only_originals = list(self._iter_only_originals(self.deleted))
            if schemas:
                terminalreporter.write_line(f"Deleted schemas ({len(schemas)}):", red=True)
                for display, _key in schemas:
                    terminalreporter.write_line(f"  - {display}", red=True)
            if only_originals:
                terminalreporter.write_line(
                    f"Deleted only originals ({len(only_originals)}):", red=True
                )
                for display in only_originals:
                    terminalreporter.write_line(f"  - {display}", red=True)

        # Unused (only if not update_mode)
        if self.unused and not update_mode:
            terminalreporter.write_line(f"Unused schemas ({len(self.unused)}):")
            for display, _key in self._iter_schemas(self.unused):  # assuming schemas
                terminalreporter.write_line(f"  - {display}")
            terminalreporter.write_line("Use --schema-update to delete unused schemas", yellow=True)


GLOBAL_STATS = SchemaStats()
