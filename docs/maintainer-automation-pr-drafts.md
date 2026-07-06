# Maintainer Automation PR Drafts

These drafts are for converting the fork branches into upstream PRs or issue
comments. They intentionally describe fork-only work as fork-only work.

## Issue #590 Comment Draft

Hi, I'd like to take a first pass at this.

My proposed first PR is intentionally small and non-invasive: discover the
existing Catch2 benchmark output path, add fixture-tested normalization for the
benchmark results, and emit Markdown/JSON reports that can be uploaded as CI
artifacts. I would avoid changing simulator behavior and avoid PR comments in
the first PR.

If that direction looks useful, follow-ups could add baseline-vs-current
comparison, configurable drift thresholds, and optional history publishing.

Would this be a reasonable starting point for #590?

## Benchmark Reporting PR

Suggested title:

```text
tools: add benchmark reporting utilities
```

Suggested description:

```markdown
## Summary
- Add a Catch2 XML benchmark normalizer that writes stable JSON and Markdown.
- Add a normalized baseline/current benchmark comparison tool.
- Add a manual benchmark report workflow that uploads artifacts.
- Harden the manual workflow with explicit dependency setup, benchmark
  diagnostics, strict XML validation, and strict artifact checks.
- Document the local and CI benchmark reporting flow.

## Motivation
Issue #590 asks for a way to track benchmark history and PR performance drift.
The first step is to make benchmark output durable and machine-readable without
changing simulator behavior.

## What changed
- Added `tools/bench/normalize_catch2_benchmarks.py`.
- Added `tools/bench/compare_benchmark_results.py`.
- Added fixture-based Python tests for valid, malformed, duplicate, unit,
  threshold, zero-baseline, Markdown, and JSON edge cases.
- Added `.github/workflows/benchmark-report.yml` as a manual, artifact-only
  workflow.
- Added workflow diagnostics for Catch2 reporters, test discovery, benchmark
  declaration discovery, and generated XML validation.
- Added `docs/src/Benchmark-reporting.rst`.

## Out of scope
- No simulator behavior changes.
- No automatic PR comments.
- No benchmark history publishing.
- No default CI gating on benchmark drift.

## Verification
- [x] `python3 -m compileall tools/bench/normalize_catch2_benchmarks.py tools/bench/compare_benchmark_results.py test/python/test_benchmark_normalizer.py test/python/test_benchmark_diff.py`
- [x] `python3 -m unittest discover -v --start-directory test/python --pattern 'test_benchmark*.py'`
- [x] `python3 -m unittest discover -v --start-directory test/python`
- [x] `make pytest`
- [x] `vcpkg/bootstrap-vcpkg.sh`
- [x] `vcpkg/vcpkg install`
- [x] `./config.sh`
- [x] `make test/bin/000-test-main`
- [x] `test/bin/000-test-main --order rand --warn NoAssertions --invisibles`
- [x] `test/bin/000-test-main --list-reporters`
- [x] `test/bin/000-test-main --list-tests`
- [x] `grep -R "BENCHMARK" -n test/cpp src inc || true`
- [x] Generated Catch2 XML contained `BenchmarkResults`.
- [x] Catch2 XML benchmark output normalized successfully from a real XML run with 9 benchmarks.
- [x] Self-compare with `--fail-on-regression` passed with 9 pass, 0 warn, and 0 fail.
- [x] Comparator fixture output JSON validated with `python3 -m json.tool`.
- [x] Sphinx docs build succeeded with existing Doxygen/BibTeX warnings.
- [x] Benchmark workflow YAML parsed successfully.
- [x] `git diff --check`
- [ ] `actionlint` - skipped because it was not installed locally.
- [ ] GitHub Actions manual workflow run - not runnable yet because GitHub only dispatches `workflow_dispatch` workflows after the workflow file exists on the repository default branch.

## Follow-ups
- Add optional PR comments after maintainers choose a comment update policy.
- Add benchmark history publishing after maintainers choose storage and retention.
- Decide whether drift thresholds should ever fail CI.
```

## Clang-Tidy Artifact PR

Suggested title:

```text
ci: add clang-tidy report artifact workflow
```

Suggested description:

```markdown
## Summary
- Add a pull-request clang-tidy workflow for changed C++ lines.
- Merge ChampSim's per-directory `compile_commands.json` files into a root
  database for clang-tidy.
- Upload artifact-only clang-tidy reports without posting PR comments.
- Remove an obsolete `.clang-tidy` key that clang-tidy-18 rejects.

## Motivation
Issue #591 asks for clang-tidy suggestions during PR review. This keeps the
first pass low-permission and artifact-only while still making diagnostics
available to maintainers.

## What changed
- Added `.github/workflows/clang-tidy-report.yml`.
- Added `.github/scripts/merge_compile_commands.py`.
- Added tests for deterministic merge behavior and malformed compile databases.
- Kept `permissions: contents: read` and avoided `pull_request_target`.

## Out of scope
- No PR comments.
- No write permissions.
- No whole-matrix clang-tidy job.
- No CI failure on clang-tidy diagnostics in the first pass.

## Verification
- [x] `python3 -m compileall .github/scripts/merge_compile_commands.py test/python/test_merge_compile_commands.py`
- [x] `python3 -m unittest discover -v --start-directory test/python --pattern 'test_merge_compile_commands.py'`
- [x] `python3 -m unittest discover -v --start-directory test/python`
- [x] `./config.sh`
- [x] `make absolute.options compile_commands`
- [x] `python3 .github/scripts/merge_compile_commands.py --output /tmp/champsim-merged-compile-commands.json --summary /tmp/champsim-compile-commands-summary.md`
- [x] `python3 -m json.tool /tmp/champsim-merged-compile-commands.json`
- [x] `clang-tidy-18 --verify-config`
- [x] `clang-tidy-18 -p src src/address.cc --quiet`
- [x] `clang-tidy-diff.py` no-change smoke check.
- [x] `clang-tidy-diff.py` synthetic diff smoke check.
- [x] `make test/bin/000-test-main`
- [x] `test/bin/000-test-main --order rand --warn NoAssertions --invisibles`
- [x] workflow YAML parsed successfully.
- [x] `git diff --check`
- [ ] `actionlint` - skipped because it was not installed locally.

## Follow-ups
- Let maintainers decide whether diagnostics should later become review
  comments.
- Add tighter changed-file filtering if maintainers want fewer artifacts.
- Consider failing only on selected checks after baseline noise is understood.
```

## CPI Stack Listener Design PR

Suggested title:

```text
docs: outline CPI stack listener design
```

Suggested description:

```markdown
## Summary
- Add a design note for issue #647.
- Propose stage-sample events, reason vocabulary, output schema, and staged PR
  slices for CPI stack listeners.

## Motivation
CPI stacks help explain which pipeline bottlenecks contribute to observed CPI.
A design note lets maintainers review event shape and attribution limits before
core-model instrumentation is added.

## Out of scope
- No simulator behavior changes.
- No new listener implementation.
- No CI integration yet.

## Verification
- [x] `git diff --check`
- [x] Sphinx docs build succeeded with existing Doxygen/BibTeX warnings.

## Follow-ups
- Add event types and a no-op listener.
- Add dispatch attribution first.
- Add issue/retire attribution after the reason priority is agreed.
```

## Performance Debug Listener Design PR

Suggested title:

```text
docs: outline performance debug listener design
```

Suggested description:

```markdown
## Summary
- Add a design note for issue #648.
- Propose filtered per-instruction delay samples, output schema, accuracy
  limits, and staged implementation slices.

## Motivation
Issue #648 describes the difficulty of explaining why a specific instruction is
delayed at a specific stage. A design note keeps the first review focused on
the event model and filtering requirements.

## Out of scope
- No simulator behavior changes.
- No listener implementation.
- No command-line filter plumbing yet.

## Verification
- [x] `git diff --check`
- [x] Sphinx docs build succeeded with existing Doxygen/BibTeX warnings.

## Follow-ups
- Add listener registration and filter configuration.
- Emit dispatch/retire snapshots first.
- Add execute and LSQ reasons after the snapshot schema is stable.
```
