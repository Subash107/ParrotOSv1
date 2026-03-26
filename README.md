# Acme DevSecOps Bug Bounty Simulation Lab

This project is an intentionally vulnerable multi-service lab that behaves like a small internal company platform. Docker Compose wires together the employee app, API, admin panel, MinIO object storage, and MySQL so you can practice realistic reconnaissance, chaining, and exploitation in a local environment.

## Services

- `app.acme.local` at `http://localhost:8080`
- `api.acme.local` at `http://localhost:8081`
- `admin.acme.local` at `http://localhost:8082`
- `storage.acme.local` S3 API at `http://localhost:9000`
- `storage.acme.local` console at `http://localhost:9001`
- `database` MySQL at `localhost:3306`

## Included Vulnerabilities

- Weak JWT secret: `secret123`
- JWTs have no expiration
- Role is trusted directly from the JWT payload
- IDOR on `GET /api/user?id=`
- Admin panel trusts only `role: admin`
- Stored and reflected XSS in the front end
- MinIO default credentials and anonymous public bucket access
- Overexposed admin and user data in the API and admin dashboard

## Repository Layout

```text
.
|-- admin/
|   |-- Dockerfile
|   |-- package.json
|   `-- src/admin.js
|-- api/
|   |-- Dockerfile
|   |-- package.json
|   `-- src/api.js
|-- app/
|   |-- Dockerfile
|   |-- package.json
|   `-- src/server.js
|-- docs/
|   |-- guides/
|   |   |-- BURP_ZAP_WALKTHROUGH.md
|   |   `-- METHODOLOGY.md
|   `-- reports/
|       |-- BUG_BOUNTY_REPORT.md
|       |-- BUGCROWD_TEMPLATE.md
|       |-- EXECUTIVE_REPORT.md
|       |-- FINDINGS.md
|       `-- HACKERONE_TEMPLATE.md
|-- infrastructure/
|   |-- database/init.sql
|   `-- minio/init.sh
|-- scripts/
|   `-- remote/
|-- tools/
|   |-- forge_admin_jwt.py
|   `-- parrot_os_ssh_client.py
|-- .github/workflows/security-lab.yml
`-- docker-compose.yml
```

Generated scan output and exploit artifacts are written to `reports/`.

## Bootstrap

Run the bootstrap check once on a new machine to create the `reports/` directory, verify prerequisites, validate the Compose file, and check whether your local host aliases are present.

Windows PowerShell:

```powershell
.\scripts\setup\bootstrap.ps1
```

Windows PowerShell with automatic hosts update in an elevated session:

```powershell
.\scripts\setup\bootstrap.ps1 -AddHosts
```

Linux or macOS:

```bash
bash scripts/setup/bootstrap.sh
```

Linux or macOS with automatic hosts update:

```bash
sudo bash scripts/setup/bootstrap.sh --add-hosts
```

## Documentation Map

- `docs/guides/METHODOLOGY.md` for the phase-by-phase bug bounty workflow
- `docs/guides/BURP_ZAP_WALKTHROUGH.md` for the browser-proxy walkthrough
- `docs/reports/FINDINGS.md` for the validated findings summary
- `docs/reports/BUG_BOUNTY_REPORT.md` for a formal bug bounty style report
- `docs/reports/EXECUTIVE_REPORT.md` for a leadership-friendly summary
- `docs/reports/HACKERONE_TEMPLATE.md` and `docs/reports/BUGCROWD_TEMPLATE.md` for submission-ready drafts

## How To Run

1. Add these host entries so the lab domains resolve locally.

   ```text
   127.0.0.1 app.acme.local
   127.0.0.1 api.acme.local
   127.0.0.1 admin.acme.local
   127.0.0.1 storage.acme.local
   ```

2. Start the lab.

   ```bash
   docker compose up --build
   ```

3. Open the services:

   - `http://app.acme.local:8080`
   - `http://api.acme.local:8081`
   - `http://admin.acme.local:8082`
   - `http://storage.acme.local:9001`

4. Use the default application credentials:

   - `alice / welcome123`
   - `bob / hunter2`
   - `admin / adminpass`

5. Use the MinIO default credentials:

   - `minioadmin / minioadmin`

## Common Commands

If you have `make` available, the root [Makefile](d:/ParrotOS/acme-devsecops-lab/Makefile) wraps the most common tasks:

- `make help`
- `make bootstrap`
- `make bootstrap-windows`
- `make config`
- `make build`
- `make up`
- `make down`
- `make logs`
- `make token`
- `make remote-methodology`
- `make remote-recon`

The repo also includes a root [`.editorconfig`](d:/ParrotOS/acme-devsecops-lab/.editorconfig) so editors pick up consistent formatting automatically.

## Networking Notes

- All services share the Docker Compose bridge network `acme-net`.
- The front end calls the API over the internal name `api.acme.local`.
- The admin panel and API both talk to the MySQL container internally.
- MinIO is reachable from the other services over the internal name `storage.acme.local`.

## Vulnerability Map

### Authentication flaws

- `POST /login` issues a JWT signed with `secret123`
- Tokens have no expiration
- The API trusts the `role` field embedded inside the token
- The front end stores the token in a JavaScript-readable cookie

### IDOR

- `GET /api/user?id=` returns user records directly
- No ownership or role check is performed
- Sensitive fields such as `password` and `api_key` are disclosed

### Broken admin access

- `admin.acme.local` trusts only the request header `role: admin`
- No session, token, or secondary verification is required

### XSS

- The comment feed stores raw HTML and JavaScript from `POST /comment`
- `/profile?bio=` reflects content directly back into the DOM
- The front end renders user content without sanitization

### Storage misconfiguration

- MinIO uses the default credentials `minioadmin / minioadmin`
- The `public-assets` bucket is created automatically and exposed anonymously

## Example Attack Scenarios

### 1. Stored XSS -> cookie theft -> account takeover

1. Log into `app.acme.local` as a low-privileged user.
2. Post a comment containing JavaScript in the comment form.
3. When another authenticated user loads the feed, the browser executes the payload.
4. Because the app stores the JWT in a readable `session` cookie, the payload can steal it.
5. Replay the stolen token in a browser or API client to impersonate that user.

### 2. JWT tampering -> admin API access

1. Capture a normal JWT from the `session` cookie after login.
2. Decode the payload and change `"role":"user"` to `"role":"admin"`.
3. Re-sign the token with the weak secret `secret123`.
4. Call `GET /api/admin` with `Authorization: Bearer <tampered-token>`.
5. Review the returned user list, comments, and infrastructure notes.

Example helper command if you have Node and `jsonwebtoken` available:

```bash
node -e "console.log(require('jsonwebtoken').sign({sub:1,username:'alice',role:'admin',department:'engineering'}, 'secret123'))"
```

### 3. IDOR -> admin data disclosure

1. Browse to `http://api.acme.local:8081/api/user?id=1`
2. Change the identifier to `2` and `3`
3. Observe that the API exposes every user record, including the admin account
4. Use the leaked email, password, role, and API key to pivot into other services

Example request:

```bash
curl "http://localhost:8081/api/user?id=3"
```

### 4. Broken admin header -> full access

1. Visit the admin panel directly or use `curl`
2. Add the header `role: admin`
3. The panel responds with sensitive user data and recent comments

Example request:

```bash
curl -H "role: admin" "http://localhost:8082/export"
```

### 5. Storage misconfiguration

1. Open the MinIO console on `http://localhost:9001`
2. Sign in with `minioadmin / minioadmin`
3. Browse the `public-assets` bucket or fetch the public object directly

Example request:

```bash
curl "http://localhost:9000/public-assets/security-note.txt"
```

## Example Exploit Chains

- Stored XSS in the comment feed -> steal readable session cookie -> reuse JWT -> access victim session -> tamper token role -> pull `/api/admin`
- Enumerate `GET /api/user?id=` -> leak admin user details and API key -> add `role: admin` header -> dump the admin export -> log into MinIO with default credentials
- Reflected XSS through `/profile?bio=` -> execute JavaScript in the victim browser -> steal the session cookie -> access admin-only API data after JWT tampering

## Automation

- Dockerfiles are included for `app`, `api`, and `admin`
- `.github/workflows/security-lab.yml` builds the Compose stack, runs an Nmap scan, and performs security smoke checks
- `scripts/remote/` contains helper scripts for scanning, exploitation, reporting, and Burp-driven verification
- `tools/` contains the JWT forging helper and the Parrot OS SSH client

## Cleanup

```bash
docker compose down -v
```

## Safety Note

This environment is intentionally insecure. Run it only on an isolated local machine or private lab network, and do not expose it to the public internet.
