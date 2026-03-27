#!/usr/bin/env python3
"""Generate reward-style learning assets from a shared scenario summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASELINE_POINTS = 50
BASELINE_FLAG = "ACME{lab_online_baseline}"


def load_summary(report_root: Path) -> dict[str, Any]:
    summary_path = report_root / "summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def all_challenges(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return summary.get("challenge_results", [])


def vulnerable_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [finding for finding in all_challenges(summary) if finding.get("result") == "Vulnerable"]


def score_summary(summary: dict[str, Any]) -> tuple[int, int, list[dict[str, Any]], dict[str, int]]:
    services = summary.get("services", [])
    healthy_services = all(service.get("healthy") for service in services)

    completed = vulnerable_findings(summary)
    track_scores: dict[str, int] = {}
    total_points = BASELINE_POINTS if healthy_services else 0
    max_points = BASELINE_POINTS + sum(int(item.get("points", 0)) for item in all_challenges(summary))

    for finding in completed:
        points = int(finding.get("points", 0))
        total_points += points
        track = str(finding.get("track", "Uncategorized"))
        track_scores[track] = track_scores.get(track, 0) + points

    if healthy_services:
        track_scores["Baseline"] = BASELINE_POINTS

    return total_points, max_points, completed, track_scores


def render_scorecard(
    report_root: Path,
    summary: dict[str, Any],
    total_points: int,
    max_points: int,
    completed: list[dict[str, Any]],
    track_scores: dict[str, int],
) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    completed_titles = {item["title"] for item in completed}

    lines: list[str] = []
    lines.append("# Bug Bounty Rewards Lab Scorecard")
    lines.append("")
    lines.append(f"Generated: `{generated_at}`")
    lines.append(f"Score: `{total_points}/{max_points}`")
    lines.append("")
    lines.append("This is a training scorecard for local practice. It is not a real payout program.")
    lines.append("")
    lines.append("## Track Scores")
    lines.append("")
    lines.append("| Track | Points Earned |")
    lines.append("| --- | --- |")

    for track, points in sorted(track_scores.items()):
        lines.append(f"| {track} | {points} |")

    lines.append("")
    lines.append("## Challenge Board")
    lines.append("")
    lines.append("| Challenge | Level | Track | Reward | Points | Status |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    lines.append(f"| Lab baseline online | Beginner | Baseline | Ready To Hunt | {BASELINE_POINTS} | {'Earned' if track_scores.get('Baseline') else 'Pending'} |")

    for finding in all_challenges(summary):
        status = "Earned" if finding["title"] in completed_titles else "Pending"
        lines.append(
            f"| {finding['title']} | {finding['level']} | {finding['track']} | "
            f"{finding['reward']} | {finding['points']} | {status} |"
        )

    lines.append("")
    lines.append("## Level Map")
    lines.append("")
    lines.append("| Level | What it means in this lab |")
    lines.append("| --- | --- |")
    lines.append("| Beginner | Direct endpoint or browser proof with minimal request changes |")
    lines.append("| Intermediate | Requires parameter tampering, header changes, token review, or persistent injection validation |")
    lines.append("| Advanced | Requires chaining multiple issues or forging deeper privilege escalation paths manually |")
    lines.append("")
    lines.append("## Flags Earned")
    lines.append("")

    if track_scores.get("Baseline"):
        lines.append(f"- `{BASELINE_FLAG}` from `Lab baseline online`")

    if completed:
        for item in completed:
            lines.append(f"- `{item['flag']}` from `{item['title']}`")
    if not completed and not track_scores.get("Baseline"):
        lines.append("- No flags earned yet.")

    lines.append("")
    lines.append("## Next Learning Moves")
    lines.append("")

    if len(completed) == len(all_challenges(summary)):
        lines.append("- You completed the full local reward lab path. Next step: reproduce each finding manually with Burp or ZAP and write your own report from scratch.")
        lines.append("- Try the advanced bonus path: forge an admin JWT manually and access /api/admin as a chained exploit.")
    else:
        lines.append("- Re-run the remaining manual checks and compare your own screenshots with the raw evidence in this run folder.")
        lines.append("- Practice rewriting each confirmed finding in HackerOne and Bugcrowd format.")

    lines.append("- Use the generated bug bounty report as a reference, then try producing your own cleaned-up version without automation.")

    (report_root / "LAB_REWARD_SCORECARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_walkthrough_flags(report_root: Path, completed: list[dict[str, Any]], baseline_earned: bool, summary: dict[str, Any]) -> None:
    completed_titles = {item["title"] for item in completed}

    lines: list[str] = []
    lines.append("# Walkthrough Flags")
    lines.append("")
    lines.append("These are private training flags for the local lab. Earn a flag only after you reproduce the issue yourself.")
    lines.append("")
    lines.append("| Challenge | Level | Flag | Status |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(f"| Lab baseline online | Beginner | `{BASELINE_FLAG}` | {'Earned' if baseline_earned else 'Locked'} |")

    for finding in all_challenges(summary):
        status = "Earned" if finding["title"] in completed_titles else "Locked"
        lines.append(f"| {finding['title']} | {finding['level']} | `{finding['flag']}` | {status} |")

    lines.append("")
    lines.append("## Hint Ladders")
    lines.append("")

    for finding in all_challenges(summary):
        lines.append(f"### {finding['title']}")
        lines.append("")
        lines.append(f"- Level: `{finding['level']}`")
        lines.append(f"- Flag: `{finding['flag']}`")
        for index, hint in enumerate(finding.get("hint_ladder", []), start=1):
            lines.append(f"- Hint {index}: {hint}")
        lines.append("")

    lines.append("## Advanced Bonus Flags")
    lines.append("")
    lines.append("- `ACME{jwt_forgery_to_admin_api}`")
    lines.append("  Earn this by forging an admin JWT with the weak secret and successfully calling `/api/admin`.")
    lines.append("- `ACME{comment_xss_to_session_theft_path}`")
    lines.append("  Earn this by proving the stored XSS can be chained to the readable `session` cookie in a safe local demo.")

    (report_root / "WALKTHROUGH_FLAGS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_bug_bounty_report(
    report_root: Path,
    summary: dict[str, Any],
    completed: list[dict[str, Any]],
    total_points: int,
) -> None:
    scope = [
        "http://app.acme.local:8080",
        "http://api.acme.local:8081",
        "http://admin.acme.local:8082",
        "http://storage.acme.local:9000",
        "http://storage.acme.local:9001",
    ]

    lines: list[str] = []
    lines.append("# Filled Bug Bounty Learning Report")
    lines.append("")
    lines.append("This report is generated from the local training lab evidence and is intended for learning how to structure bug bounty findings.")
    lines.append("")
    lines.append(f"Overall training score: `{total_points}`")
    lines.append("")
    lines.append("## Scope")
    lines.append("")

    for item in scope:
        lines.append(f"- `{item}`")

    lines.append("")
    lines.append("## Confirmed Findings")
    lines.append("")
    lines.append("| Title | Severity | Track | Reward |")
    lines.append("| --- | --- | --- | --- |")

    for finding in completed:
        lines.append(f"| {finding['title']} | {finding['severity']} | {finding['track']} | {finding['reward']} |")

    lines.append("")

    for finding in completed:
        lines.append(f"## {finding['title']}")
        lines.append("")
        lines.append(f"**Severity:** {finding['severity']}")
        lines.append("")
        lines.append(f"**Level:** {finding['level']}")
        lines.append("")
        lines.append(f"**Training flag:** `{finding['flag']}`")
        lines.append("")
        lines.append(f"**Why it matters:** {finding['why_it_matters']}")
        lines.append("")
        lines.append("**Observed summary:**")
        lines.append(f"- {finding['summary']}")
        lines.append("")
        lines.append("**Manual reproduction steps:**")
        for index, step in enumerate(finding.get("manual_steps", []), start=1):
            lines.append(f"{index}. {step}")
        lines.append("")
        lines.append("**Evidence files:**")
        for evidence in finding.get("evidence", []):
            lines.append(f"- `{evidence}`")
        lines.append("")
        lines.append("**What to learn from this challenge:**")
        for item in finding.get("what_to_learn", []):
            lines.append(f"- {item}")
        lines.append("")
        lines.append("**Hint ladder:**")
        for index, hint in enumerate(finding.get("hint_ladder", []), start=1):
            lines.append(f"- Hint {index}: {hint}")
        lines.append("")
        lines.append("**Recommended remediation:**")
        for item in finding.get("remediation", []):
            lines.append(f"- {item}")
        lines.append("")

    lines.append("## Suggested Study Order")
    lines.append("")
    lines.append("1. Reproduce IDOR manually in the browser and with curl.")
    lines.append("2. Reproduce the header-based admin export flaw in PowerShell or Burp Repeater.")
    lines.append("3. Validate reflected XSS and stored XSS in the browser.")
    lines.append("4. Review the JWT structure, decode it, and understand why the role claim is dangerous.")
    lines.append("5. Explore the MinIO console and compare public object access with authenticated console access.")
    lines.append("6. After the core path, try the advanced bonus flags by chaining JWT forgery or XSS to a second impact step.")
    lines.append("")
    lines.append("## Training Note")
    lines.append("")
    lines.append("This lab is for private learning only. It simulates bug bounty style findings, but it does not correspond to a real payout program.")

    (report_root / "FILLED_BUG_BOUNTY_REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()

    report_root = Path(args.report_root).resolve()
    summary = load_summary(report_root)
    total_points, max_points, completed, track_scores = score_summary(summary)

    render_scorecard(report_root, summary, total_points, max_points, completed, track_scores)
    render_bug_bounty_report(report_root, summary, completed, total_points)
    render_walkthrough_flags(report_root, completed, bool(track_scores.get("Baseline")), summary)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
