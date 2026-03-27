#!/usr/bin/env python3
"""Capture and validate a lab scenario from shared challenge manifests."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from lab_catalog import default_labs_root, load_challenges, load_profile


def write_text(path: Path, text: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(text, encoding="utf-8")


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


def encode_jwt_segment(data: dict[str, Any]) -> str:
  raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
  return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def sign_jwt(secret: str, payload: dict[str, Any]) -> str:
  header = {"alg": "HS256", "typ": "JWT"}
  encoded_header = encode_jwt_segment(header)
  encoded_payload = encode_jwt_segment(payload)
  signing_input = f"{encoded_header}.{encoded_payload}".encode("utf-8")
  signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
  encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
  return f"{encoded_header}.{encoded_payload}.{encoded_signature}"


def rel(path: Path, base: Path) -> str:
  try:
    return path.relative_to(base).as_posix()
  except ValueError:
    return path.as_posix()


def render_headers(status: int, reason: str, headers: Any) -> str:
  lines = [f"HTTP/1.1 {status} {reason}"]
  for key, value in headers.items():
    lines.append(f"{key}: {value}")
  return "\n".join(lines) + "\n"


class NoRedirectHandler(request.HTTPRedirectHandler):
  def http_error_301(self, req, fp, code, msg, headers):
    return fp

  def http_error_302(self, req, fp, code, msg, headers):
    return fp

  def http_error_303(self, req, fp, code, msg, headers):
    return fp

  def http_error_307(self, req, fp, code, msg, headers):
    return fp

  def http_error_308(self, req, fp, code, msg, headers):
    return fp


def http_capture(
  *,
  url: str,
  method: str = "GET",
  headers: dict[str, str] | None = None,
  data: bytes | None = None,
  timeout: int = 15,
  follow_redirects: bool = True,
) -> tuple[int | None, str, str]:
  req = request.Request(url, data=data, headers=headers or {}, method=method)
  opener = request.build_opener() if follow_redirects else request.build_opener(NoRedirectHandler())

  try:
    with opener.open(req, timeout=timeout) as response:
      body = response.read().decode("utf-8", errors="replace")
      return response.getcode(), render_headers(response.status, response.reason, response.headers), body
  except error.HTTPError as exc:
    body = exc.read().decode("utf-8", errors="replace")
    return exc.code, render_headers(exc.code, exc.reason, exc.headers), body
  except Exception as exc:  # noqa: BLE001
    return None, "", str(exc)


def capture_response(
  *,
  url: str,
  headers_path: Path,
  body_path: Path,
  status_path: Path,
  method: str = "GET",
  headers: dict[str, str] | None = None,
  data: bytes | None = None,
  follow_redirects: bool = True,
) -> bool:
  status, header_text, body = http_capture(
    url=url,
    method=method,
    headers=headers,
    data=data,
    follow_redirects=follow_redirects,
  )

  write_text(headers_path, header_text)
  write_text(body_path, body)
  write_text(status_path, str(status) if status is not None else "request_failed")
  return status is not None


def capture_storage_env(raw_dir: Path, compose_file: Path) -> bool:
  status_path = raw_dir / "storage_env.status.txt"
  env_path = raw_dir / "storage_env.txt"

  command = [
    "docker",
    "compose",
    "-f",
    str(compose_file),
    "exec",
    "-T",
    "storage",
    "env",
  ]

  try:
    result = subprocess.run(
      command,
      check=False,
      capture_output=True,
      text=True,
    )
  except OSError as exc:
    write_text(env_path, str(exc))
    write_text(status_path, "docker_exec_failed")
    return False

  output = result.stdout if result.stdout else result.stderr
  write_text(env_path, output)
  write_text(status_path, "0" if result.returncode == 0 else "docker_exec_failed")
  return result.returncode == 0


def capture_live_evidence(args: argparse.Namespace, raw_dir: Path) -> int:
  failures = 0

  service_checks = [
    (f"{args.app_url}/", "app_home", "body.txt"),
    (f"{args.app_url}/health", "app_health", "body.txt"),
    (f"{args.api_url}/health", "api_health", "body.txt"),
    (f"{args.admin_url}/health", "admin_health", "body.txt"),
    (f"{args.storage_console_url}/", "storage_console_home", "body.txt"),
    (f"{args.storage_api_url}/public-assets/security-note.txt", "storage_public_object", "body.txt"),
  ]

  for url, stem, body_suffix in service_checks:
    success = capture_response(
      url=url,
      headers_path=raw_dir / f"{stem}.headers.txt",
      body_path=raw_dir / f"{stem}.{body_suffix}",
      status_path=raw_dir / f"{stem}.status.txt",
    )
    if not success:
      failures += 1

  login_request = {"username": "alice", "password": "welcome123"}
  write_text(raw_dir / "login_request.json", json.dumps(login_request))
  success = capture_response(
    url=f"{args.api_url}/login",
    method="POST",
    headers={"Content-Type": "application/json"},
    data=json.dumps(login_request).encode("utf-8"),
    headers_path=raw_dir / "login_response.headers.txt",
    body_path=raw_dir / "login_response.json",
    status_path=raw_dir / "login_response.status.txt",
  )
  if not success:
    failures += 1

  admin_login_request = {"username": "admin", "password": "adminpass"}
  write_text(raw_dir / "admin_login_request.json", json.dumps(admin_login_request))
  success = capture_response(
    url=f"{args.api_url}/login",
    method="POST",
    headers={"Content-Type": "application/json"},
    data=json.dumps(admin_login_request).encode("utf-8"),
    headers_path=raw_dir / "admin_login_response.headers.txt",
    body_path=raw_dir / "admin_login_response.json",
    status_path=raw_dir / "admin_login_response.status.txt",
  )
  if not success:
    failures += 1

  admin_login_response = read_json(raw_dir / "admin_login_response.json")
  admin_token = str(admin_login_response.get("token", ""))
  if admin_token:
    success = capture_response(
      url=f"{args.api_url}/api/admin",
      headers={"Authorization": f"Bearer {admin_token}"},
      headers_path=raw_dir / "api_admin_legit.headers.txt",
      body_path=raw_dir / "api_admin_legit.json",
      status_path=raw_dir / "api_admin_legit.status.txt",
    )
  else:
    write_text(raw_dir / "api_admin_legit.headers.txt", "")
    write_text(raw_dir / "api_admin_legit.json", json.dumps({"error": "admin login did not return a token"}, indent=2))
    write_text(raw_dir / "api_admin_legit.status.txt", "request_failed")
    success = False
  if not success:
    failures += 1

  app_login_form = parse.urlencode(
    {
      "username": "alice",
      "password": "welcome123",
    }
  ).encode("utf-8")
  success = capture_response(
    url=f"{args.app_url}/login",
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data=app_login_form,
    headers_path=raw_dir / "app_login_response.headers.txt",
    body_path=raw_dir / "app_login_response.body.txt",
    status_path=raw_dir / "app_login_response.status.txt",
    follow_redirects=False,
  )
  if not success:
    failures += 1

  forged_payload = {
    "sub": 1,
    "username": "alice",
    "role": "admin",
    "department": "engineering",
  }
  forged_token = sign_jwt(args.forged_jwt_secret, forged_payload)
  write_text(raw_dir / "forged_admin_payload.json", json.dumps(forged_payload, indent=2))
  write_text(raw_dir / "forged_admin_token.txt", forged_token)
  success = capture_response(
    url=f"{args.api_url}/api/admin",
    headers={"Authorization": f"Bearer {forged_token}"},
    headers_path=raw_dir / "api_admin_forged.headers.txt",
    body_path=raw_dir / "api_admin_forged.json",
    status_path=raw_dir / "api_admin_forged.status.txt",
  )
  if not success:
    failures += 1

  for user_id in (1, 2, 3):
    success = capture_response(
      url=f"{args.api_url}/api/user?id={user_id}",
      headers_path=raw_dir / f"idor_user_{user_id}.headers.txt",
      body_path=raw_dir / f"idor_user_{user_id}.json",
      status_path=raw_dir / f"idor_user_{user_id}.status.txt",
    )
    if not success:
      failures += 1

  success = capture_response(
    url=f"{args.admin_url}/export",
    headers={"role": "admin"},
    headers_path=raw_dir / "admin_export.headers.txt",
    body_path=raw_dir / "admin_export.json",
    status_path=raw_dir / "admin_export.status.txt",
  )
  if not success:
    failures += 1

  reflected_payload = "<script>alert(1)</script>"
  write_text(raw_dir / "reflected_xss_payload.txt", reflected_payload)
  reflected_query = parse.urlencode({"bio": reflected_payload})
  success = capture_response(
    url=f"{args.app_url}/profile?{reflected_query}",
    headers_path=raw_dir / "reflected_xss.headers.txt",
    body_path=raw_dir / "reflected_xss.html",
    status_path=raw_dir / "reflected_xss.status.txt",
  )
  if not success:
    failures += 1

  stored_payload = "<img src=x onerror=alert(1)>"
  write_text(raw_dir / "stored_xss_payload.txt", stored_payload)
  stored_body = parse.urlencode(
    {
      "displayName": "automation-python",
      "content": stored_payload,
    }
  ).encode("utf-8")
  success = capture_response(
    url=f"{args.app_url}/comment",
    method="POST",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data=stored_body,
    headers_path=raw_dir / "stored_xss_post.headers.txt",
    body_path=raw_dir / "stored_xss_post.body.txt",
    status_path=raw_dir / "stored_xss_post.status.txt",
  )
  if not success:
    failures += 1

  success = capture_response(
    url=f"{args.app_url}/",
    headers_path=raw_dir / "stored_xss_home.headers.txt",
    body_path=raw_dir / "stored_xss_home.html",
    status_path=raw_dir / "stored_xss_home.status.txt",
  )
  if not success:
    failures += 1

  success = capture_response(
    url=f"{args.api_url}/api/comments",
    headers_path=raw_dir / "stored_xss_comments.headers.txt",
    body_path=raw_dir / "stored_xss_comments.json",
    status_path=raw_dir / "stored_xss_comments.status.txt",
  )
  if not success:
    failures += 1

  success = capture_response(
    url=f"{args.storage_console_url}/",
    headers_path=raw_dir / "storage_console.headers.txt",
    body_path=raw_dir / "storage_console.html",
    status_path=raw_dir / "storage_console.status.txt",
  )
  if not success:
    failures += 1

  success = capture_response(
    url=f"{args.storage_api_url}/public-assets/security-note.txt",
    headers_path=raw_dir / "storage_public_object_check.headers.txt",
    body_path=raw_dir / "storage_public_object_check.txt",
    status_path=raw_dir / "storage_public_object_check.status.txt",
  )
  if not success:
    failures += 1

  if not capture_storage_env(raw_dir, Path(args.compose_file)):
    failures += 1

  return failures


def get_nested_value(data: dict[str, Any], dotted_path: str) -> Any:
  current: Any = data
  for part in dotted_path.split("."):
    if not isinstance(current, dict) or part not in current:
      return None
    current = current[part]
  return current


def get_cookie_attributes(headers_text: str, cookie_name: str) -> dict[str, Any]:
  cookie_prefix = f"set-cookie: {cookie_name}="

  for line in headers_text.splitlines():
    lowered = line.lower()
    if not lowered.startswith(cookie_prefix):
      continue

    raw_value = line.split(":", 1)[1].strip()
    parts = [part.strip() for part in raw_value.split(";") if part.strip()]
    attributes: dict[str, Any] = {"raw": raw_value}

    for part in parts[1:]:
      if "=" in part:
        key, value = part.split("=", 1)
        attributes[key.lower()] = value
      else:
        attributes[part.lower()] = True

    return attributes

  return {}


def evaluate_service_checks(report_root: Path, profile: dict[str, Any]) -> list[dict[str, Any]]:
  services: list[dict[str, Any]] = []

  for service in profile.get("service_checks", []):
    stem = service["stem"]
    status_path = report_root / "raw" / f"{stem}.status.txt"
    body_path = report_root / "raw" / f"{stem}.body.txt"
    status_code = read_status_code(status_path)
    services.append(
      {
        "name": service["name"],
        "status_code": status_code,
        "healthy": status_code == service["expected_status"],
        "expected_status": service["expected_status"],
        "evidence": [
          rel(status_path, report_root),
          rel(body_path, report_root),
        ],
      }
    )

  return services


def evaluate_challenge(report_root: Path, challenge: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
  validator = challenge["validator"]
  kind = validator["kind"]
  details: dict[str, Any] = {}
  vulnerable = False

  if kind == "weak_jwt":
    response = read_json(report_root / validator["response_path"])
    token = str(response.get("token", ""))
    payload = decode_jwt_payload(token)
    required_claims = validator.get("required_claims", [])
    missing_claims = validator.get("missing_claims", [])
    vulnerable = bool(token)
    vulnerable = vulnerable and all(claim in payload for claim in required_claims)
    vulnerable = vulnerable and all(claim not in payload for claim in missing_claims)
    details["jwt_payload"] = payload
  elif kind == "idor_user_records":
    users = [read_json(report_root / item) for item in validator.get("user_paths", [])]
    unique_users = {user.get("username") for user in users if user}
    required_fields = validator.get("required_fields", [])
    vulnerable = len(unique_users) >= validator.get("minimum_unique_users", 1)
    vulnerable = vulnerable and all(
      all(field in user for field in required_fields)
      for user in users
      if user
    )
    details["unique_users"] = sorted(item for item in unique_users if item)
  elif kind == "admin_export":
    response = read_json(report_root / validator["response_path"])
    status_code = read_status_code(report_root / validator["status_path"])
    array_value = response.get(validator["required_array_key"])
    secret_value = get_nested_value(response, validator["required_secret_path"])
    vulnerable = status_code == 200 and isinstance(array_value, list) and bool(secret_value)
    details["status_code"] = status_code
  elif kind == "payload_reflection":
    payload = read_text(report_root / validator["payload_path"])
    html = read_text(report_root / validator["content_path"])
    vulnerable = bool(payload) and payload in html
  elif kind == "stored_payload":
    payload = read_text(report_root / validator["payload_path"])
    html = read_text(report_root / validator["html_path"])
    comments = read_json(report_root / validator["comments_path"]).get(validator["comments_key"], [])
    vulnerable = bool(payload) and (
      payload in html
      or any(
        payload == comment.get("content")
        for comment in comments
        if isinstance(comment, dict)
      )
    )
    details["comment_count"] = len(comments) if isinstance(comments, list) else 0
  elif kind == "storage_exposure":
    console_status = read_status_code(report_root / validator["console_status_path"])
    public_status = read_status_code(report_root / validator["public_status_path"])
    storage_env = read_text(report_root / validator["env_path"])
    default_creds = "MINIO_ROOT_USER=minioadmin" in storage_env and "MINIO_ROOT_PASSWORD=minioadmin" in storage_env
    public_access = console_status == 200 and public_status == 200
    vulnerable = public_access or default_creds
    details["default_credentials"] = default_creds
    details["public_access"] = public_access
  elif kind == "session_cookie":
    headers_text = read_text(report_root / validator["headers_path"])
    cookie_attributes = get_cookie_attributes(headers_text, validator["cookie_name"])
    missing_attributes = [item.lower() for item in validator.get("missing_attributes", [])]
    vulnerable = bool(cookie_attributes)
    vulnerable = vulnerable and all(attribute not in cookie_attributes for attribute in missing_attributes)
    details["cookie_attributes"] = cookie_attributes
  elif kind == "forged_admin_api_access":
    response = read_json(report_root / validator["response_path"])
    status_code = read_status_code(report_root / validator["status_path"])
    role_value = get_nested_value(response, validator["required_role_path"])
    users_value = response.get(validator["required_array_key"])
    vulnerable = status_code == 200 and role_value == validator["required_role_value"] and isinstance(users_value, list)
    details["status_code"] = status_code
    details["requested_role"] = role_value
  elif kind == "admin_api_sensitive_exposure":
    response = read_json(report_root / validator["response_path"])
    status_code = read_status_code(report_root / validator["status_path"])
    secret_value = get_nested_value(response, validator["required_secret_path"])
    users = response.get(validator["required_array_key"], [])
    user_field = validator["required_user_field"]
    user_field_count = sum(
      1
      for user in users
      if isinstance(user, dict) and user_field in user
    )
    vulnerable = status_code == 200 and bool(secret_value) and user_field_count > 0
    details["status_code"] = status_code
    details["user_field_count"] = user_field_count
  else:
    raise ValueError(f"Unsupported validator kind: {kind}")

  result = {
    "id": challenge["id"],
    "title": challenge["title"],
    "severity": challenge["severity"],
    "summary": challenge["summary"],
    "result": "Vulnerable" if vulnerable else "Not confirmed",
    "track": challenge["track"],
    "level": challenge["level"],
    "points": challenge["points"],
    "reward": challenge["reward"],
    "flag": challenge["flag"],
    "why_it_matters": challenge["why_it_matters"],
    "manual_steps": challenge["manual_steps"],
    "hint_ladder": challenge["hint_ladder"],
    "what_to_learn": challenge["what_to_learn"],
    "remediation": challenge["remediation"],
    "evidence": challenge["evidence"],
    "validator_kind": kind,
    "details": details,
  }

  return result, details


def build_summary(
  *,
  report_root: Path,
  profile: dict[str, Any],
  challenges: list[dict[str, Any]],
  capture_source: str,
  capture_failures: int,
) -> dict[str, Any]:
  challenge_expectations = profile.get("challenge_expectations", {})
  services = evaluate_service_checks(report_root, profile)
  results: list[dict[str, Any]] = []
  jwt_payload: dict[str, Any] = {}

  for challenge in challenges:
    result, details = evaluate_challenge(report_root, challenge)
    expected_result = challenge_expectations.get(challenge["id"])
    result["expected_result"] = expected_result
    result["matches_profile"] = expected_result is None or result["result"] == expected_result
    results.append(result)
    if details.get("jwt_payload"):
      jwt_payload = details["jwt_payload"]

  summary = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ"),
    "report_root": report_root.as_posix(),
    "profile": {
      "id": profile["id"],
      "name": profile["name"],
      "description": profile["description"],
    },
    "capture": {
      "source": capture_source,
      "failures": capture_failures,
    },
    "services": services,
    "jwt_payload": jwt_payload,
    "challenge_results": results,
    "findings": [
      {
        "title": item["title"],
        "severity": item["severity"],
        "result": item["result"],
        "summary": item["summary"],
        "evidence": item["evidence"],
      }
      for item in results
    ],
  }

  write_text(report_root / "summary.json", json.dumps(summary, indent=2))
  write_text(report_root / "challenge_results.json", json.dumps(results, indent=2))
  return summary


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser()
  parser.add_argument("--report-root", required=True)
  parser.add_argument("--profile", default="vulnerable")
  parser.add_argument(
    "--capture-source",
    choices=("live", "existing"),
    default="live",
    help="Capture fresh evidence from running services or validate an existing report root.",
  )
  parser.add_argument("--labs-root", default=str(default_labs_root()))
  parser.add_argument("--compose-file", default="docker-compose.yml")
  parser.add_argument("--app-url", default="http://localhost:8080")
  parser.add_argument("--api-url", default="http://localhost:8081")
  parser.add_argument("--admin-url", default="http://localhost:8082")
  parser.add_argument("--storage-api-url", default="http://localhost:9000")
  parser.add_argument("--storage-console-url", default="http://localhost:9001")
  parser.add_argument("--forged-jwt-secret", default="secret123")
  return parser.parse_args()


def main() -> int:
  args = parse_args()
  report_root = Path(args.report_root).resolve()
  raw_dir = report_root / "raw"
  raw_dir.mkdir(parents=True, exist_ok=True)

  profile = load_profile(args.profile, Path(args.labs_root))
  challenges = load_challenges(profile.get("challenge_ids", []), Path(args.labs_root))

  capture_failures = 0
  if args.capture_source == "live":
    capture_failures = capture_live_evidence(args, raw_dir)

  build_summary(
    report_root=report_root,
    profile=profile,
    challenges=challenges,
    capture_source=args.capture_source,
    capture_failures=capture_failures,
  )

  return capture_failures


if __name__ == "__main__":
  sys.exit(main())
