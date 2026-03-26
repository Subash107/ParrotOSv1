# ParrotOS Tooling And Bug Testing Guide

This guide captures the ParrotOS-side testing state verified against the local `localbugbountylabendtoend` environment on March 26, 2026.

## Verified Environment

- ParrotOS host was reachable over SSH at `172.28.61.113`
- Remote project path: `/home/subash/localbugbountylabendtoend`
- `docker compose ps` showed the `app`, `api`, `admin`, `database`, and `storage` services up
- Host aliases for `app.acme.local`, `api.acme.local`, `admin.acme.local`, and `storage.acme.local` resolved to `127.0.0.1`
- Basic endpoint checks returned `200` for the main application, API health, admin health, public MinIO object, and MinIO console

## Tool Check Summary

The following tools were checked from ParrotOS by verifying the command path and, where practical, a version banner.

| Tool | Status | Verification | Notes |
| --- | --- | --- | --- |
| `nmap` | Present | `Nmap version 7.95` | Good for exposed-port and service discovery |
| `theHarvester` | Missing | `command -v` failed | Not currently available |
| `nikto` | Present | `Nikto 2.6.0` | Suitable for basic web checks on the app, API, and admin targets |
| `hydra` | Present | `Hydra v9.5` | Suitable for credential attack demos against the login flow |
| `john` | Missing | `command -v` failed | Not currently available |
| `msfconsole` | Present | command path found | Installed, but not required for the core lab workflow |
| `zaproxy` | Present | `ZAP 2.17.0` detected | GUI launch failed in headless mode; use daemon/X11 mode |
| `burpsuite` | Present | command path found | GUI tool, so verify with a desktop or forwarded display |
| `curl` | Present | `curl 8.14.1` | Primary tool for direct HTTP probing |
| `jq` | Missing | `command -v` failed | JSON pretty-printing is not available yet |
| `python3` | Present | `Python 3.13.5` | Useful for helper scripts and token work |
| `docker` | Present | `Docker version 26.1.5+dfsg1` | Required for the lab stack |
| `docker-compose` | Present | `Docker Compose version 2.26.1-4` | Lab stack management works |
| `gobuster` | Present | `3.6` | Optional content discovery tool |
| `ffuf` | Present | `ffuf version 2.1.0-dev` | Optional fuzzing tool |
| `sqlmap` | Present | `1.9.6#stable` | Installed but not central to this lab's main findings |
| `whatweb` | Present | `WhatWeb version 0.5.5` | Useful for lightweight fingerprinting |
| `feroxbuster` | Present | `feroxbuster 2.13.1` | Optional content discovery tool |
| `nuclei` | Missing | `command -v` failed | Not currently available |
| `dirsearch` | Present | help banner returned | Optional content discovery tool |
| `dirb` | Present | banner returned | Optional content discovery tool |
| `hashcat` | Present | `v6.2.6` | Installed but not necessary for the main demo path |
| `wfuzz` | Present | `3.1.0` banner returned | Optional fuzzing tool |
| `amass` | Missing | `command -v` failed | Not currently available |
| `subfinder` | Missing | `command -v` failed | Not currently available |
| `rustscan` | Missing | `command -v` failed | Not currently available |

## Best Links For Bug Testing

These are the main targets to hit from ParrotOS or through Burp/ZAP.

### Front end

| Target | Purpose | What to test |
| --- | --- | --- |
| `http://app.acme.local:8080/` | Main portal | Login flow, readable JWT cookie, stored XSS in the comment feed |
| `http://app.acme.local:8080/profile?bio=<payload>` | Profile preview | Reflected XSS through the `bio` query parameter |
| `http://app.acme.local:8080/logout` | Session reset | Clear the demo session during testing |

### API

| Target | Purpose | What to test |
| --- | --- | --- |
| `POST http://api.acme.local:8081/login` | Login endpoint | Weak JWT handling, no expiration, predictable role tampering workflow |
| `GET http://api.acme.local:8081/api/user?id=1` | Baseline user lookup | Sensitive data exposure pattern |
| `GET http://api.acme.local:8081/api/user?id=3` | Admin record via IDOR | Confirm password/API key disclosure |
| `GET http://api.acme.local:8081/api/admin` | Admin-only data | Use a forged admin JWT in `Authorization: Bearer <token>` |
| `POST http://api.acme.local:8081/comment` | Comment storage | Store XSS payloads and test identity behavior |
| `GET http://api.acme.local:8081/api/comments` | Comment retrieval | Confirm stored content is returned unsanitized |
| `GET http://api.acme.local:8081/health` | Health check | Quick reachability test |

### Admin panel

| Target | Purpose | What to test |
| --- | --- | --- |
| `http://admin.acme.local:8082/` | Admin dashboard | Broken access control with the `role: admin` header |
| `http://admin.acme.local:8082/export` | JSON export | Sensitive bulk data export with only `role: admin` |
| `http://admin.acme.local:8082/health` | Health check | Quick reachability test |

### Storage

| Target | Purpose | What to test |
| --- | --- | --- |
| `http://storage.acme.local:9001/` | MinIO console | Default credentials and console access |
| `http://storage.acme.local:9000/public-assets/security-note.txt` | Public object | Public bucket/object exposure |

## Recommended Test Flow From ParrotOS

1. Confirm the stack and tooling:

   ```bash
   bash scripts/remote/remote_tool_inventory.sh
   ```

2. Run the methodology/tool readiness check:

   ```bash
   bash scripts/remote/remote_methodology_check.sh
   ```

3. Run recon against the exposed services:

   ```bash
   bash scripts/remote/remote_recon_scan.sh
   ```

4. Validate the exploit chain:

   ```bash
   bash scripts/remote/remote_exploit.sh
   ```

5. Work through the browser-proxy flow with:

   - `docs/guides/BURP_ZAP_WALKTHROUGH.md`

## Useful Direct Requests

### IDOR check

```bash
curl "http://api.acme.local:8081/api/user?id=3"
```

### Admin header bypass

```bash
curl -H "role: admin" "http://admin.acme.local:8082/export"
```

### Login and JWT capture

```bash
curl -s -X POST "http://api.acme.local:8081/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"welcome123"}'
```

### Forge a token locally

```bash
python3 tools/forge_admin_jwt.py
```

### Public bucket check

```bash
curl "http://storage.acme.local:9000/public-assets/security-note.txt"
```

## Notes And Gaps

- `zaproxy` is installed, but a normal GUI launch failed in the headless check. Use it with a desktop session, X11 forwarding, or daemon mode.
- `burpsuite` is installed, but it is also a GUI workflow and is best launched from a graphical session.
- `jq`, `john`, `theHarvester`, `nuclei`, `amass`, `subfinder`, and `rustscan` were not present during this check.
- The main, immediately useful tools for this lab are `curl`, `nmap`, `nikto`, `hydra`, `python3`, Burp Suite, and ZAP.
