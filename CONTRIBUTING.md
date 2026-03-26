# Contributing to ParrotOS Bug Hunting Local Lab

Thanks for helping improve this training lab.

This repository is intentionally vulnerable for learning purposes, so good contributions keep the lab realistic, well documented, and safe to run in isolated environments.

## Good Ways to Contribute

- Improve lab documentation, walkthroughs, and reporting templates.
- Add repeatable validation scripts for ParrotOS, Windows, or containerized environments.
- Improve contributor onboarding, issue triage, and release presentation.
- Fix broken setup steps, workflow regressions, or reproducibility problems.
- Propose new training tracks, badge ideas, or guided scenarios.

## Before You Start

- Use GitHub Discussions for questions, ideas, and learning-oriented conversations.
- Use Issues for confirmed bugs, actionable enhancements, or clearly scoped work.
- Keep all work focused on local training. Do not propose exposing this lab to the public internet.

## Recommended Workflow

1. Open or join a Discussion if the idea is still forming.
2. Open an Issue if the work is concrete and actionable.
3. Create a branch from `main`.
4. Make small, reviewable changes with clear evidence.
5. Open a pull request with a short summary, validation notes, and any screenshots or report output that help reviewers.

Suggested branch names:

- `docs/<topic>`
- `fix/<topic>`
- `feat/<topic>`
- `ci/<topic>`

## Local Validation

Run the checks that match your change when possible:

- `docker compose up -d --build`
- `make remote-tool-inventory`
- `scripts/windows/run_local_lab_tests.bat`

If you cannot run a check, say so clearly in the pull request.

## Pull Request Expectations

- Keep changes scoped to one improvement at a time.
- Update documentation when behavior, workflow, or repo structure changes.
- Include reproduction steps for bugs.
- Include test or validation notes for scripts, workflows, and templates.
- Avoid committing secrets, real target data, or unsafe internet-facing configurations.

## Collaboration Tips

- Tag issues with labels like `good first issue`, `help wanted`, `documentation`, `windows`, or `automation` when relevant.
- If you pair with someone, use co-authored commits so both contributors get proper credit.
- If your change starts as a question, turn it into a Discussion first and link it from the PR later.

## Safety

This repository is for private training and controlled demos only. By contributing, you agree to keep the project educational, isolated, and clearly documented.
