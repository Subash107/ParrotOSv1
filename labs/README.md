# Lab Scenarios

This directory holds the shared scenario catalog for the lab runner and report generators.

## Layout

- `challenges/`: one JSON file per challenge or vulnerability.
- `profiles/`: named lab profiles that decide which challenges to validate and what result each profile expects.

## Why It Exists

The repo used to duplicate challenge metadata across:

- Windows batch checks
- CI smoke checks
- markdown report generation
- learning scorecard generation

The shared manifests make new challenges easier to add because the capture flow, validation step, and reports can all read the same source of truth.

## Current Workflow

1. `tools/run_lab_scenario.py` captures live evidence or validates an existing report root.
2. The runner writes `summary.json` and `challenge_results.json`.
3. `tools/generate_windows_test_report.py` and `tools/generate_learning_lab_report.py` render markdown from that summary.

## Profile Notes

- `vulnerable.json` represents the intentionally insecure baseline.
- `remediated.json` is a scaffold for future fixed-mode validation.
