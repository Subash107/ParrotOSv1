#!/usr/bin/env python3
"""Generate badge, certificate, and record files for lab completion awards."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import re
import textwrap
from pathlib import Path


DEFAULT_LAB_NAME = "Acme DevSecOps Bug Bounty Simulation Lab"
DEFAULT_REPO_URL = "https://github.com/Subash107/ParrotOS"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate completion badge assets for the Acme lab."
    )
    parser.add_argument("--recipient-name", required=True, help="Name on the award")
    parser.add_argument(
        "--github-username",
        default="",
        help="Optional GitHub username for the award record",
    )
    parser.add_argument(
        "--track",
        default="Full Lab Completion",
        help="Track or award label to display",
    )
    parser.add_argument(
        "--completion-date",
        default="",
        help="Completion date in YYYY-MM-DD format, defaults to today",
    )
    parser.add_argument(
        "--badge-slug",
        default="",
        help="Optional custom slug for output files",
    )
    parser.add_argument(
        "--evidence-summary",
        default="",
        help="Optional summary describing how the completion was validated",
    )
    parser.add_argument(
        "--output-root",
        default="achievements",
        help="Directory where generated assets should be written",
    )
    parser.add_argument(
        "--lab-name",
        default=DEFAULT_LAB_NAME,
        help="Lab name shown on the certificate",
    )
    parser.add_argument(
        "--repo-url",
        default=DEFAULT_REPO_URL,
        help="Repository URL included in generated records",
    )
    parser.add_argument(
        "--workflow-run-url",
        default="",
        help="Optional workflow run URL included in generated records",
    )
    parser.add_argument(
        "--github-output",
        default="",
        help="Optional path to a GitHub Actions output file",
    )
    return parser.parse_args()


def normalize_date(value: str) -> tuple[str, str]:
    if value:
        parsed = dt.date.fromisoformat(value)
    else:
        parsed = dt.date.today()
    return parsed.isoformat(), parsed.strftime("%B %d, %Y")


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or "completion-award"


def build_slug(args: argparse.Namespace, date_iso: str) -> str:
    if args.badge_slug.strip():
        return slugify(args.badge_slug)
    base = f"{args.recipient_name}-{args.track}-{date_iso}"
    return slugify(base)


def short_text(value: str, width: int) -> str:
    value = " ".join(value.split())
    if len(value) <= width:
        return value
    return value[: width - 3].rstrip() + "..."


def wrap_svg_text(value: str, width: int) -> list[str]:
    cleaned = " ".join(value.split())
    return textwrap.wrap(cleaned, width=width)[:2] or [""]


def render_badge(
    recipient_name: str,
    github_username: str,
    track: str,
    completion_date_display: str,
    slug: str,
) -> str:
    recipient_lines = wrap_svg_text(recipient_name, 24)
    footer_name = f"@{github_username}" if github_username else slug
    footer_name = short_text(footer_name, 32)

    line_y = [182, 228]
    name_blocks = "\n".join(
        f'    <text x="72" y="{y}" font-size="46" font-weight="700" fill="#f8fafc">{html.escape(line)}</text>'
        for line, y in zip(recipient_lines, line_y)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="630" viewBox="0 0 1200 630" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(track)} badge</title>
  <desc id="desc">Completion badge for {html.escape(recipient_name)} in the Acme DevSecOps Bug Bounty Simulation Lab.</desc>
  <defs>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="50%" stop-color="#111827" />
      <stop offset="100%" stop-color="#172554" />
    </linearGradient>
    <linearGradient id="accent" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#22c55e" />
      <stop offset="100%" stop-color="#38bdf8" />
    </linearGradient>
  </defs>
  <rect width="1200" height="630" rx="36" fill="url(#bg)" />
  <rect x="32" y="32" width="1136" height="566" rx="28" fill="none" stroke="#334155" stroke-width="2" />
  <rect x="72" y="76" width="238" height="42" rx="21" fill="#0b1220" stroke="#22c55e" />
  <text x="191" y="104" text-anchor="middle" font-size="20" font-weight="700" fill="#86efac">ACME LAB AWARD</text>
  <text x="72" y="150" font-size="20" font-weight="600" fill="#93c5fd">Certificate of completion</text>
{name_blocks}
  <text x="72" y="292" font-size="28" font-weight="500" fill="#cbd5e1">{html.escape(track)}</text>
  <rect x="72" y="332" width="452" height="8" rx="4" fill="url(#accent)" />
  <text x="72" y="392" font-size="24" fill="#cbd5e1">Awarded for completing the intentionally vulnerable training lab.</text>
  <text x="72" y="438" font-size="22" fill="#94a3b8">Issued {html.escape(completion_date_display)}</text>
  <text x="72" y="542" font-size="20" fill="#64748b">{html.escape(footer_name)}</text>
  <circle cx="963" cy="236" r="116" fill="#0b1220" stroke="url(#accent)" stroke-width="10" />
  <path d="M928 236l24 24 46-58" fill="none" stroke="#4ade80" stroke-width="18" stroke-linecap="round" stroke-linejoin="round" />
  <text x="963" y="405" text-anchor="middle" font-size="24" font-weight="700" fill="#e2e8f0">VERIFIED</text>
  <text x="963" y="440" text-anchor="middle" font-size="18" fill="#93c5fd">training completion</text>
  <text x="963" y="517" text-anchor="middle" font-size="18" fill="#64748b">github.com/Subash107/ParrotOS</text>
</svg>
"""


def render_certificate(
    recipient_name: str,
    github_username: str,
    track: str,
    completion_date_display: str,
    evidence_summary: str,
    lab_name: str,
    repo_url: str,
    workflow_run_url: str,
    badge_rel_path: str,
) -> str:
    username_line = (
        f"<p><strong>GitHub:</strong> @{html.escape(github_username)}</p>"
        if github_username
        else ""
    )
    evidence_html = (
        f"<p><strong>Evidence summary:</strong> {html.escape(evidence_summary)}</p>"
        if evidence_summary
        else "<p><strong>Evidence summary:</strong> Completion was recorded through the lab badge workflow.</p>"
    )
    workflow_html = (
        f'<p><strong>Workflow run:</strong> <a href="{html.escape(workflow_run_url)}">{html.escape(workflow_run_url)}</a></p>'
        if workflow_run_url
        else ""
    )

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{html.escape(recipient_name)} - Completion Certificate</title>
  <style>
    :root {{
      color-scheme: dark;
      --bg: #09111f;
      --panel: #0f172a;
      --border: #334155;
      --text: #e2e8f0;
      --muted: #94a3b8;
      --accent: #22c55e;
      --accent-alt: #38bdf8;
    }}
    * {{
      box-sizing: border-box;
    }}
    body {{
      margin: 0;
      min-height: 100vh;
      font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(56, 189, 248, 0.16), transparent 30%),
        radial-gradient(circle at top right, rgba(34, 197, 94, 0.18), transparent 28%),
        linear-gradient(160deg, #020617, var(--bg));
      display: grid;
      place-items: center;
      padding: 32px;
    }}
    .certificate {{
      width: min(980px, 100%);
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border);
      border-radius: 28px;
      padding: 40px;
      box-shadow: 0 30px 80px rgba(2, 6, 23, 0.45);
    }}
    .eyebrow {{
      display: inline-block;
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid rgba(34, 197, 94, 0.5);
      color: #86efac;
      font-size: 0.85rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3.4rem);
    }}
    h2 {{
      margin: 0 0 18px;
      font-size: clamp(1.3rem, 2vw, 1.8rem);
      color: var(--accent-alt);
      font-weight: 600;
    }}
    p {{
      line-height: 1.6;
      color: var(--muted);
    }}
    .grid {{
      display: grid;
      gap: 24px;
      grid-template-columns: 1.1fr 0.9fr;
      margin-top: 28px;
    }}
    .panel {{
      padding: 24px;
      border-radius: 20px;
      border: 1px solid rgba(51, 65, 85, 0.9);
      background: rgba(2, 6, 23, 0.45);
    }}
    .panel img {{
      width: 100%;
      border-radius: 18px;
      border: 1px solid rgba(51, 65, 85, 0.9);
      background: #020617;
    }}
    a {{
      color: #7dd3fc;
    }}
    @media (max-width: 760px) {{
      .certificate {{
        padding: 24px;
      }}
      .grid {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <main class="certificate">
    <div class="eyebrow">Acme Lab Completion</div>
    <h1>{html.escape(recipient_name)}</h1>
    <h2>{html.escape(track)}</h2>
    <p>
      This certificate confirms completion of the <strong>{html.escape(lab_name)}</strong>
      on <strong>{html.escape(completion_date_display)}</strong>.
    </p>
    <div class="grid">
      <section class="panel">
        <p><strong>Recipient:</strong> {html.escape(recipient_name)}</p>
        {username_line}
        <p><strong>Track:</strong> {html.escape(track)}</p>
        <p><strong>Repository:</strong> <a href="{html.escape(repo_url)}">{html.escape(repo_url)}</a></p>
        {evidence_html}
        {workflow_html}
      </section>
      <section class="panel">
        <img src="../{html.escape(badge_rel_path)}" alt="{html.escape(recipient_name)} completion badge" />
      </section>
    </div>
  </main>
</body>
</html>
"""


def render_record(
    recipient_name: str,
    github_username: str,
    track: str,
    completion_date_iso: str,
    completion_date_display: str,
    evidence_summary: str,
    repo_url: str,
    workflow_run_url: str,
    badge_file: str,
    certificate_file: str,
) -> str:
    username_line = f"- GitHub username: `@{github_username}`\n" if github_username else ""
    evidence_line = (
        evidence_summary.strip()
        if evidence_summary.strip()
        else "Completion was recorded through the repository badge workflow."
    )
    workflow_line = (
        f"- Workflow run: {workflow_run_url}\n" if workflow_run_url else ""
    )

    return f"""# Completion Award

![{recipient_name} completion badge](../badges/{badge_file})

- Recipient: `{recipient_name}`
{username_line}- Track: `{track}`
- Issued on: `{completion_date_iso}` ({completion_date_display})
- Badge file: [`../badges/{badge_file}`](../badges/{badge_file})
- Certificate file: [`../certificates/{certificate_file}`](../certificates/{certificate_file})
- Repository: {repo_url}
{workflow_line}
## Evidence Summary

{evidence_line}
"""


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="\n")


def write_github_output(path: Path, outputs: dict[str, str]) -> None:
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for key, value in outputs.items():
            if "\n" in value:
                handle.write(f"{key}<<EOF\n{value}\nEOF\n")
            else:
                handle.write(f"{key}={value}\n")


def main() -> int:
    args = parse_args()
    completion_date_iso, completion_date_display = normalize_date(args.completion_date)
    slug = build_slug(args, completion_date_iso)

    output_root = Path(args.output_root)
    badge_dir = output_root / "badges"
    certificate_dir = output_root / "certificates"
    record_dir = output_root / "records"

    badge_file = f"{slug}.svg"
    certificate_file = f"{slug}.html"
    record_file = f"{slug}.md"

    badge_path = badge_dir / badge_file
    certificate_path = certificate_dir / certificate_file
    record_path = record_dir / record_file

    badge_svg = render_badge(
        recipient_name=args.recipient_name,
        github_username=args.github_username.strip(),
        track=args.track,
        completion_date_display=completion_date_display,
        slug=slug,
    )
    certificate_html = render_certificate(
        recipient_name=args.recipient_name,
        github_username=args.github_username.strip(),
        track=args.track,
        completion_date_display=completion_date_display,
        evidence_summary=args.evidence_summary.strip(),
        lab_name=args.lab_name,
        repo_url=args.repo_url,
        workflow_run_url=args.workflow_run_url,
        badge_rel_path=f"badges/{badge_file}",
    )
    record_md = render_record(
        recipient_name=args.recipient_name,
        github_username=args.github_username.strip(),
        track=args.track,
        completion_date_iso=completion_date_iso,
        completion_date_display=completion_date_display,
        evidence_summary=args.evidence_summary.strip(),
        repo_url=args.repo_url,
        workflow_run_url=args.workflow_run_url,
        badge_file=badge_file,
        certificate_file=certificate_file,
    )

    write_file(badge_path, badge_svg)
    write_file(certificate_path, certificate_html)
    write_file(record_path, record_md)

    badge_markdown = f"![{args.recipient_name} completion badge]({badge_path.as_posix()})"
    outputs = {
        "badge_slug": slug,
        "badge_path": badge_path.as_posix(),
        "certificate_path": certificate_path.as_posix(),
        "record_path": record_path.as_posix(),
        "badge_markdown": badge_markdown,
    }

    if args.github_output.strip():
        write_github_output(Path(args.github_output), outputs)

    print(f"Generated badge: {badge_path.as_posix()}")
    print(f"Generated certificate: {certificate_path.as_posix()}")
    print(f"Generated record: {record_path.as_posix()}")
    print(f"Embed snippet: {badge_markdown}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
