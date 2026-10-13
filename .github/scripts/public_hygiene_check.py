"""Public-repository hygiene check: things that should not be in a public repository unless
listed on purpose.

Complements leakage_check.py (which looks for known terms) with shape-based checks that need no
knowledge of the origin project:

  email       an email address not in the allowlist
  ip          an IPv4 address not in the allowlist
  hex         a 7 to 40 character hex run (commit hash, object id) outside the files where pins
              are expected; SHA-256 digests (64 hex) and action pins (`@<sha>`) are not flagged
  url         a URL whose host is not in the allowlist, or a github.com URL whose owner is not
  text        non-English text (Latin letters with diacritics, arrows and similar typography)
              outside the files declared as deliberately non-English
  identifier  a camelCase identifier in prose or evaluation files that is not in the allowlist
              (every such name is either invented for an example, and listed, or a leak)
  date        an ISO date inside plugin/ that is not in the allowlist (the shipped skill uses
              a few synthetic example dates and nothing else)

Allowlist: .github/hygiene-allowlist.txt, one entry per line, `<kind>:<value>`; `#` starts a
comment. Kinds: email (exact address, or `*@domain`), ip, hex-file (path prefix where hex runs
are expected), host, github-owner, lang-file (path allowed to hold non-English text),
identifier, date.

    python3 .github/scripts/public_hygiene_check.py            # check the repository

Scope: tracked and untracked-but-not-ignored text files, except the two list files under
.github/ and this script (its word lists would match themselves). Exit codes: 0 clean, 1 findings (printed as file:line:kind:value), 2 setup error.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

ALLOWLIST = ".github/hygiene-allowlist.txt"
SKIP_FILES = {ALLOWLIST, ".github/leakage-patterns.txt", ".github/scripts/public_hygiene_check.py"}
PROSE_SUFFIXES = {".md", ".json", ".txt"}

A, I = chr(0x103), chr(0xEE)  # a-breve and i-circumflex, built so this file stays ASCII
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IP_RE = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
HEX_RE = re.compile(r"(?<![0-9a-fA-F@/])[0-9a-f]{7,40}(?![0-9a-fA-F])")
URL_RE = re.compile(r"https?://([A-Za-z0-9.-]+)(?=[/\s)\"'>\]]|$)(/[^\s)\"'>\]]*)?")
CAMEL_RE = re.compile(r"\b[a-z]+[A-Z][A-Za-z0-9]+\b")
DATE_RE = re.compile(r"\b20\d{2}-\d{2}-\d{2}\b")
# Latin letters with diacritics, arrows and a few typographic symbols
NON_ENGLISH_RE = re.compile("[" + chr(0xC0) + "-" + chr(0x24F) + chr(0x1E00) + "-" + chr(0x1EFF) + chr(0x2190) + "-" + chr(0x22FF) + "]")
# Common Romanian words, with and without diacritics: text typed without diacritics has none for
# NON_ENGLISH_RE to catch. Each word here has no English homograph.
RO_WORDS = re.compile(r"\b(pentru|este|dac" + A + r"|f" + A + r"r" + A + r"|" + I + r"ntr|" + A + r"sta|asta|aici|acum|" + I + r"nc" + A + r"|dup" + A + r"|c" + A + r"tre"
                      r"|fara|dupa|daca|catre|sunt|doar|fiecare|nicio|niciun|fisierul|liniile)\b", re.IGNORECASE)


def load_allowlist(path: Path) -> dict[str, set[str]]:
    allow: dict[str, set[str]] = {k: set() for k in ("email", "ip", "hex-file", "host", "github-owner", "lang-file", "identifier", "date")}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, sep, value = line.partition(":")
        if not sep or kind not in allow or not value:
            print(f"hygiene check: bad allowlist entry: {raw!r}", file=sys.stderr)
            sys.exit(2)
        allow[kind].add(value.strip())
    return allow


def repo_files() -> list[Path]:
    out = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], check=True, capture_output=True).stdout
    files = []
    for raw in out.split(b"\0"):
        if not raw:
            continue
        name = raw.decode()
        if name in SKIP_FILES:
            continue
        p = Path(name)
        if p.is_file():
            files.append(p)
    return files


def is_binary(p: Path) -> bool:
    with p.open("rb") as fh:
        return b"\0" in fh.read(8192)


def email_allowed(addr: str, allow: set[str]) -> bool:
    domain = addr.rsplit("@", 1)[1].lower()
    return addr.lower() in {a.lower() for a in allow} or f"*@{domain}" in allow


def scan_file(p: Path, text: str, allow: dict[str, set[str]]) -> list[tuple[int, str, str]]:
    name = p.as_posix()
    hits: list[tuple[int, str, str]] = []
    hex_ok = any(name.startswith(prefix) for prefix in allow["hex-file"])
    lang_ok = name in allow["lang-file"]
    prose = p.suffix.lower() in PROSE_SUFFIXES
    in_plugin = name.startswith("plugin/")

    for n, line in enumerate(text.splitlines(), 1):
        for m in EMAIL_RE.finditer(line):
            if not email_allowed(m.group(0), allow["email"]):
                hits.append((n, "email", m.group(0)))
        for m in IP_RE.finditer(line):
            if m.group(0) not in allow["ip"]:
                hits.append((n, "ip", m.group(0)))
        if not hex_ok:
            for m in HEX_RE.finditer(line):
                tok = m.group(0)
                if len(tok) == 64 or not re.search(r"[a-f]", tok) or not re.search(r"\d", tok):
                    continue  # digests, or runs that are only letters or only digits
                hits.append((n, "hex", tok))
        for m in URL_RE.finditer(line):
            host = m.group(1).lower()
            url = m.group(0).rstrip(",.;:")
            if host not in allow["host"]:
                hits.append((n, "url", url))
            elif host == "github.com":
                owner = (m.group(2) or "/").split("/")[1] if m.group(2) else ""
                if owner and owner not in allow["github-owner"]:
                    hits.append((n, "url", url))
        if not lang_ok:
            m = NON_ENGLISH_RE.search(line)
            if m:
                hits.append((n, "text", m.group(0)))
            m = RO_WORDS.search(line)
            if m:
                hits.append((n, "text", m.group(0)))
        if prose:
            for m in CAMEL_RE.finditer(line):
                if m.group(0) not in allow["identifier"]:
                    hits.append((n, "identifier", m.group(0)))
        if in_plugin:
            for m in DATE_RE.finditer(line):
                if m.group(0) not in allow["date"]:
                    hits.append((n, "date", m.group(0)))
    return hits


def main() -> int:
    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("hygiene check: not inside a git repository", file=sys.stderr)
        return 2
    os.chdir(top)
    allow_path = Path(ALLOWLIST)
    if not allow_path.is_file():
        print(f"hygiene check: {ALLOWLIST} not found", file=sys.stderr)
        return 2
    allow = load_allowlist(allow_path)

    total = scanned = 0
    for p in repo_files():
        if is_binary(p):
            continue
        scanned += 1
        text = p.read_text(encoding="utf-8", errors="replace")
        for n, kind, value in scan_file(p, text, allow):
            print(f"{p.as_posix()}:{n}:{kind}:{value}")
            total += 1
    if total:
        print(f"hygiene check: {total} finding(s) in {scanned} files; list each on purpose in {ALLOWLIST} or remove it", file=sys.stderr)
        return 1
    print(f"hygiene check: {scanned} files, no findings")
    return 0


if __name__ == "__main__":
    sys.exit(main())
