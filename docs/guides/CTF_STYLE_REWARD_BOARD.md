# CTF-Style Reward Board

This lab now supports a CTF-style training layer on top of the bug bounty workflow.

## Levels

### Beginner

These are direct proof challenges with simple browser or request changes:

- IDOR on `GET /api/user?id=`
- reflected XSS on `/profile`
- MinIO public exposure and default credentials

### Intermediate

These require slightly deeper reasoning or tampering:

- weak JWT design review on `/login`
- header-based admin export bypass
- stored XSS in the comment feed

### Advanced

These are intended as self-driven bonus chains after the main board is cleared:

- forge an admin JWT and access `/api/admin`
- demonstrate how stored XSS can be chained to the readable `session` cookie
- combine IDOR and admin export leaks into a broader compromise narrative

## Flags

Each main challenge has a stable training flag generated into `WALKTHROUGH_FLAGS.md` in every test run folder.

Example output files:

- `LAB_REWARD_SCORECARD.md`
- `FILLED_BUG_BOUNTY_REPORT.md`
- `WALKTHROUGH_FLAGS.md`

## Suggested Use

1. Run the automated suite.
2. Open the latest run folder under `reports/`.
3. Start with Beginner flags.
4. Move to Intermediate flags.
5. Attempt Advanced bonus chains only after you can reproduce the core issues manually.

## Teaching Goal

The idea is to make the project feel like:

- a bug bounty practice lab
- a repeatable evidence generator
- a guided CTF progression board

without turning it into a toy challenge that hides the reporting and impact-writing side of bug bounty work.
