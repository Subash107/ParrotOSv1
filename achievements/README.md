# Completion Awards

This folder stores generated completion assets for people who finish the lab.

## What gets created

- `badges/` contains personal SVG completion badges.
- `certificates/` contains certificate-style HTML pages.
- `records/` contains markdown award records with links and evidence notes.

## How to award a badge

1. Open the `Actions` tab in GitHub.
2. Select the `award-completion-badge` workflow.
3. Click `Run workflow`.
4. Fill in the recipient name, track, and optional GitHub username or evidence summary.
5. After the workflow finishes, it will commit the generated assets back into this folder and upload them as workflow artifacts.

## Suggested completion evidence

- Recon notes or scan output stored in `reports/`
- A validated exploit chain from the lab
- A clean write-up using the docs in `docs/reports/`
- Screenshots, payloads, or Burp/ZAP exports that support the completion claim
