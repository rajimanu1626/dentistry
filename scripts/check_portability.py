#!/usr/bin/env python3
"""Enforce the portability invariants defined in CLAUDE.md and the plan.

Runs in CI and as a pre-commit hook. Greps the tree (excluding allow-listed paths)
for tokens that would couple us to Supabase or any other provider.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# (regex, human-readable description, scope = file globs to apply rule against)
BANNED_PATTERNS: list[tuple[re.Pattern[str], str, tuple[str, ...]]] = [
    (
        re.compile(r"\bauth\.uid\s*\("),
        "Use current_setting('app.current_user_id')::uuid in RLS, not auth.uid().",
        ("apps/api/**/*.py", "apps/api/**/*.sql", "infra/db/**/*.sql"),
    ),
    (
        re.compile(r"\bauth\.users\b"),
        "Reference our own `users` table; never FK to auth.users (Supabase-only).",
        ("apps/api/**/*.py", "apps/api/**/*.sql", "infra/db/**/*.sql"),
    ),
    (
        re.compile(r"\bsupabase\.realtime\b|@supabase/realtime", re.IGNORECASE),
        "Supabase Realtime is non-portable; use SSE/WebSocket from FastAPI instead.",
        ("apps/**/*",),
    ),
    (
        re.compile(r"supabase/functions|edge[_-]?function", re.IGNORECASE),
        "Edge Functions are Supabase-only. Put logic in FastAPI.",
        ("apps/**/*",),
    ),
    (
        re.compile(r"pg_net|pg_cron"),
        "pg_net / pg_cron are Supabase-specific. Use GitHub Actions cron / app jobs.",
        ("apps/api/**/*.py", "apps/api/**/*.sql", "infra/db/**/*.sql"),
    ),
    (
        re.compile(r"CREATE\s+POLICY[^;]+ON\s+storage\.", re.IGNORECASE | re.DOTALL),
        "Do not define RLS policies on storage.* — enforce access control in FastAPI.",
        ("infra/db/**/*.sql", "apps/api/**/*.sql"),
    ),
]

# Files we never scan.
EXCLUDE = {
    ".git",
    "node_modules",
    "dist",
    "build",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".turbo",
    "coverage",
    "playwright-report",
    "test-results",
}

# Files allowed to mention banned tokens (e.g. this script, plan, runbook).
ALLOWLIST_PATHS = {
    "scripts/check_portability.py",
    "CLAUDE.md",
    "README.md",
    "infra/runbooks/migrate-to-aws.md",
    ".cursor/rules/portability-invariants.mdc",
}


def _matches_glob(path: Path, globs: tuple[str, ...]) -> bool:
    rel = path.relative_to(ROOT)
    return any(rel.match(g) for g in globs)


def _iter_files() -> list[Path]:
    paths: list[Path] = []
    for p in ROOT.rglob("*"):
        if not p.is_file():
            continue
        if any(part in EXCLUDE for part in p.parts):
            continue
        rel = p.relative_to(ROOT).as_posix()
        if rel in ALLOWLIST_PATHS:
            continue
        paths.append(p)
    return paths


def main() -> int:
    violations: list[str] = []
    for path in _iter_files():
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for regex, message, scope in BANNED_PATTERNS:
            if not _matches_glob(path, scope):
                continue
            for m in regex.finditer(text):
                line_no = text[: m.start()].count("\n") + 1
                rel = path.relative_to(ROOT)
                violations.append(f"  {rel}:{line_no} :: {message}\n      matched: {m.group(0)!r}")

    if violations:
        print("Portability invariants violated:")
        print()
        print("\n".join(violations))
        print()
        print("See CLAUDE.md → Portability invariants. To intentionally allow, add the path to ALLOWLIST_PATHS.")
        return 1

    print("Portability invariants: OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
