#!/usr/bin/env python3
"""Generate a markdown report from the shared lab scenario summary."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def load_summary(report_root: Path) -> dict[str, Any]:
    summary_path = report_root / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary file: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def render_services(lines: list[str], services: list[dict[str, Any]]) -> None:
    lines.append("## Service Status")
    lines.append("")
    lines.append("| Service | HTTP Status | Healthy | Evidence |")
    lines.append("| --- | --- | --- | --- |")

    for service in services:
        code = service.get("status_code")
        healthy = "Yes" if service.get("healthy") else "No"
        evidence = ", ".join(f"`{item}`" for item in service.get("evidence", []))
        lines.append(f"| {service.get('name', 'Unknown')} | {code if code is not None else 'n/a'} | {healthy} | {evidence} |")

    lines.append("")


def render_jwt_snapshot(lines: list[str], jwt_payload: dict[str, Any]) -> None:
    lines.append("## JWT Snapshot")
    lines.append("")

    if jwt_payload:
        lines.append("```json")
        lines.append(json.dumps(jwt_payload, indent=2))
        lines.append("```")
    else:
        lines.append("JWT payload could not be decoded from the captured login response.")

    lines.append("")


def render_findings(lines: list[str], findings: list[dict[str, Any]]) -> None:
    lines.append("## Findings")
    lines.append("")

    for finding in findings:
        lines.append(f"### {finding['title']}")
        lines.append("")
        lines.append(f"- Severity: `{finding['severity']}`")
        lines.append(f"- Result: `{finding['result']}`")

        expected_result = finding.get("expected_result")
        if expected_result:
            lines.append(f"- Expected profile result: `{expected_result}`")
            lines.append(f"- Matches profile: `{'Yes' if finding.get('matches_profile') else 'No'}`")

        lines.append(f"- Summary: {finding['summary']}")
        lines.append(f"- Evidence: {', '.join(f'`{item}`' for item in finding.get('evidence', []))}")
        lines.append("")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()

    report_root = Path(args.report_root).resolve()
    summary = load_summary(report_root)

    lines: list[str] = []
    lines.append("# Automated Windows Test Report")
    lines.append("")
    lines.append(f"Generated: `{summary.get('generated_at', 'unknown')}`")
    lines.append(f"Evidence root: `{summary.get('report_root', report_root.as_posix())}`")

    profile = summary.get("profile", {})
    if profile:
        lines.append(f"Profile: `{profile.get('name', profile.get('id', 'unknown'))}`")

    capture = summary.get("capture", {})
    if capture:
        lines.append(f"Capture source: `{capture.get('source', 'unknown')}`")
        lines.append(f"Capture failures: `{capture.get('failures', 0)}`")

    lines.append("")

    render_services(lines, summary.get("services", []))
    render_jwt_snapshot(lines, summary.get("jwt_payload", {}))
    render_findings(lines, summary.get("challenge_results", summary.get("findings", [])))

    lines.append("## Notes")
    lines.append("")
    lines.append("- This report now renders from the shared lab scenario summary instead of duplicating challenge logic in the markdown generator.")
    lines.append("- Use `tools/run_lab_scenario.py` to refresh `summary.json` from a live stack or an existing evidence folder.")

    (report_root / "AUTOMATED_WINDOWS_TEST_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
