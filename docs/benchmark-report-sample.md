# Benchmark Drift Report Sample

This sample was generated from the benchmark comparison tool in
`codex/benchmark-report-tools` using fixture baseline/current JSON data. It
shows the artifact format and verdict behavior; it is not a real ChampSim
benchmark-regression claim.

Generation command:

```sh
python3 tools/bench/compare_benchmark_results.py \
  --baseline test/python/fixtures/benchmark_diff/baseline.json \
  --current test/python/fixtures/benchmark_diff/current.json \
  --output-md benchmark-report-sample.md \
  --output-json benchmark-report-sample.json \
  --sort change
```

## Generated Markdown Output

# Benchmark Drift Report

Benchmarks compared: 8
Thresholds: warn >= 5%, fail >= 10% regression

| Verdict | Count |
| --- | ---: |
| fail | 3 |
| warn | 1 |
| pass | 2 |
| new | 1 |
| missing | 1 |
| error | 0 |

## Worst Regressions

- zeta zero: n/a (1 ns)
- gamma fail: +12.00% (12 ns)
- eta unit conversion: +10.00% (100 ns)
- beta warn: +6.00% (6 ns)

## Details

| Benchmark | Baseline | Current | Unit | Delta | Delta % | Verdict |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| zeta zero | 0 | 1 | ns | 1 | n/a | fail |
| gamma fail | 100 | 112 | ns | 12 | +12.00% | fail |
| eta unit conversion | 1000 | 1100 | ns | 100 | +10.00% | fail |
| beta warn | 100 | 106 | ns | 6 | +6.00% | warn |
| alpha pass | 100 | 103 | ns | 3 | +3.00% | pass |
| delta improves | 100 | 95 | ns | -5 | -5.00% | pass |
| epsilon missing | 50 | n/a | ns | n/a | n/a | missing |
| theta new | n/a | 25 | ns | n/a | n/a | new |
