"""Guard: no internal or customer data in this public repository.

The checks are **structural, not name-based** — deliberately. A blocklist of
customer names would have to live in this repo and would therefore publish the
very customer list it is meant to protect. Keying on the *shape* of real values
instead covers a new customer automatically, without ever naming one here.

Each check fails closed: anything that is not a known placeholder is a failure.
That is the point. A new literal added on purpose needs one line here, and
adding that line forces a human to look at the value first.

**Scope: git-tracked files.** Commit messages and pull-request text are public
too and are *not* covered — those remain a human check before pushing.
"""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

# This file states the patterns and must not match itself.
SELF = Path(__file__).name

SKIP_DIRS = {".git", ".venv", "venv", "__pycache__", ".power-automate-backups", "tmp"}
TEXT_SUFFIXES = {
    ".py", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg", ".ini", ".sh", ""
}

# --- Placeholders that are allowed to appear ---------------------------------
# Synthetic GUIDs used in docs, tests and config examples. Real environment or
# tenant ids never look like these.
PLACEHOLDER_GUIDS = {
    "00000000-0000-0000-0000-000000000000",
    "11111111-1111-1111-1111-111111111111",
    "22222222-2222-2222-2222-222222222222",
    "12345678-90ab-cdef-1234-567890abcd99",
    "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeff",
}

# Hostnames allowed in front of `.crm*.dynamics.com`. Real Dataverse orgs are
# either `org` + hex (e.g. org1a2b3c4d) or carry the customer's own name, so
# neither can pass this set.
PLACEHOLDER_DATAVERSE_HOSTS = {
    "org", "<org>", "cfg", "dev", "prod", "ok", "denied", "flag", "acme", "contoso",
}

# --- Shapes of real values ---------------------------------------------------
GUID = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")
DATAVERSE_HOST = re.compile(r"([A-Za-z0-9<>_.-]+)\.(?:api\.)?crm\d*\.dynamics\.com")
# `@odata.bind` and friends are OData annotations, not addresses.
EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@(?!odata\.)[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
# 1Password item ids: 26 lowercase alphanumerics containing at least one digit.
# The digit requirement is what separates them from OData field names such as
# `environmentvariablevalueid`.
ONEPASSWORD_ITEM = re.compile(r"\b(?=[a-z0-9]{26}\b)(?=[a-z0-9]*\d)[a-z0-9]{26}\b")
SECRET_REFERENCE = re.compile(r"op://")
# Internal repository and config names. Safe to name here: these are ours, not
# a customer's.
INTERNAL_NAMES = re.compile(r"credentials\.config|power_automate_ctl|n8n-cicd|walspro\.weclapp")


def tracked_files() -> list[Path]:
    """Git-tracked text files, with a filesystem fallback for sdist checkouts."""
    try:
        out = subprocess.run(
            ["git", "-C", str(REPO), "ls-files", "-z"],
            capture_output=True, text=True, timeout=30, check=True,
        ).stdout
        names = [n for n in out.split("\0") if n]
        paths = [REPO / n for n in names]
    except (OSError, subprocess.SubprocessError):
        paths = [p for p in REPO.rglob("*") if not SKIP_DIRS & set(p.parts)]
    return [
        p for p in paths
        if p.is_file() and p.name != SELF and p.suffix.lower() in TEXT_SUFFIXES
    ]


class NoInternalDataTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files = tracked_files()
        cls.contents = {}
        for path in cls.files:
            try:
                cls.contents[path] = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue

    def _findings(self, pattern, keep=lambda value: True):
        found = []
        for path, text in self.contents.items():
            for match in pattern.findall(text):
                value = match if isinstance(match, str) else match[0]
                if keep(value):
                    found.append(f"{path.relative_to(REPO)}: {value}")
        return sorted(set(found))

    def test_repository_is_not_empty(self):
        """Guards the guard: a broken file walk must not look like a pass."""
        self.assertGreater(len(self.contents), 10)

    def test_no_real_guids(self):
        found = self._findings(GUID, lambda v: v.lower() not in PLACEHOLDER_GUIDS)
        self.assertEqual(found, [], "Real-looking GUID(s); use a placeholder or allowlist it:")

    def test_no_real_dataverse_hosts(self):
        found = self._findings(
            DATAVERSE_HOST, lambda v: v.lower() not in PLACEHOLDER_DATAVERSE_HOSTS
        )
        self.assertEqual(found, [], "Non-placeholder Dataverse host(s):")

    def test_no_email_addresses(self):
        found = self._findings(EMAIL)
        self.assertEqual(found, [], "E-mail address(es) — service accounts must not appear:")

    def test_no_onepassword_item_ids(self):
        found = self._findings(ONEPASSWORD_ITEM)
        self.assertEqual(found, [], "1Password item id shape(s):")

    def test_no_secret_references(self):
        found = self._findings(SECRET_REFERENCE)
        self.assertEqual(found, [], "Secret reference(s):")

    def test_no_internal_repository_or_config_names(self):
        found = self._findings(INTERNAL_NAMES)
        self.assertEqual(found, [], "Internal repository/config name(s):")
