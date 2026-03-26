#!/usr/bin/env python3
"""Generate a markdown report from the Windows batch lab checks."""

from __future__ import annotations

import argparse
import base64
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def read_text(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace").strip()


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8", errors="replace"))
    except json.JSONDecodeError:
        return {}


def read_status_code(path: Path) -> int | None:
    raw = read_text(path)
    if not raw.isdigit():
        return None
    return int(raw)


def decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        return {}

    payload = parts[1]
    padding = "=" * (-len(payload) % 4)

    try:
        decoded = base64.urlsafe_b64decode(payload + padding).decode("utf-8")
        return json.loads(decoded)
    except (ValueError, json.JSONDecodeError):
        return {}


def rel(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def make_finding(
    title: str,
    severity: str,
    vulnerable: bool,
    summary: str,
    evidence: list[str],
) -> dict[str, Any]:
    return {
        "title": title,
        "severity": severity,
        "result": "Vulnerable" if vulnerable else "Not confirmed",
        "summary": summary,
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report-root", required=True)
    args = parser.parse_args()

    report_root = Path(args.report_root).resolve()
    raw_dir = report_root / "raw"

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")

    service_checks = [
        ("App Home", "app_home"),
        ("App Health", "app_health"),
        ("API Health", "api_health"),
        ("Admin Health", "admin_health"),
        ("Storage Console", "storage_console_home"),
        ("Public Object", "storage_public_object"),
    ]

    services: list[dict[str, Any]] = []
    for label, stem in service_checks:
        status_code = read_status_code(raw_dir / f"{stem}.status.txt")
        services.append(
            {
                "name": label,
                "status_code": status_code,
                "healthy": status_code == 200,
                "evidence": [
                    rel(raw_dir / f"{stem}.status.txt", report_root),
                    rel(raw_dir / f"{stem}.body.txt", report_root),
                ],
            }
        )

    login_response = read_json(raw_dir / "login_response.json")
    jwt_token = str(login_response.get("token", ""))
    jwt_payload = decode_jwt_payload(jwt_token)
    weak_jwt = bool(jwt_token) and "exp" not in jwt_payload and "role" in jwt_payload

    idor_users = [read_json(raw_dir / f"idor_user_{index}.json") for index in (1, 2, 3)]
    unique_users = {user.get("username") for user in idor_users if user}
    idor_vulnerable = len(unique_users) >= 3 and all("password" in user and "api_key" in user for user in idor_users if user)

    admin_export = read_json(raw_dir / "admin_export.json")
    admin_export_status = read_status_code(raw_dir / "admin_export.status.txt")
    admin_export_vulnerable = (
        admin_export_status == 200
        and isinstance(admin_export.get("users"), list)
        and bool(admin_export.get("storage", {}).get("secretKey"))
    )

    reflected_payload = read_text(raw_dir / "reflected_xss_payload.txt")
    reflected_html = read_text(raw_dir / "reflected_xss.html")
    reflected_xss = bool(reflected_payload) and reflected_payload in reflected_html

    stored_payload = read_text(raw_dir / "stored_xss_payload.txt")
    stored_home = read_text(raw_dir / "stored_xss_home.html")
    stored_comments = read_json(raw_dir / "stored_xss_comments.json").get("comments", [])
    stored_xss = bool(stored_payload) and (
        stored_payload in stored_home
        or any(stored_payload == comment.get("content") for comment in stored_comments if isinstance(comment, dict))
    )

    storage_console_status = read_status_code(raw_dir / "storage_console.status.txt")
    public_object_status = read_status_code(raw_dir / "storage_public_object_check.status.txt")
    storage_env = read_text(raw_dir / "storage_env.txt")
    default_minio_creds = "MINIO_ROOT_USER=minioadmin" in storage_env and "MINIO_ROOT_PASSWORD=minioadmin" in storage_env
    storage_public = storage_console_status == 200 and public_object_status == 200

    findings = [
        make_finding(
            "Weak JWT configuration on /login",
            "Medium",
            weak_jwt,
            "The API login returns a signed JWT that includes a trusted role claim and no expiration timestamp.",
            [
                rel(raw_dir / "login_request.json", report_root),
                rel(raw_dir / "login_response.json", report_root),
            ],
        ),
        make_finding(
            "IDOR on /api/user?id=",
            "High",
            idor_vulnerable,
            "Changing the id parameter exposes different users, including passwords and API keys, without authorization.",
            [rel(raw_dir / f"idor_user_{index}.json", report_root) for index in (1, 2, 3)],
        ),
        make_finding(
            "Broken access control on /export via role header",
            "Critical",
            admin_export_vulnerable,
            "Sending only role: admin returns privileged export data, including storage secrets and full user records.",
            [
                rel(raw_dir / "admin_export.status.txt", report_root),
                rel(raw_dir / "admin_export.json", report_root),
            ],
        ),
        make_finding(
            "Reflected XSS on /profile",
            "High",
            reflected_xss,
            "The profile preview reflects the supplied bio payload directly into the HTML without sanitization.",
            [
                rel(raw_dir / "reflected_xss_payload.txt", report_root),
                rel(raw_dir / "reflected_xss.html", report_root),
            ],
        ),
        make_finding(
            "Stored XSS in comment feed",
            "High",
            stored_xss,
            "A malicious comment payload is stored and rendered back into the home page and comments API output without sanitization.",
            [
                rel(raw_dir / "stored_xss_payload.txt", report_root),
                rel(raw_dir / "stored_xss_post.body.txt", report_root),
                rel(raw_dir / "stored_xss_home.html", report_root),
                rel(raw_dir / "stored_xss_comments.json", report_root),
            ],
        ),
        make_finding(
            "MinIO storage exposure",
            "High",
            storage_public or default_minio_creds,
            "The storage console is exposed locally, the public object is readable without authentication, and default MinIO credentials remain configured.",
            [
                rel(raw_dir / "storage_console.html", report_root),
                rel(raw_dir / "storage_public_object_check.txt", report_root),
                rel(raw_dir / "storage_env.txt", report_root),
            ],
        ),
    ]

    summary = {
        "generated_at": generated_at,
        "report_root": report_root.as_posix(),
        "services": services,
        "jwt_payload": jwt_payload,
        "findings": findings,
    }

    (report_root / "summary.json").write_text(
        json.dumps(summary, indent=2),
        encoding="utf-8",
    )

    lines: list[str] = []
    lines.append("# Automated Windows Test Report")
    lines.append("")
    lines.append(f"Generated: `{generated_at}`")
    lines.append(f"Evidence root: `{report_root.as_posix()}`")
    lines.append("")
    lines.append("## Service Status")
    lines.append("")
    lines.append("| Service | HTTP Status | Healthy | Evidence |")
    lines.append("| --- | --- | --- | --- |")
    for service in services:
        code = service["status_code"] if service["status_code"] is not None else "n/a"
        healthy = "Yes" if service["healthy"] else "No"
        evidence = ", ".join(f"`{item}`" for item in service["evidence"])
        lines.append(f"| {service['name']} | {code} | {healthy} | {evidence} |")

    lines.append("")
    lines.append("## JWT Snapshot")
    lines.append("")
    if jwt_payload:
        lines.append("```json")
        lines.append(json.dumps(jwt_payload, indent=2))
        lines.append("```")
    else:
        lines.append("JWT payload could not be decoded from the captured login response.")

    lines.append("")
    lines.append("## Findings")
    lines.append("")
    for finding in findings:
        lines.append(f"### {finding['title']}")
        lines.append("")
        lines.append(f"- Severity: `{finding['severity']}`")
        lines.append(f"- Result: `{finding['result']}`")
        lines.append(f"- Summary: {finding['summary']}")
        lines.append(f"- Evidence: {', '.join(f'`{item}`' for item in finding['evidence'])}")
        lines.append("")

    lines.append("## Notes")
    lines.append("")
    lines.append("- The reflected and stored XSS checks confirm unsanitized rendering by capturing the raw payload in the HTML output. Use a browser manually if you also want a popup screenshot.")
    lines.append("- The admin export and IDOR checks collect raw JSON so you can reuse the evidence directly in a bug bounty style report.")

    (report_root / "AUTOMATED_WINDOWS_TEST_REPORT.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
