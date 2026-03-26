#!/usr/bin/env python3
"""Generate reward-style learning assets from a Windows test run summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BASELINE_POINTS = 50
BASELINE_FLAG = "ACME{lab_online_baseline}"

CHALLENGE_CATALOG: dict[str, dict[str, Any]] = {
    "Weak JWT configuration on /login": {
        "track": "Auth And Token Abuse",
        "level": "Intermediate",
        "points": 100,
        "reward": "Token Breaker",
        "flag": "ACME{jwt_role_claim_without_expiry}",
        "severity": "Medium",
        "why_it_matters": "Weak JWT design teaches how attackers abuse missing expiry and trusted client-side role claims.",
        "manual_steps": [
            "Log in as alice on the app or call POST /login directly.",
            "Capture the returned JWT and decode the payload.",
            "Confirm there is no exp claim and the role field is trusted in the token.",
        ],
        "hint_ladder": [
            "Look closely at the token returned by POST /login.",
            "Decode the JWT payload and inspect which claims are present.",
            "The flag is earned when you confirm the token keeps a role claim but no expiration.",
        ],
        "what_to_learn": [
            "How JWTs are structured and decoded.",
            "Why signed tokens still fail when weak secrets and dangerous claims are trusted.",
            "Why expiration and server-side authorization both matter.",
        ],
        "remediation": [
            "Use a strong random signing secret.",
            "Add token expiration and rotation.",
            "Do not trust privileged claims without server-side checks.",
        ],
    },
    "IDOR on /api/user?id=": {
        "track": "Access Control",
        "level": "Beginner",
        "points": 150,
        "reward": "Object Explorer",
        "flag": "ACME{idor_user_records_exposed}",
        "severity": "High",
        "why_it_matters": "IDOR is a common real bug bounty class because simple identifier changes can expose other users' data.",
        "manual_steps": [
            "Open /api/user?id=1 in the browser or curl.",
            "Change the id value to 2 and then 3.",
            "Observe that other users, including admin, are disclosed without authorization.",
        ],
        "hint_ladder": [
            "Try changing only the numeric id value in the same endpoint.",
            "Compare the returned usernames and sensitive fields.",
            "The flag is earned when three different user records are exposed by changing only id.",
        ],
        "what_to_learn": [
            "How to test object references safely and systematically.",
            "Which sensitive fields make IDOR findings more severe.",
            "How to write a clean impact statement for authorization flaws.",
        ],
        "remediation": [
            "Enforce object-level authorization for every requested record.",
            "Return only the caller's own data unless elevated access is verified.",
            "Avoid exposing sensitive fields like passwords and API keys.",
        ],
    },
    "Broken access control on /export via role header": {
        "track": "Access Control",
        "level": "Intermediate",
        "points": 200,
        "reward": "Header Impersonator",
        "flag": "ACME{trusted_client_role_header}",
        "severity": "Critical",
        "why_it_matters": "Trusting a client-supplied privilege header is an easy privilege escalation path and a strong learning case for broken server-side authorization.",
        "manual_steps": [
            "Send GET /export to the admin service.",
            "Add the request header role: admin.",
            "Observe that privileged export data is returned without real authentication.",
        ],
        "hint_ladder": [
            "The admin health endpoint works without special auth, but the real panel needs something extra.",
            "Try adding a simple header instead of a token or cookie.",
            "The flag is earned when role: admin alone unlocks the export response.",
        ],
        "what_to_learn": [
            "Why authorization must be bound to verified identity, not arbitrary request metadata.",
            "How to prove business impact from leaked secrets and records.",
            "How small header changes can produce high-severity findings.",
        ],
        "remediation": [
            "Require real authentication before admin endpoints are served.",
            "Ignore user-controlled privilege headers for authorization decisions.",
            "Perform role checks on server-side session or token state only.",
        ],
    },
    "Reflected XSS on /profile": {
        "track": "Client-side Injection",
        "level": "Beginner",
        "points": 150,
        "reward": "Link Crafter",
        "flag": "ACME{profile_bio_reflection_xss}",
        "severity": "High",
        "why_it_matters": "Reflected XSS teaches payload testing, URL encoding, browser execution, and how bugs become phishing-style attack chains.",
        "manual_steps": [
            "Visit /profile?bio=<script>alert(1)</script>.",
            "Observe that the payload is reflected directly into the HTML response.",
            "Confirm browser execution manually if you want a popup screenshot.",
        ],
        "hint_ladder": [
            "The profile preview is a better target than the login form.",
            "Try a harmless script payload in the bio query parameter.",
            "The flag is earned when your payload is reflected unsanitized in the profile preview response.",
        ],
        "what_to_learn": [
            "How reflection-based injection appears in raw responses.",
            "Why output encoding matters for query parameters.",
            "How reflected XSS is demonstrated in a report.",
        ],
        "remediation": [
            "HTML-encode reflected user input before rendering.",
            "Apply input handling rules appropriate to the rendering context.",
            "Use CSP as a defense-in-depth control.",
        ],
    },
    "Stored XSS in comment feed": {
        "track": "Client-side Injection",
        "level": "Intermediate",
        "points": 175,
        "reward": "Comment Ghost",
        "flag": "ACME{stored_comment_payload_rendered}",
        "severity": "High",
        "why_it_matters": "Stored XSS is highly valuable for learning because the payload persists and can affect other users and future page views.",
        "manual_steps": [
            "Submit a comment payload such as <img src=x onerror=alert(1)>.",
            "Reload the home page or fetch the comments API.",
            "Observe that the payload is stored and returned unsanitized.",
        ],
        "hint_ladder": [
            "The comment feed is storing raw HTML-like content already.",
            "Use a payload that executes when the page renders an invalid image.",
            "The flag is earned when your comment payload persists and is returned unsanitized from the feed.",
        ],
        "what_to_learn": [
            "How storage changes the risk profile of XSS findings.",
            "Why HTML-rich inputs need sanitization before display.",
            "How to tie stored XSS to session theft or admin compromise paths.",
        ],
        "remediation": [
            "Sanitize or encode comment content before rendering.",
            "Treat all user content as untrusted input.",
            "Store session cookies with HttpOnly to reduce exploit impact.",
        ],
    },
    "MinIO storage exposure": {
        "track": "Secrets And Storage",
        "level": "Beginner",
        "points": 125,
        "reward": "Bucket Diver",
        "flag": "ACME{public_bucket_default_minio_creds}",
        "severity": "High",
        "why_it_matters": "Misconfigured storage and unchanged default credentials are common bug bounty wins and excellent practice for cloud misconfiguration reviews.",
        "manual_steps": [
            "Open the public object in the browser or curl it anonymously.",
            "Visit the MinIO console and log in with minioadmin / minioadmin.",
            "Confirm the public-assets bucket and exposed object are accessible.",
        ],
        "hint_ladder": [
            "One object is readable even before you authenticate to the console.",
            "The admin UI uses the vendor's well-known default credentials.",
            "The flag is earned when you confirm both anonymous object access and default console credentials.",
        ],
        "what_to_learn": [
            "How public object exposure differs from full console compromise.",
            "Why default credentials are especially dangerous on admin surfaces.",
            "How to describe storage findings clearly in a report.",
        ],
        "remediation": [
            "Replace default credentials immediately.",
            "Remove unnecessary anonymous access.",
            "Apply least-privilege bucket policies and review exposed objects.",
        ],
    },
}


def load_summary(report_root: Path) -> dict[str, Any]:
    summary_path = report_root / "summary.json"
    return json.loads(summary_path.read_text(encoding="utf-8"))


def vulnerable_findings(summary: dict[str, Any]) -> list[dict[str, Any]]:
    return [finding for finding in summary.get("findings", []) if finding.get("result") == "Vulnerable"]


def score_summary(summary: dict[str, Any]) -> tuple[int, int, list[dict[str, Any]], dict[str, int]]:
    services = summary.get("services", [])
    healthy_services = all(service.get("healthy") for service in services)

    completed: list[dict[str, Any]] = []
    track_scores: dict[str, int] = {}
    total_points = BASELINE_POINTS if healthy_services else 0
    max_points = BASELINE_POINTS + sum(item["points"] for item in CHALLENGE_CATALOG.values())

    for finding in vulnerable_findings(summary):
        title = finding["title"]
        meta = CHALLENGE_CATALOG.get(title)
        if not meta:
            continue
        completed.append({**finding, **meta})
        total_points += meta["points"]
        track_scores[meta["track"]] = track_scores.get(meta["track"], 0) + meta["points"]

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
    for title, meta in CHALLENGE_CATALOG.items():
        status = "Earned" if title in completed_titles else "Pending"
        lines.append(f"| {title} | {meta['level']} | {meta['track']} | {meta['reward']} | {meta['points']} | {status} |")
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
    if len(completed) == len(CHALLENGE_CATALOG):
        lines.append("- You completed the full local reward lab path. Next step: reproduce each finding manually with Burp or ZAP and write your own report from scratch.")
        lines.append("- Try the advanced bonus path: forge an admin JWT manually and access /api/admin as a chained exploit.")
    else:
        lines.append("- Re-run the remaining manual checks and compare your own screenshots with the raw evidence in this run folder.")
        lines.append("- Practice rewriting each confirmed finding in HackerOne and Bugcrowd format.")
    lines.append("- Use the generated bug bounty report as a reference, then try producing your own cleaned-up version without automation.")

    (report_root / "LAB_REWARD_SCORECARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def render_walkthrough_flags(report_root: Path, completed: list[dict[str, Any]], baseline_earned: bool) -> None:
    completed_titles = {item["title"] for item in completed}

    lines: list[str] = []
    lines.append("# Walkthrough Flags")
    lines.append("")
    lines.append("These are private training flags for the local lab. Earn a flag only after you reproduce the issue yourself.")
    lines.append("")
    lines.append("| Challenge | Level | Flag | Status |")
    lines.append("| --- | --- | --- | --- |")
    lines.append(f"| Lab baseline online | Beginner | `{BASELINE_FLAG}` | {'Earned' if baseline_earned else 'Locked'} |")
    for title, meta in CHALLENGE_CATALOG.items():
        status = "Earned" if title in completed_titles else "Locked"
        lines.append(f"| {title} | {meta['level']} | `{meta['flag']}` | {status} |")
    lines.append("")
    lines.append("## Hint Ladders")
    lines.append("")
    for title, meta in CHALLENGE_CATALOG.items():
        lines.append(f"### {title}")
        lines.append("")
        lines.append(f"- Level: `{meta['level']}`")
        lines.append(f"- Flag: `{meta['flag']}`")
        for index, hint in enumerate(meta["hint_ladder"], start=1):
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
        for index, step in enumerate(finding["manual_steps"], start=1):
            lines.append(f"{index}. {step}")
        lines.append("")
        lines.append("**Evidence files:**")
        for evidence in finding["evidence"]:
            lines.append(f"- `{evidence}`")
        lines.append("")
        lines.append("**What to learn from this challenge:**")
        for item in finding["what_to_learn"]:
            lines.append(f"- {item}")
        lines.append("")
        lines.append("**Hint ladder:**")
        for index, hint in enumerate(finding["hint_ladder"], start=1):
            lines.append(f"- Hint {index}: {hint}")
        lines.append("")
        lines.append("**Recommended remediation:**")
        for item in finding["remediation"]:
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
    render_walkthrough_flags(report_root, completed, bool(track_scores.get("Baseline")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
