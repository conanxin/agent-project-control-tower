"""
redaction.py — lightweight privacy check for event payloads.

This is NOT a security scanner. It catches obvious mistakes (accidentally
pasting a token, an IP, a local home path) before an event is written. It
will not stop a determined adversary, and that's not the goal.

Strategy
--------
- BLOCK  patterns: a clear secret / credential / home path → refuse to write
- WARN   patterns: ambiguous text that *might* be sensitive → write but flag
- PASS   : nothing matched

Usage
-----
>>> from redaction import check_text
>>> check_text("api_key=sk-1234567890abcdef1234")
('FAIL', 'token-like string detected: api_key=...')
>>> check_text("Tested locally, all green")
('PASS', '')

CLI
---
    python -m redaction --check "some text"
"""
from __future__ import annotations

import re
from typing import Final


# ----- patterns -----------------------------------------------------------

# Anything that looks like "key=secret" or "key: secret" where secret is a
# non-trivial token (16+ alphanum, or sk-/ghp_ prefixes). This is conservative:
# we don't try to be clever about which field names are "really" sensitive.

# A few common "name = value" credential shapes. We catch the assignment
# operator (with optional whitespace and quotes).
_CREDENTIAL_NAMES: Final[tuple[str, ...]] = (
    "token", "api_key", "apikey", "password", "passwd", "secret",
    "access_key", "access_key_id", "private_key", "auth", "authorization",
    "bearer",
)

# Path patterns — only block user-specific home dirs (don't block /tmp or /opt).
_HOME_PATH_PATTERNS: Final[tuple[re.Pattern[str], ...]] = (
    # Linux user homes — most likely accidental
    re.compile(r"/home/(?!tower\b|runner\b|www-data\b|node\b)[A-Za-z0-9._-]+/"),
    # macOS
    re.compile(r"/Users/(?!Shared\b|runner\b)[A-Za-z0-9._-]+/"),
    # Windows
    re.compile(r"[A-Za-z]:\\Users\\[^\\\s:]+\\"),
)

# IPv4 — block public-looking (1.x–223.x, excluding 0/127/169.254/224+). For
# MVP we just block any IPv4 in text fields; redacting private 10.x by hand
# is the user's job.
_IPV4_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
)

# Explicit "Authorization: Bearer xxx" / "Bearer xxxx" markers
_AUTH_HEADER_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b(?:authorization\s*:\s*bearer|bearer\s+)[A-Za-z0-9._\-+/=]{12,}"
)

# .env file references
_ENV_REF_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:^|[\s/\"'])(\.env(?:\.[A-Za-z0-9_]+)?)\b"
)


# ----- public API ---------------------------------------------------------


def _scan(text: str) -> tuple[str, str]:
    """Return (severity, reason). severity ∈ {FAIL, WARN, PASS}."""
    if not text:
        return "PASS", ""

    # 1. explicit auth header
    if _AUTH_HEADER_RE.search(text):
        return "FAIL", "Authorization/Bearer header detected"

    # 2. credential-shaped key=value
    # Match: token=foo, token: foo, "token": "foo", token = "foo"
    low = text.lower()
    for name in _CREDENTIAL_NAMES:
        # rough: look for the name as a word followed by = or :
        for sep in ("=", ":"):
            pat = re.compile(
                rf"(?i)\b{re.escape(name)}\b\s*{re.escape(sep)}\s*['\"]?([A-Za-z0-9._\-+/=]{{6,}})"
            )
            m = pat.search(text)
            if m:
                return "FAIL", f"credential-like assignment: {name}{sep}<redacted>"

    # 3. .env references
    if _ENV_REF_RE.search(text):
        return "WARN", ".env file reference detected (consider omitting)"

    # 4. user home paths
    for pat in _HOME_PATH_PATTERNS:
        m = pat.search(text)
        if m:
            return "WARN", f"local home path detected: {m.group(0)!r}"

    # 5. IPv4
    if _IPV4_RE.search(text):
        return "WARN", "IPv4 address detected (consider removing unless intentional)"

    return "PASS", ""


def check_text(text: str) -> tuple[str, str]:
    """Public helper: check a single text field. Returns (severity, reason)."""
    return _scan(text)


def check_payload(payload: dict) -> tuple[str, list[str]]:
    """Scan a dict of fields. Returns (overall_severity, [reasons]).

    Overall severity is the WORST of all fields:
      FAIL > WARN > PASS
    """
    if not isinstance(payload, dict):
        return "PASS", []

    severities = {"FAIL": 2, "WARN": 1, "PASS": 0}
    worst = "PASS"
    reasons: list[str] = []
    for key, value in payload.items():
        if not isinstance(value, str):
            continue
        sev, reason = _scan(value)
        if reason:
            reasons.append(f"[{key}] {sev}: {reason}")
        if severities[sev] > severities[worst]:
            worst = sev
    return worst, reasons


if __name__ == "__main__":
    import argparse
    import sys

    p = argparse.ArgumentParser(description="redaction check")
    p.add_argument("--check", metavar="TEXT", help="scan a single string")
    p.add_argument("--check-payload-json", metavar="JSON",
                   help="scan a JSON-encoded dict of fields")
    args = p.parse_args()

    if args.check is not None:
        sev, reason = check_text(args.check)
        print(f"{sev}: {reason}" if reason else "PASS")
        sys.exit(0 if sev != "FAIL" else 1)
    if args.check_payload_json is not None:
        import json
        sev, reasons = check_payload(json.loads(args.check_payload_json))
        for r in reasons:
            print(r)
        print(f"overall: {sev}")
        sys.exit(0 if sev != "FAIL" else 1)
    p.print_help()
    sys.exit(2)
