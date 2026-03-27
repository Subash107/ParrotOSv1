#!/usr/bin/env python3
"""Helpers for loading shared lab challenge manifests and profiles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def default_labs_root() -> Path:
  return Path(__file__).resolve().parent.parent / "labs"


def read_json(path: Path) -> dict[str, Any]:
  return json.loads(path.read_text(encoding="utf-8"))


def load_profile(profile_name: str, labs_root: Path | None = None) -> dict[str, Any]:
  root = labs_root or default_labs_root()
  path = root / "profiles" / f"{profile_name}.json"

  if not path.exists():
    raise FileNotFoundError(f"Unknown lab profile: {profile_name}")

  profile = read_json(path)
  profile["path"] = path.as_posix()
  return profile


def load_challenge(challenge_id: str, labs_root: Path | None = None) -> dict[str, Any]:
  root = labs_root or default_labs_root()
  matches = sorted((root / "challenges").glob("*.json"))

  for path in matches:
    challenge = read_json(path)
    if challenge.get("id") == challenge_id:
      challenge["path"] = path.as_posix()
      return challenge

  raise FileNotFoundError(f"Unknown challenge id: {challenge_id}")


def load_challenges(challenge_ids: list[str], labs_root: Path | None = None) -> list[dict[str, Any]]:
  return [load_challenge(challenge_id, labs_root) for challenge_id in challenge_ids]
