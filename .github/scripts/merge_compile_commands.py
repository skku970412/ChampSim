#!/usr/bin/env python3
"""Merge ChampSim's per-directory compile command databases."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_SEARCH_ROOTS = (
    Path("src"),
    Path("inc"),
    Path("test/cpp/src"),
    Path("branch"),
    Path("btb"),
    Path("prefetcher"),
    Path("replacement"),
)


class CompileCommandMergeError(ValueError):
    """Raised when compile command databases cannot be merged."""


def discover_databases(root: Path, search_roots: list[Path]) -> list[Path]:
    databases: set[Path] = set()
    for search_root in search_roots:
        candidate = (root / search_root).resolve()
        if candidate.exists():
            databases.update(candidate.rglob("compile_commands.json"))
    return sorted(databases, key=lambda path: str(path))


def _read_database(path: Path) -> list[dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"), parse_constant=_reject_json_constant)
    except json.JSONDecodeError as exc:
        raise CompileCommandMergeError(f"{path} is not valid JSON: {exc}") from exc
    except ValueError as exc:
        raise CompileCommandMergeError(f"{path} is not valid JSON: {exc}") from exc
    except OSError as exc:
        raise CompileCommandMergeError(f"could not read {path}: {exc}") from exc

    if not isinstance(data, list):
        raise CompileCommandMergeError(f"{path} must contain a JSON list")

    entries: list[dict[str, Any]] = []
    for index, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise CompileCommandMergeError(f"{path} entry {index} must be an object")

        file_name = entry.get("file")
        directory = entry.get("directory")
        has_command = isinstance(entry.get("command"), str) and bool(entry["command"].strip())
        has_arguments = isinstance(entry.get("arguments"), list) and bool(entry["arguments"])

        if not isinstance(file_name, str) or not file_name.strip():
            raise CompileCommandMergeError(f"{path} entry {index} is missing a non-empty file field")
        if not isinstance(directory, str) or not directory.strip():
            raise CompileCommandMergeError(f"{path} entry {index} is missing a non-empty directory field")
        if not has_command and not has_arguments:
            raise CompileCommandMergeError(f"{path} entry {index} is missing command or arguments")
        if has_arguments and not all(isinstance(argument, str) for argument in entry["arguments"]):
            raise CompileCommandMergeError(f"{path} entry {index} arguments must be strings")

        entries.append(entry)

    return entries


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant {value!r}")


def merge_databases(databases: list[Path]) -> list[dict[str, Any]]:
    if not databases:
        raise CompileCommandMergeError("no compile_commands.json files found")

    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for database in databases:
        for entry in _read_database(database):
            key = json.dumps(entry, sort_keys=True, separators=(",", ":"))
            if key in seen:
                continue
            seen.add(key)
            merged.append(entry)

    if not merged:
        raise CompileCommandMergeError("compile command databases did not contain any entries")

    return sorted(merged, key=lambda entry: (entry["file"], entry["directory"], json.dumps(entry, sort_keys=True)))


def write_json(entries: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(entries, allow_nan=False, indent=2) + "\n", encoding="utf-8")


def _markdown_cell(value: object) -> str:
    return str(value).replace("\\", "\\\\").replace("\r", " ").replace("\n", " ").replace("\t", " ").replace("|", "\\|")


def write_summary(databases: list[Path], entries: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# compile_commands Summary",
        "",
        f"Databases merged: {len(databases)}",
        f"Entries written: {len(entries)}",
        "",
        "| Database |",
        "| --- |",
    ]
    lines.extend(f"| {_markdown_cell(database)} |" for database in databases)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Merge ChampSim compile_commands.json files into one root database.")
    parser.add_argument("--root", default=Path("."), type=Path, help="Repository root.")
    parser.add_argument("--output", required=True, type=Path, help="Merged compile_commands.json output path.")
    parser.add_argument("--summary", type=Path, help="Optional Markdown summary path.")
    parser.add_argument(
        "--search-root",
        action="append",
        type=Path,
        help="Directory to search recursively for compile_commands.json. May be repeated.",
    )
    parser.add_argument(
        "--compile-commands",
        action="append",
        type=Path,
        help="Explicit compile_commands.json path. May be repeated.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    root = args.root.resolve()

    try:
        databases = args.compile_commands or discover_databases(root, args.search_root or list(DEFAULT_SEARCH_ROOTS))
        databases = sorted(
            [(database if database.is_absolute() else root / database).resolve() for database in databases],
            key=lambda path: str(path),
        )
        entries = merge_databases(databases)
        write_json(entries, args.output)
        if args.summary is not None:
            write_summary(databases, entries, args.summary)
    except CompileCommandMergeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
