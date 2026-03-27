#!/usr/bin/env python3
"""Generate side-by-side vulnerable vs remediated comparison artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REPORTS_ROOT = PROJECT_ROOT / "reports"


def load_summary(report_root: Path) -> dict[str, Any]:
    summary_path = report_root / "summary.json"
    if not summary_path.exists():
        raise FileNotFoundError(f"Missing summary file: {summary_path}")
    return json.loads(summary_path.read_text(encoding="utf-8"))


def challenge_id_set(summary: dict[str, Any]) -> set[str]:
    return {
        str(item.get("id", "")).strip()
        for item in summary.get("challenge_results", [])
        if str(item.get("id", "")).strip()
    }


def preference_score(report_root: Path) -> int:
    name = report_root.name
    if name in {"manual-scenario", "remediated-scenario"}:
        return 40
    if name.startswith("windows-test-run_"):
        return 30
    if "dryrun" in name:
        return 20
    if name.startswith("verification-"):
        return 10
    return 15


def discover_summaries(reports_root: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    if not reports_root.exists():
        return records

    for summary_path in reports_root.glob("*/summary.json"):
        report_root = summary_path.parent
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        profile_id = str(summary.get("profile", {}).get("id", "")).strip()
        if profile_id not in {"vulnerable", "remediated"}:
            continue

        records.append(
            {
                "report_root": report_root.resolve(),
                "summary": summary,
                "profile_id": profile_id,
                "challenge_ids": challenge_id_set(summary),
                "mtime_ns": summary_path.stat().st_mtime_ns,
                "preference": preference_score(report_root),
            }
        )

    return records


def choose_partner(
    anchor: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    def partner_score(candidate: dict[str, Any]) -> tuple[int, int, int, int]:
        shared_ids = len(anchor["challenge_ids"] & candidate["challenge_ids"])
        candidate_count = len(candidate["challenge_ids"])
        return (
            shared_ids,
            min(len(anchor["challenge_ids"]), candidate_count),
            anchor["preference"] + candidate["preference"],
            candidate["mtime_ns"],
        )

    return max(candidates, key=partner_score)


def choose_best_pair(records: list[dict[str, Any]]) -> tuple[dict[str, Any], dict[str, Any]]:
    vulnerable_records = [record for record in records if record["profile_id"] == "vulnerable"]
    remediated_records = [record for record in records if record["profile_id"] == "remediated"]

    if not vulnerable_records or not remediated_records:
        raise FileNotFoundError(
            "Could not find both vulnerable and remediated summary.json files under the reports root."
        )

    best_pair: tuple[dict[str, Any], dict[str, Any]] | None = None
    best_score: tuple[int, int, int, int, int] | None = None

    for vulnerable in vulnerable_records:
        for remediated in remediated_records:
            shared_ids = len(vulnerable["challenge_ids"] & remediated["challenge_ids"])
            pair_score = (
                shared_ids,
                min(len(vulnerable["challenge_ids"]), len(remediated["challenge_ids"])),
                vulnerable["preference"] + remediated["preference"],
                min(vulnerable["mtime_ns"], remediated["mtime_ns"]),
                max(vulnerable["mtime_ns"], remediated["mtime_ns"]),
            )

            if best_score is None or pair_score > best_score:
                best_pair = (vulnerable, remediated)
                best_score = pair_score

    if best_pair is None:
        raise FileNotFoundError(
            "Could not identify a vulnerable/remediated comparison pair from the discovered reports."
        )

    return best_pair


def resolve_summary_record(
    profile_id: str,
    explicit_root: str | None,
    reports_root: Path,
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    if explicit_root:
        report_root = Path(explicit_root).resolve()
        summary = load_summary(report_root)
        actual_profile = str(summary.get("profile", {}).get("id", "")).strip()
        if actual_profile and actual_profile != profile_id:
            raise ValueError(
                f"Expected profile '{profile_id}' at {report_root}, found '{actual_profile}'."
            )
        return {
            "report_root": report_root,
            "summary": summary,
            "profile_id": actual_profile or profile_id,
            "challenge_ids": challenge_id_set(summary),
            "mtime_ns": (report_root / "summary.json").stat().st_mtime_ns,
            "preference": preference_score(report_root),
        }

    profile_records = [record for record in records if record["profile_id"] == profile_id]
    if not profile_records:
        raise FileNotFoundError(
            f"Could not find any {profile_id} summary.json files under {reports_root.as_posix()}."
        )

    return max(
        profile_records,
        key=lambda record: (
            len(record["challenge_ids"]),
            record["preference"],
            record["mtime_ns"],
        ),
    )


def is_vulnerable(result: str | None) -> bool:
    return str(result or "").strip().lower() == "vulnerable"


def status_class(result: str | None) -> str:
    normalized = str(result or "").strip().lower()
    if normalized == "vulnerable":
        return "status-bad"
    if normalized == "not confirmed":
        return "status-good"
    if normalized == "missing":
        return "status-missing"
    return "status-neutral"


def match_class(matches_profile: Any) -> str:
    if matches_profile is True:
        return "status-good"
    if matches_profile is False:
        return "status-bad"
    return "status-neutral"


def outcome_class(outcome: str) -> str:
    if outcome == "Fixed in remediated mode":
        return "status-good"
    if outcome == "Still vulnerable":
        return "status-bad"
    if outcome == "Regression in remediated mode":
        return "status-bad"
    if outcome == "Missing evidence":
        return "status-missing"
    return "status-neutral"


def profile_match_label(matches_profile: Any) -> str:
    if matches_profile is True:
        return "Profile match"
    if matches_profile is False:
        return "Profile mismatch"
    return "Profile n/a"


def classify_outcome(vulnerable_result: str | None, remediated_result: str | None) -> str:
    if vulnerable_result == "Missing" or remediated_result == "Missing":
        return "Missing evidence"
    if is_vulnerable(vulnerable_result) and not is_vulnerable(remediated_result):
        return "Fixed in remediated mode"
    if is_vulnerable(vulnerable_result) and is_vulnerable(remediated_result):
        return "Still vulnerable"
    if not is_vulnerable(vulnerable_result) and is_vulnerable(remediated_result):
        return "Regression in remediated mode"
    if vulnerable_result == remediated_result:
        return "Consistent across modes"
    return "Behavior changed"


def challenge_order(vulnerable_summary: dict[str, Any], remediated_summary: dict[str, Any]) -> list[str]:
    ordered_ids: list[str] = []

    for finding in vulnerable_summary.get("challenge_results", []):
        identifier = str(finding.get("id", "")).strip()
        if identifier and identifier not in ordered_ids:
            ordered_ids.append(identifier)

    for finding in remediated_summary.get("challenge_results", []):
        identifier = str(finding.get("id", "")).strip()
        if identifier and identifier not in ordered_ids:
            ordered_ids.append(identifier)

    return ordered_ids


def build_challenge_rows(
    vulnerable_summary: dict[str, Any],
    remediated_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    vulnerable_map = {
        str(item.get("id", "")): item
        for item in vulnerable_summary.get("challenge_results", [])
        if item.get("id")
    }
    remediated_map = {
        str(item.get("id", "")): item
        for item in remediated_summary.get("challenge_results", [])
        if item.get("id")
    }

    rows: list[dict[str, Any]] = []
    for identifier in challenge_order(vulnerable_summary, remediated_summary):
        vulnerable = vulnerable_map.get(identifier, {})
        remediated = remediated_map.get(identifier, {})
        vulnerable_result = str(vulnerable.get("result", "Missing"))
        remediated_result = str(remediated.get("result", "Missing"))

        rows.append(
            {
                "id": identifier,
                "title": vulnerable.get("title") or remediated.get("title") or identifier,
                "track": vulnerable.get("track") or remediated.get("track") or "Uncategorized",
                "severity": vulnerable.get("severity") or remediated.get("severity") or "Unknown",
                "points": int(vulnerable.get("points") or remediated.get("points") or 0),
                "vulnerable_result": vulnerable_result,
                "remediated_result": remediated_result,
                "vulnerable_matches_profile": vulnerable.get("matches_profile"),
                "remediated_matches_profile": remediated.get("matches_profile"),
                "outcome": classify_outcome(vulnerable_result, remediated_result),
                "summary": vulnerable.get("summary") or remediated.get("summary") or "",
            }
        )

    return rows


def build_service_rows(
    vulnerable_summary: dict[str, Any],
    remediated_summary: dict[str, Any],
) -> list[dict[str, Any]]:
    vulnerable_map = {
        str(item.get("name", "")): item for item in vulnerable_summary.get("services", []) if item.get("name")
    }
    remediated_map = {
        str(item.get("name", "")): item for item in remediated_summary.get("services", []) if item.get("name")
    }
    ordered_names: list[str] = []

    for service in vulnerable_summary.get("services", []):
        name = str(service.get("name", "")).strip()
        if name and name not in ordered_names:
            ordered_names.append(name)

    for service in remediated_summary.get("services", []):
        name = str(service.get("name", "")).strip()
        if name and name not in ordered_names:
            ordered_names.append(name)

    rows: list[dict[str, Any]] = []
    for name in ordered_names:
        vulnerable = vulnerable_map.get(name, {})
        remediated = remediated_map.get(name, {})
        rows.append(
            {
                "name": name,
                "vulnerable_status_code": vulnerable.get("status_code"),
                "remediated_status_code": remediated.get("status_code"),
                "vulnerable_healthy": vulnerable.get("healthy"),
                "remediated_healthy": remediated.get("healthy"),
                "vulnerable_expected_status": vulnerable.get("expected_status"),
                "remediated_expected_status": remediated.get("expected_status"),
            }
        )
    return rows


def build_track_rows(challenge_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    track_index: dict[str, dict[str, Any]] = {}

    for row in challenge_rows:
        track = str(row.get("track", "Uncategorized"))
        if track not in track_index:
            track_index[track] = {
                "track": track,
                "total": 0,
                "vulnerable_confirmed": 0,
                "remediated_confirmed": 0,
            }

        track_index[track]["total"] += 1
        if is_vulnerable(row.get("vulnerable_result")):
            track_index[track]["vulnerable_confirmed"] += 1
        if is_vulnerable(row.get("remediated_result")):
            track_index[track]["remediated_confirmed"] += 1

    return sorted(track_index.values(), key=lambda item: (item["remediated_confirmed"], item["track"]))


def build_snapshot(
    vulnerable_summary: dict[str, Any],
    remediated_summary: dict[str, Any],
    challenge_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    vulnerable_confirmed = sum(1 for row in challenge_rows if is_vulnerable(row["vulnerable_result"]))
    remediated_confirmed = sum(1 for row in challenge_rows if is_vulnerable(row["remediated_result"]))
    fixed_count = sum(1 for row in challenge_rows if row["outcome"] == "Fixed in remediated mode")
    regression_count = sum(1 for row in challenge_rows if row["outcome"] == "Regression in remediated mode")
    match_vulnerable = sum(1 for row in challenge_rows if row["vulnerable_matches_profile"] is True)
    match_remediated = sum(1 for row in challenge_rows if row["remediated_matches_profile"] is True)
    total_services = max(
        len(vulnerable_summary.get("services", [])),
        len(remediated_summary.get("services", [])),
    )
    vulnerable_healthy = sum(1 for service in vulnerable_summary.get("services", []) if service.get("healthy"))
    remediated_healthy = sum(1 for service in remediated_summary.get("services", []) if service.get("healthy"))
    hardening_percent = round((fixed_count / vulnerable_confirmed) * 100) if vulnerable_confirmed else 0

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
        "total_challenges": len(challenge_rows),
        "vulnerable_confirmed": vulnerable_confirmed,
        "remediated_confirmed": remediated_confirmed,
        "fixed_count": fixed_count,
        "regression_count": regression_count,
        "residual_count": remediated_confirmed,
        "hardening_percent": hardening_percent,
        "vulnerable_profile_matches": match_vulnerable,
        "remediated_profile_matches": match_remediated,
        "total_services": total_services,
        "vulnerable_healthy_services": vulnerable_healthy,
        "remediated_healthy_services": remediated_healthy,
    }


def render_markdown(
    output_root: Path,
    snapshot: dict[str, Any],
    challenge_rows: list[dict[str, Any]],
    service_rows: list[dict[str, Any]],
    track_rows: list[dict[str, Any]],
    vulnerable_root: Path,
    remediated_root: Path,
) -> None:
    residual_rows = [row for row in challenge_rows if row["outcome"] == "Still vulnerable"]
    fixed_rows = [row for row in challenge_rows if row["outcome"] == "Fixed in remediated mode"]

    lines: list[str] = []
    lines.append("# Vulnerable vs Remediated Comparison Summary")
    lines.append("")
    lines.append(f"Generated: `{snapshot['generated_at']}`")
    lines.append(f"Vulnerable source: `{vulnerable_root.as_posix()}`")
    lines.append(f"Remediated source: `{remediated_root.as_posix()}`")
    lines.append("")
    lines.append("## Snapshot")
    lines.append("")
    lines.append(f"- Total shared scenarios: `{snapshot['total_challenges']}`")
    lines.append(f"- Confirmed in vulnerable mode: `{snapshot['vulnerable_confirmed']}`")
    lines.append(f"- Confirmed in remediated mode: `{snapshot['remediated_confirmed']}`")
    lines.append(f"- Fixed in remediated mode: `{snapshot['fixed_count']}`")
    lines.append(f"- Residual findings in remediated mode: `{snapshot['residual_count']}`")
    lines.append(f"- Hardening coverage: `{snapshot['hardening_percent']}%`")
    lines.append("")
    lines.append("## Challenge Matrix")
    lines.append("")
    lines.append("| Challenge | Track | Vulnerable | Remediated | Outcome |")
    lines.append("| --- | --- | --- | --- | --- |")

    for row in challenge_rows:
        lines.append(
            f"| {row['title']} | {row['track']} | {row['vulnerable_result']} | "
            f"{row['remediated_result']} | {row['outcome']} |"
        )

    lines.append("")
    lines.append("## Track Drift")
    lines.append("")
    lines.append("| Track | Shared Challenges | Vulnerable Confirmed | Remediated Confirmed |")
    lines.append("| --- | --- | --- | --- |")
    for row in track_rows:
        lines.append(
            f"| {row['track']} | {row['total']} | {row['vulnerable_confirmed']} | {row['remediated_confirmed']} |"
        )

    lines.append("")
    lines.append("## Service Health")
    lines.append("")
    lines.append("| Service | Vulnerable | Remediated |")
    lines.append("| --- | --- | --- |")
    for row in service_rows:
        vulnerable_value = (
            f"{row['vulnerable_status_code']} ({'healthy' if row['vulnerable_healthy'] else 'unhealthy'})"
            if row["vulnerable_status_code"] is not None
            else "missing"
        )
        remediated_value = (
            f"{row['remediated_status_code']} ({'healthy' if row['remediated_healthy'] else 'unhealthy'})"
            if row["remediated_status_code"] is not None
            else "missing"
        )
        lines.append(f"| {row['name']} | {vulnerable_value} | {remediated_value} |")

    lines.append("")
    lines.append("## Residual Attention")
    lines.append("")
    if residual_rows:
        for row in residual_rows:
            lines.append(f"- `{row['title']}` remains vulnerable in remediated mode.")
    else:
        lines.append("- No residual confirmed findings remain in the remediated profile.")

    lines.append("")
    lines.append("## Fixed Highlights")
    lines.append("")
    if fixed_rows:
        for row in fixed_rows:
            lines.append(f"- `{row['title']}` moved from `Vulnerable` to `{row['remediated_result']}`.")
    else:
        lines.append("- No scenario transitioned to a fixed state yet.")

    (output_root / "COMPARISON_SUMMARY.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_html(
    output_root: Path,
    snapshot: dict[str, Any],
    challenge_rows: list[dict[str, Any]],
    service_rows: list[dict[str, Any]],
    track_rows: list[dict[str, Any]],
    vulnerable_root: Path,
    remediated_root: Path,
) -> None:
    residual_rows = [row for row in challenge_rows if row["outcome"] == "Still vulnerable"]
    fixed_rows = [row for row in challenge_rows if row["outcome"] == "Fixed in remediated mode"]

    def chip(label: str, css_class: str) -> str:
        return f'<span class="status-pill {css_class}">{escape(label)}</span>'

    def service_chip(healthy: Any) -> str:
        if healthy is True:
            return chip("Healthy", "status-good")
        if healthy is False:
            return chip("Unhealthy", "status-bad")
        return chip("Missing", "status-missing")

    challenge_table_rows = "\n".join(
        [
            (
                "<tr>"
                f"<td><strong>{escape(row['title'])}</strong><div class=\"muted\">{escape(row['summary'])}</div></td>"
                f"<td>{escape(row['track'])}</td>"
                f"<td>{escape(row['severity'])}</td>"
                f"<td>{chip(row['vulnerable_result'], status_class(row['vulnerable_result']))}<div class=\"mini\">"
                f"{chip(profile_match_label(row['vulnerable_matches_profile']), match_class(row['vulnerable_matches_profile']))}</div></td>"
                f"<td>{chip(row['remediated_result'], status_class(row['remediated_result']))}<div class=\"mini\">"
                f"{chip(profile_match_label(row['remediated_matches_profile']), match_class(row['remediated_matches_profile']))}</div></td>"
                f"<td>{chip(row['outcome'], outcome_class(row['outcome']))}</td>"
                "</tr>"
            )
            for row in challenge_rows
        ]
    )

    service_table_rows = "\n".join(
        [
            (
                "<tr>"
                f"<td>{escape(row['name'])}</td>"
                f"<td>{escape(str(row['vulnerable_status_code']) if row['vulnerable_status_code'] is not None else 'missing')} "
                f"{service_chip(row['vulnerable_healthy'])}</td>"
                f"<td>{escape(str(row['remediated_status_code']) if row['remediated_status_code'] is not None else 'missing')} "
                f"{service_chip(row['remediated_healthy'])}</td>"
                "</tr>"
            )
            for row in service_rows
        ]
    )

    track_table_rows = "\n".join(
        [
            (
                "<tr>"
                f"<td>{escape(row['track'])}</td>"
                f"<td>{row['total']}</td>"
                f"<td>{row['vulnerable_confirmed']}</td>"
                f"<td>{row['remediated_confirmed']}</td>"
                "</tr>"
            )
            for row in track_rows
        ]
    )

    residual_items = "\n".join(
        [f"<li>{escape(row['title'])}</li>" for row in residual_rows]
    ) or "<li>No residual confirmed findings in remediated mode.</li>"
    fixed_items = "\n".join(
        [f"<li>{escape(row['title'])}</li>" for row in fixed_rows]
    ) or "<li>No scenarios have transitioned to fixed yet.</li>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Lab Mode Comparison Dashboard</title>
  <style>
    :root {{
      --bg: #f4f0e8;
      --bg-accent: #e4efe7;
      --ink: #1f1d1a;
      --muted: #5f5a53;
      --panel: rgba(255, 252, 246, 0.88);
      --line: rgba(61, 53, 44, 0.12);
      --shadow: 0 24px 60px rgba(56, 44, 31, 0.14);
      --good: #12715f;
      --good-bg: #daf4eb;
      --bad: #8f2626;
      --bad-bg: #f9dfdb;
      --warn: #8a5a08;
      --warn-bg: #faecc7;
      --neutral: #44556d;
      --neutral-bg: #dfe8f5;
      --missing: #6a5f4a;
      --missing-bg: #ede6d8;
    }}

    * {{
      box-sizing: border-box;
    }}

    body {{
      margin: 0;
      font-family: "Trebuchet MS", "Segoe UI", sans-serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(255, 207, 145, 0.42), transparent 30%),
        radial-gradient(circle at top right, rgba(124, 205, 181, 0.34), transparent 34%),
        linear-gradient(160deg, var(--bg) 0%, #f8f6f0 45%, var(--bg-accent) 100%);
    }}

    .shell {{
      max-width: 1360px;
      margin: 0 auto;
      padding: 40px 24px 64px;
    }}

    .hero {{
      padding: 30px;
      border: 1px solid rgba(255, 255, 255, 0.42);
      border-radius: 28px;
      background: linear-gradient(135deg, rgba(255, 251, 245, 0.94), rgba(243, 249, 245, 0.9));
      box-shadow: var(--shadow);
      backdrop-filter: blur(10px);
      position: relative;
      overflow: hidden;
    }}

    .hero::after {{
      content: "";
      position: absolute;
      inset: auto -80px -80px auto;
      width: 220px;
      height: 220px;
      background: radial-gradient(circle, rgba(18, 113, 95, 0.22), transparent 68%);
      pointer-events: none;
    }}

    .eyebrow {{
      text-transform: uppercase;
      letter-spacing: 0.16em;
      font-size: 12px;
      color: var(--muted);
      margin: 0 0 10px;
    }}

    h1, h2 {{
      font-family: Georgia, "Times New Roman", serif;
      letter-spacing: -0.03em;
      margin: 0;
    }}

    h1 {{
      font-size: clamp(2.3rem, 5vw, 4rem);
      line-height: 0.96;
      max-width: 11ch;
    }}

    .hero-grid {{
      display: grid;
      grid-template-columns: 1.1fr 0.9fr;
      gap: 28px;
      align-items: end;
      position: relative;
      z-index: 1;
    }}

    .hero-copy p {{
      max-width: 62ch;
      color: var(--muted);
      line-height: 1.6;
      margin: 14px 0 0;
    }}

    .meta-list {{
      margin: 0;
      padding: 0;
      list-style: none;
      display: grid;
      gap: 12px;
      color: var(--muted);
      font-size: 14px;
    }}

    .meta-list code {{
      font-family: Consolas, "Courier New", monospace;
      font-size: 13px;
      word-break: break-all;
    }}

    .card-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 18px;
      margin-top: 22px;
    }}

    .card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 22px;
      padding: 18px 18px 16px;
      box-shadow: var(--shadow);
    }}

    .metric-label {{
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.12em;
      color: var(--muted);
      margin-bottom: 10px;
    }}

    .metric-value {{
      font-size: clamp(1.9rem, 3vw, 2.8rem);
      font-weight: 700;
      line-height: 1;
    }}

    .metric-sub {{
      color: var(--muted);
      margin-top: 10px;
      font-size: 14px;
      line-height: 1.45;
    }}

    .section {{
      margin-top: 24px;
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 22px;
      box-shadow: var(--shadow);
    }}

    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 16px;
    }}

    .section-head p {{
      margin: 6px 0 0;
      color: var(--muted);
      line-height: 1.5;
      max-width: 62ch;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 14px;
    }}

    th, td {{
      text-align: left;
      padding: 14px 12px;
      border-top: 1px solid var(--line);
      vertical-align: top;
    }}

    thead th {{
      border-top: none;
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
      color: var(--muted);
    }}

    tbody tr:hover {{
      background: rgba(18, 113, 95, 0.05);
    }}

    .muted {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
      margin-top: 6px;
    }}

    .status-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.03em;
      white-space: nowrap;
    }}

    .mini {{
      margin-top: 10px;
    }}

    .status-good {{
      color: var(--good);
      background: var(--good-bg);
    }}

    .status-bad {{
      color: var(--bad);
      background: var(--bad-bg);
    }}

    .status-neutral {{
      color: var(--neutral);
      background: var(--neutral-bg);
    }}

    .status-missing {{
      color: var(--missing);
      background: var(--missing-bg);
    }}

    .status-warn {{
      color: var(--warn);
      background: var(--warn-bg);
    }}

    .two-up {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 24px;
    }}

    ul {{
      margin: 0;
      padding-left: 20px;
      color: var(--muted);
      line-height: 1.7;
    }}

    .footer-note {{
      color: var(--muted);
      margin-top: 18px;
      font-size: 13px;
    }}

    @media (max-width: 980px) {{
      .hero-grid,
      .two-up {{
        grid-template-columns: 1fr;
      }}

      .shell {{
        padding: 24px 14px 40px;
      }}

      .hero,
      .section {{
        padding: 18px;
      }}

      table {{
        display: block;
        overflow-x: auto;
      }}
    }}
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-grid">
        <div class="hero-copy">
          <p class="eyebrow">Shared Scenario Dashboard</p>
          <h1>Vulnerable vs remediated mode, side by side.</h1>
          <p>
            This comparison reads the generated <code>summary.json</code> artifacts for both profiles and shows which
            scenarios were removed, which ones still survive, and whether the service health stayed stable while the
            lab hardened.
          </p>
        </div>
        <ul class="meta-list">
          <li>Generated: <code>{escape(snapshot['generated_at'])}</code></li>
          <li>Vulnerable summary: <code>{escape((vulnerable_root / 'summary.json').as_posix())}</code></li>
          <li>Remediated summary: <code>{escape((remediated_root / 'summary.json').as_posix())}</code></li>
          <li>Output folder: <code>{escape(output_root.as_posix())}</code></li>
        </ul>
      </div>
      <div class="card-grid">
        <article class="card">
          <div class="metric-label">Shared Scenarios</div>
          <div class="metric-value">{snapshot['total_challenges']}</div>
          <div class="metric-sub">One catalog, two modes, one comparison surface.</div>
        </article>
        <article class="card">
          <div class="metric-label">Confirmed In Vulnerable Mode</div>
          <div class="metric-value">{snapshot['vulnerable_confirmed']}</div>
          <div class="metric-sub">Expected training baseline findings still reproduced.</div>
        </article>
        <article class="card">
          <div class="metric-label">Residual In Remediated Mode</div>
          <div class="metric-value">{snapshot['remediated_confirmed']}</div>
          <div class="metric-sub">Confirmed findings that still remain after hardening.</div>
        </article>
        <article class="card">
          <div class="metric-label">Hardening Coverage</div>
          <div class="metric-value">{snapshot['hardening_percent']}%</div>
          <div class="metric-sub">{snapshot['fixed_count']} fixed, {snapshot['regression_count']} regressions.</div>
        </article>
      </div>
    </section>

    <section class="section">
      <div class="section-head">
        <div>
          <h2>Challenge Matrix</h2>
          <p>The same scenario manifest set, compared across the intentionally insecure and remediated stacks.</p>
        </div>
        {chip(f"{snapshot['fixed_count']} fixed", "status-good")} {chip(f"{snapshot['residual_count']} residual", "status-warn" if snapshot['residual_count'] else "status-good")}
      </div>
      <table>
        <thead>
          <tr>
            <th>Challenge</th>
            <th>Track</th>
            <th>Severity</th>
            <th>Vulnerable</th>
            <th>Remediated</th>
            <th>Outcome</th>
          </tr>
        </thead>
        <tbody>
          {challenge_table_rows}
        </tbody>
      </table>
    </section>

    <div class="two-up">
      <section class="section">
        <div class="section-head">
          <div>
            <h2>Track Drift</h2>
            <p>Where hardening removed the most findings, organized by challenge track.</p>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Track</th>
              <th>Shared</th>
              <th>Vulnerable</th>
              <th>Remediated</th>
            </tr>
          </thead>
          <tbody>
            {track_table_rows}
          </tbody>
        </table>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Service Health</h2>
            <p>Baseline service checks from each summary so hardening changes stay observable.</p>
          </div>
        </div>
        <table>
          <thead>
            <tr>
              <th>Service</th>
              <th>Vulnerable</th>
              <th>Remediated</th>
            </tr>
          </thead>
          <tbody>
            {service_table_rows}
          </tbody>
        </table>
        <p class="footer-note">
          Healthy services: {snapshot['vulnerable_healthy_services']}/{snapshot['total_services']} in vulnerable mode and
          {snapshot['remediated_healthy_services']}/{snapshot['total_services']} in remediated mode.
        </p>
      </section>
    </div>

    <div class="two-up">
      <section class="section">
        <div class="section-head">
          <div>
            <h2>Fixed Highlights</h2>
            <p>Scenarios that were confirmed in the vulnerable stack but dropped out after remediation.</p>
          </div>
        </div>
        <ul>
          {fixed_items}
        </ul>
      </section>

      <section class="section">
        <div class="section-head">
          <div>
            <h2>Residual Attention</h2>
            <p>Anything still confirmed in remediated mode should stay on the next engineering pass.</p>
          </div>
        </div>
        <ul>
          {residual_items}
        </ul>
      </section>
    </div>
  </main>
</body>
</html>
"""

    (output_root / "COMPARISON_DASHBOARD.html").write_text(html, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vulnerable-report-root")
    parser.add_argument("--remediated-report-root")
    parser.add_argument("--reports-root", default=str(DEFAULT_REPORTS_ROOT))
    parser.add_argument("--output-root", default=str(DEFAULT_REPORTS_ROOT / "mode-comparison"))
    args = parser.parse_args()

    reports_root = Path(args.reports_root).resolve()
    output_root = Path(args.output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    discovered_records = discover_summaries(reports_root)

    if args.vulnerable_report_root and args.remediated_report_root:
        vulnerable_record = resolve_summary_record(
            "vulnerable",
            args.vulnerable_report_root,
            reports_root,
            discovered_records,
        )
        remediated_record = resolve_summary_record(
            "remediated",
            args.remediated_report_root,
            reports_root,
            discovered_records,
        )
    elif args.vulnerable_report_root:
        vulnerable_record = resolve_summary_record(
            "vulnerable",
            args.vulnerable_report_root,
            reports_root,
            discovered_records,
        )
        remediated_candidates = [
            record for record in discovered_records if record["profile_id"] == "remediated"
        ]
        if not remediated_candidates:
            raise FileNotFoundError(
                f"Could not find any remediated summary.json files under {reports_root.as_posix()}."
            )
        remediated_record = choose_partner(vulnerable_record, remediated_candidates)
    elif args.remediated_report_root:
        remediated_record = resolve_summary_record(
            "remediated",
            args.remediated_report_root,
            reports_root,
            discovered_records,
        )
        vulnerable_candidates = [
            record for record in discovered_records if record["profile_id"] == "vulnerable"
        ]
        if not vulnerable_candidates:
            raise FileNotFoundError(
                f"Could not find any vulnerable summary.json files under {reports_root.as_posix()}."
            )
        vulnerable_record = choose_partner(remediated_record, vulnerable_candidates)
    else:
        vulnerable_record, remediated_record = choose_best_pair(discovered_records)

    vulnerable_root = Path(vulnerable_record["report_root"])
    remediated_root = Path(remediated_record["report_root"])
    vulnerable_summary = vulnerable_record["summary"]
    remediated_summary = remediated_record["summary"]

    challenge_rows = build_challenge_rows(vulnerable_summary, remediated_summary)
    service_rows = build_service_rows(vulnerable_summary, remediated_summary)
    track_rows = build_track_rows(challenge_rows)
    snapshot = build_snapshot(vulnerable_summary, remediated_summary, challenge_rows)

    comparison_payload = {
        "generated_at": snapshot["generated_at"],
        "vulnerable_report_root": vulnerable_root.as_posix(),
        "remediated_report_root": remediated_root.as_posix(),
        "output_root": output_root.as_posix(),
        "snapshot": snapshot,
        "challenge_rows": challenge_rows,
        "service_rows": service_rows,
        "track_rows": track_rows,
    }
    (output_root / "comparison.json").write_text(json.dumps(comparison_payload, indent=2), encoding="utf-8")

    render_markdown(
        output_root,
        snapshot,
        challenge_rows,
        service_rows,
        track_rows,
        vulnerable_root,
        remediated_root,
    )
    render_html(
        output_root,
        snapshot,
        challenge_rows,
        service_rows,
        track_rows,
        vulnerable_root,
        remediated_root,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
