# Bug Bounty Rewards Lab

This project can be used as a private bug bounty learning lab with track-based rewards, repeatable local tests, and auto-generated practice reports.

## Goal

Use the lab to learn how to:

- identify common bug bounty finding classes
- reproduce them cleanly
- collect evidence
- write reports with impact and remediation

This is a training lab only. It is not connected to a real bounty payout program.

## Reward Tracks

| Level | Track | Challenge | Reward | Points | Training Flag |
| --- | --- | --- | --- | --- | --- |
| Beginner | Baseline | Bring the lab online and verify all services | `Ready To Hunt` | 50 | `ACME{lab_online_baseline}` |
| Intermediate | Auth And Token Abuse | Weak JWT configuration on `/login` | `Token Breaker` | 100 | `ACME{jwt_role_claim_without_expiry}` |
| Beginner | Access Control | IDOR on `/api/user?id=` | `Object Explorer` | 150 | `ACME{idor_user_records_exposed}` |
| Intermediate | Access Control | Admin export unlocked by `role: admin` | `Header Impersonator` | 200 | `ACME{trusted_client_role_header}` |
| Beginner | Client-side Injection | Reflected XSS on `/profile` | `Link Crafter` | 150 | `ACME{profile_bio_reflection_xss}` |
| Intermediate | Client-side Injection | Stored XSS in comment feed | `Comment Ghost` | 175 | `ACME{stored_comment_payload_rendered}` |
| Beginner | Secrets And Storage | MinIO exposure and default credentials | `Bucket Diver` | 125 | `ACME{public_bucket_default_minio_creds}` |

## Difficulty Levels

- `Beginner`: direct browser proof or very small request changes
- `Intermediate`: requires header tampering, token review, or persistence validation
- `Advanced`: challenge chaining after the main board is complete

Advanced bonus flags:

- `ACME{jwt_forgery_to_admin_api}`
- `ACME{comment_xss_to_session_theft_path}`

## Recommended Learning Order

1. Service health and baseline browsing
2. IDOR on `/api/user?id=`
3. Header-based admin export bypass
4. Reflected XSS
5. Stored XSS
6. JWT review and token abuse
7. MinIO storage review

## Best Workflow

1. Start the lab locally.
2. Run the Windows test suite:

   ```powershell
   .\scripts\windows\run_local_lab_tests.bat
   ```

3. Open the generated files in the run folder:
   - `AUTOMATED_WINDOWS_TEST_REPORT.md`
   - `FILLED_BUG_BOUNTY_REPORT.md`
   - `LAB_REWARD_SCORECARD.md`
   - `WALKTHROUGH_FLAGS.md`
4. Reproduce the same findings manually in the browser, PowerShell, Burp, or ZAP.
5. Compare your own notes with the generated evidence under `raw/`.

## What To Practice

- changing only one request parameter at a time
- saving screenshots with the URL visible
- keeping request and response evidence
- describing impact in plain language
- separating proof, impact, and remediation in a report

## Success Criteria

You are using the lab well if you can:

- explain why each finding exists
- reproduce it manually without automation
- describe impact without overstating it
- recommend a realistic fix
- write a clean report for at least one finding from scratch
- clear the Beginner board before moving to the Advanced bonus flags
