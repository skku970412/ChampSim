import importlib.util
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[2] / ".github" / "scripts" / "merge_compile_commands.py"
SPEC = importlib.util.spec_from_file_location("merge_compile_commands", SCRIPT_PATH)
merge_compile_commands = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = merge_compile_commands
SPEC.loader.exec_module(merge_compile_commands)


class MergeCompileCommandsTests(unittest.TestCase):
    def run_main(self, args):
        with contextlib.redirect_stderr(io.StringIO()):
            return merge_compile_commands.main(args)

    def make_database(self, root, relative_dir, entries):
        directory = root / relative_dir
        directory.mkdir(parents=True, exist_ok=True)
        database = directory / "compile_commands.json"
        database.write_text(json.dumps(entries), encoding="utf-8")
        return database

    def entry(self, root, relative_dir, file_name, *, arguments=None, command=None):
        entry = {
            "directory": str(root),
            "file": str(root / relative_dir / file_name),
        }
        if arguments is not None:
            entry["arguments"] = arguments
        if command is not None:
            entry["command"] = command
        return entry

    def test_merges_discovered_databases_deterministically(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            beta = self.entry(root, "src", "beta.cc", arguments=["c++", "beta.cc"])
            alpha = self.entry(root, "branch/predictor", "alpha.cc", arguments=["c++", "alpha.cc"])
            self.make_database(root, "src", [beta])
            self.make_database(root, "branch/predictor", [alpha])
            output = root / "compile_commands.json"
            summary = root / "summary.md"

            result = self.run_main(["--root", str(root), "--output", str(output), "--summary", str(summary)])

            self.assertEqual(result, 0)
            merged = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual([entry["file"] for entry in merged], [alpha["file"], beta["file"]])
            self.assertIn("Databases merged: 2", summary.read_text(encoding="utf-8"))
            self.assertIn("Entries written: 2", summary.read_text(encoding="utf-8"))

    def test_explicit_databases_are_supported_and_duplicates_are_removed(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entry = self.entry(root, "custom", "same.cc", arguments=["c++", "same.cc"])
            database = self.make_database(root, "custom", [entry, entry])
            output = root / "out.json"

            result = self.run_main(
                ["--root", str(root), "--compile-commands", str(database), "--output", str(output)]
            )

            self.assertEqual(result, 0)
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))), 1)

    def test_command_field_is_accepted_instead_of_arguments(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entry = self.entry(root, "src", "command.cc", command="c++ command.cc")
            database = self.make_database(root, "src", [entry])
            output = root / "out.json"

            result = self.run_main(
                ["--root", str(root), "--compile-commands", str(database), "--output", str(output)]
            )

            self.assertEqual(result, 0)

    def test_missing_database_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            result = self.run_main(["--root", str(root), "--output", str(root / "out.json")])

            self.assertEqual(result, 1)

    def test_malformed_json_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            directory = root / "src"
            directory.mkdir()
            (directory / "compile_commands.json").write_text("{", encoding="utf-8")

            result = self.run_main(["--root", str(root), "--output", str(root / "out.json")])

            self.assertEqual(result, 1)

    def test_non_list_database_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            self.make_database(root, "src", {"file": "not-a-list"})

            result = self.run_main(["--root", str(root), "--output", str(root / "out.json")])

            self.assertEqual(result, 1)

    def test_entries_require_file_directory_and_command_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bad_entries = [
                {"directory": str(root), "arguments": ["c++"]},
                {"file": str(root / "src" / "x.cc"), "arguments": ["c++"]},
                {"directory": str(root), "file": str(root / "src" / "x.cc")},
                {"directory": str(root), "file": str(root / "src" / "x.cc"), "arguments": ["c++", 5]},
            ]

            for index, entry in enumerate(bad_entries):
                with self.subTest(index=index):
                    case_root = root / str(index)
                    self.make_database(case_root, "src", [entry])
                    result = self.run_main(
                        ["--root", str(case_root), "--output", str(case_root / "out.json")]
                    )
                    self.assertEqual(result, 1)

    def test_non_standard_json_constant_reports_error(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            directory = root / "src"
            directory.mkdir()
            (directory / "compile_commands.json").write_text(
                '[{"directory": ".", "file": "x.cc", "arguments": ["c++"], "extra": NaN}]',
                encoding="utf-8",
            )

            result = self.run_main(["--root", str(root), "--output", str(root / "out.json")])

            self.assertEqual(result, 1)

    def test_summary_escapes_markdown_cells(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            entry = self.entry(root, "src", "pipe.cc", arguments=["c++", "pipe.cc"])
            database = self.make_database(root, "src|pipe", [entry])
            output = root / "out.json"
            summary = root / "summary.md"

            result = self.run_main(
                [
                    "--root",
                    str(root),
                    "--compile-commands",
                    str(database),
                    "--output",
                    str(output),
                    "--summary",
                    str(summary),
                ]
            )

            self.assertEqual(result, 0)
            self.assertIn("src\\|pipe", summary.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
