"""Leakage check: fail when any file in the repository contains a listed term.

Two lists, same format, one entry per line:

    sha256:<hex>    a term that must not appear, stored as the SHA-256 of its normalized form
    regex:<ERE>     a generic shape (local path, network address), matched case-insensitively

`.github/leakage-patterns.txt` is public and holds generic shapes only. The terms themselves
live outside the repository: in the file named by the environment variable LEAKAGE_TERMS_FILE
(the owner keeps `.github/leakage-terms.local`, which git ignores; CI writes a repository secret
to a temporary file). A hashed list of short terms is not safe to publish: unsalted SHA-256 of
a company or person name is recovered by guessing, so the hashes stay private too. Without a
terms file the check runs the shapes alone and says so; that is what a pull request from a fork
gets, and the owner runs the full check locally before merging.

Normalization, for terms and for file content alike: lower-case, then tokens are maximal runs
of [a-z0-9]. Each token is hashed, and so is each pair of adjacent tokens joined without a
separator, each pair with one token skipped, and each run of three, so "Foo 7", "foo-7",
"Foo nr. 7" and "FOO7" all normalize to the same token. A term has at most three tokens.

    python3 .github/scripts/leakage_check.py                 # check the repository
    python3 .github/scripts/leakage_check.py --hash "term"   # print the entry for a new term

Scope: every tracked or untracked-but-not-ignored file, except the public list itself and files
that look binary (NUL byte in the first 8 KiB). Exit codes: 0 no matches, 1 leakage found
(printed as file:line:match), 2 setup error.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

PATTERN_FILE = ".github/leakage-patterns.txt"
TERMS_ENV = "LEAKAGE_TERMS_FILE"
TOKEN_RE = re.compile(r"[a-z0-9]+")


def digest(term: str) -> str:
    return hashlib.sha256("".join(TOKEN_RE.findall(term.lower())).encode()).hexdigest()


def load_patterns(path: Path, hashes: set[str] | None = None, regexes: list[re.Pattern] | None = None) -> tuple[set[str], list[re.Pattern]]:
    hashes = set() if hashes is None else hashes
    regexes = [] if regexes is None else regexes
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        kind, _, value = line.partition(":")
        if kind == "sha256" and re.fullmatch(r"[0-9a-f]{64}", value):
            hashes.add(value)
        elif kind == "regex" and value:
            regexes.append(re.compile(value, re.IGNORECASE))
        else:
            print(f"leakage check: bad entry in {path}: {raw!r}", file=sys.stderr)
            sys.exit(2)
    if not hashes and not regexes:
        print(f"leakage check: no patterns in {path}", file=sys.stderr)
        sys.exit(2)
    return hashes, regexes


def repo_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        check=True, capture_output=True,
    ).stdout
    files = []
    for name in out.split(b"\0"):
        if not name or name.decode() == PATTERN_FILE:
            continue
        p = Path(name.decode())
        if p.is_file():
            files.append(p)
    return files


def is_binary(p: Path) -> bool:
    with p.open("rb") as fh:
        return b"\0" in fh.read(8192)


def scan_line(line: str, hashes: set[str], regexes: list[re.Pattern]) -> list[str]:
    hits = []
    tokens = TOKEN_RE.findall(line.lower())
    candidates = tokens + [a + b for a, b in zip(tokens, tokens[1:])]
    candidates += [a + c for a, c in zip(tokens, tokens[2:])]
    candidates += [a + b + c for a, b, c in zip(tokens, tokens[1:], tokens[2:])]
    for tok in candidates:
        if hashlib.sha256(tok.encode()).hexdigest() in hashes:
            hits.append(tok)
    for rx in regexes:
        for m in rx.finditer(line):
            hits.append(m.group(0))
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--hash", metavar="TERM", help="print the list entry for TERM and exit")
    a = ap.parse_args()
    if a.hash is not None:
        if len(TOKEN_RE.findall(a.hash.lower())) > 3:
            print("leakage check: a term may have at most three tokens; hash a shorter form", file=sys.stderr)
            return 2
        print(f"sha256:{digest(a.hash)}")
        return 0

    try:
        top = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True).stdout.strip()
    except subprocess.CalledProcessError:
        print("leakage check: not inside a git repository", file=sys.stderr)
        return 2
    os.chdir(top)
    pattern_path = Path(PATTERN_FILE)
    if not pattern_path.is_file():
        print(f"leakage check: {PATTERN_FILE} not found", file=sys.stderr)
        return 2
    hashes, regexes = load_patterns(pattern_path)
    terms_file = os.environ.get(TERMS_ENV, "").strip()
    if terms_file:
        terms_path = Path(terms_file)
        if not terms_path.is_file():
            print(f"leakage check: {TERMS_ENV} names a file that does not exist: {terms_file}", file=sys.stderr)
            return 2
        hashes, regexes = load_patterns(terms_path, hashes, regexes)
        terms_note = ""
    else:
        terms_note = f"; no private terms file ({TERMS_ENV} unset): shapes only"

    files = repo_files()
    if not files:
        print("leakage check: no files to scan", file=sys.stderr)
        return 2

    total = 0
    scanned = 0
    for p in files:
        if is_binary(p):
            continue
        scanned += 1
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            print(f"leakage check: cannot read {p}: {e}", file=sys.stderr)
            return 2
        for n, line in enumerate(text.splitlines(), 1):
            for hit in scan_line(line, hashes, regexes):
                print(f"{p}:{n}:{hit}")
                total += 1

    if total:
        print(f"leakage check: {total} match(es) in {scanned} files; the skill repository must contain none", file=sys.stderr)
        return 1
    print(f"leakage check: {len(hashes)} hashed terms, {len(regexes)} shapes, {scanned} files, no matches{terms_note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
