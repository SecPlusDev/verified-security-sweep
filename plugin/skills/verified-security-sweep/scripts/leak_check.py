"""No credential of the repository in what the sweep delivers.

The report, the tests and the findings index are written by the same session that read the
repository's secrets. This script collects credential-like values from the repository and
searches the deliverables for them, so that a value never leaves with the record. It prints
sources, lengths and masked context, never a value.

    python3 leak_check.py                              # docs/audits/ and the changed test files
    python3 leak_check.py --from-cited docs/audits/2026-01-15-money.md
    python3 leak_check.py --extra out/report.xlsx --extra out/handoff/
    python3 leak_check.py --strict                     # a WARN is a failure too

Values collected from the repository (read, never printed, never written anywhere):
    every value in a dotenv-style file (`.env`, `.env.*`, `*.env`) whose key names a secret;
    every string literal that is a value on a line naming a secret, in tracked text files;
    every password inside a DSN (`scheme://user:password@host`);
    every key-like token (24 or more key-alphabet characters mixing letters and digits).
--from-cited REPORT limits the tracked files to the ones the report cites (dotenv files are
always collected); it is faster and gives fewer coincidences.

Files scanned: everything under docs/audits/; the test files git reports as added, modified or
untracked under a folder named test, tests, spec or __tests__; and every --extra path (a file,
or a folder walked). A zip container (an .xlsx, .docx or .zip) is scanned member by member.

Result per hit, one line: the output file and line, the source of the value (file and line, or
the dotenv key), its length, and the output line with the value replaced by `<masked, N chars>`.
    FAIL   a value of 8 characters or more appears in a deliverable
    WARN   a shorter value appears as a whole word: possibly a coincidence (a password that is an
           ordinary word), possibly a leak; read the context and decide
Exit codes: 0 no FAIL (and no WARN with --strict); 1 at least one FAIL, or a WARN with --strict;
2 setup error (root not a repository, report or --extra path missing).

Why a script: a value inspected by hand goes through a hand-written masking expression, and in
the run that prompted this script that expression was wrong and the value was printed. The
script answers with booleans, lengths and shapes; nothing else is needed to decide.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_citations as cc  # noqa: E402  (sibling script: credential shapes and the mask)

# Values shorter than this are compared as whole words and reported as WARN, not FAIL.
MIN_FAIL_LENGTH = 8
# Values shorter than this are not worth collecting: too many coincidences, no secret.
MIN_VALUE_LENGTH = 3
# Files larger than this are not read (generated data, minified bundles).
MAX_FILE_BYTES = 1_000_000
TEST_DIR_NAMES = ("test", "tests", "spec", "__tests__")
# Lock files and minified bundles hold thousands of key-like hashes that are not credentials.
SKIP_NAME_RE = re.compile(r"(?i)(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|Pipfile\.lock|"
                          r"composer\.lock|Cargo\.lock|go\.sum|.*\.min\.(js|css)|.*\.map)$")
ZIP_SUFFIXES = (".xlsx", ".docx", ".pptx", ".zip", ".odt", ".ods")


def git_lines(root: Path, *args: str) -> list[str] | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.splitlines()


def read_text(path: Path) -> str | None:
    """Text of a file, or None when it is binary, missing or too large."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            return None
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:4096]:
        return None
    return data.decode("utf-8", errors="replace")


def strip_quotes(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def collect(root: Path, files: list[str]) -> dict[str, str]:
    """value -> source ('path:line' or 'path:KEY'). Values are kept in memory only."""
    found: dict[str, str] = {}

    def add(value: str, source: str) -> None:
        value = value.strip()
        if len(value) < MIN_VALUE_LENGTH or cc.name_like(value) or cc.REFERENCE_RE.match(value):
            return
        found.setdefault(value, source)

    for rel in files:
        if SKIP_NAME_RE.search(rel) or any(part in cc.SKIPPED_DIRS for part in Path(rel).parts):
            continue
        text = read_text(root / rel)
        if text is None:
            continue
        dotenv = cc.is_dotenv(rel)
        for n, line in enumerate(text.splitlines(), 1):
            if dotenv:
                m = re.match(r"^\s*(?:export\s+)?([\w.-]+)\s*=\s*(.*)$", line)
                if m and cc.SECRET_NAME_RE.search(m.group(1)):
                    add(strip_quotes(m.group(2).split(" #")[0]), f"{rel}:{m.group(1)}")
                continue
            for m in cc.DSN_RE.finditer(line):
                add(m.group(2), f"{rel}:{n}")
            for m in cc.KEYLIKE_RE.finditer(line):
                if cc.keylike(m.group(0)):
                    add(m.group(0), f"{rel}:{n}")
            if cc.SECRET_NAME_RE.search(line):
                for value in cc.secret_literals(line):
                    add(value, f"{rel}:{n}")
                m = cc.ASSIGN_RE.match(line)
                if m:
                    core = m.group(2).strip().rstrip(",;")
                    if core and not cc.LITERAL_RE.search(core):
                        add(core, f"{rel}:{n}")
    return found


def tracked_files(root: Path) -> list[str]:
    lines = git_lines(root, "ls-files", "-z")
    if lines is None:
        return []
    return [p for p in "\n".join(lines).split("\0") if p]


def dotenv_files(root: Path) -> list[str]:
    out = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in cc.SKIPPED_DIRS]
        for name in files:
            rel = (Path(current).relative_to(root) / name).as_posix()
            if cc.is_dotenv(rel):
                out.append(rel)
    return out


def cited_files(report: Path, root: Path) -> list[str]:
    files = cc.index_files(root)
    out: set[str] = set()
    for line in cc.read_lines(report):
        for m in cc.CITATION_RE.finditer(line):
            _, matches = cc.resolve(m.group(1), root, files)
            if len(matches) == 1:
                out.add(matches[0])
    return sorted(out)


def changed_test_files(root: Path) -> list[str]:
    lines = git_lines(root, "status", "--porcelain", "--untracked-files=all") or []
    out = []
    for line in lines:
        if len(line) < 4 or line[0] == "D" or line[1] == "D":
            continue
        rel = line[3:].split(" -> ")[-1].strip().strip('"')
        parts = Path(rel).parts
        if any(p in TEST_DIR_NAMES for p in parts[:-1]) and (root / rel).is_file():
            out.append(rel)
    return out


def deliverables(root: Path, audits: Path, extra: list[str]) -> list[Path]:
    out: list[Path] = []
    if audits.is_dir():
        out.extend(p for p in sorted(audits.rglob("*")) if p.is_file())
    out.extend(root / rel for rel in changed_test_files(root))
    for item in extra:
        p = Path(item)
        if p.is_dir():
            out.extend(q for q in sorted(p.rglob("*")) if q.is_file())
        else:
            out.append(p)
    seen: set[Path] = set()
    unique = []
    for p in out:
        r = p.resolve()
        if r not in seen:
            seen.add(r)
            unique.append(p)
    return unique


def texts_of(path: Path) -> list[tuple[str, str]]:
    """(label, text) pairs: the file itself, or each member of a zip container."""
    if path.suffix.lower() in ZIP_SUFFIXES and zipfile.is_zipfile(path):
        out = []
        with zipfile.ZipFile(path) as zf:
            for info in zf.infolist():
                if info.file_size > MAX_FILE_BYTES or info.is_dir():
                    continue
                data = zf.read(info)
                if b"\0" in data[:4096]:
                    continue
                out.append((f"{path}!{info.filename}", data.decode("utf-8", errors="replace")))
        return out
    text = read_text(path)
    return [(str(path), text)] if text is not None else []


def present(value: str, line: str) -> bool:
    if len(value) >= MIN_FAIL_LENGTH:
        return value in line
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(value) + r"(?![A-Za-z0-9])", line) is not None


def shown_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def scan(targets: list[Path], values: dict[str, str], root: Path) -> list[dict]:
    hits = []
    for target in targets:
        for label, text in texts_of(target):
            label = label.replace(str(target), shown_path(target, root), 1)
            for n, line in enumerate(text.splitlines(), 1):
                matched = [v for v in values if present(v, line)]
                if not matched:
                    continue
                # A DSN and the password inside it both match: report the longer one only
                matched = [v for v in matched if not any(v != w and v in w for w in matched)]
                context = line
                for v in sorted(matched, key=len, reverse=True):
                    context = context.replace(v, cc.MASK.format(n=len(v)))
                for v in matched:
                    hits.append({"level": "FAIL" if len(v) >= MIN_FAIL_LENGTH else "WARN",
                                 "where": f"{label}:{n}", "source": values[v], "length": len(v),
                                 "context": context.strip()})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--root", help="repository root (default: git top level of the current directory)")
    ap.add_argument("--audits", default="docs/audits", help="audits folder, relative to the root (default: docs/audits)")
    ap.add_argument("--from-cited", metavar="REPORT", help="collect values only from the files this report cites")
    ap.add_argument("--extra", action="append", default=[], metavar="PATH", help="another file or folder to scan; repeatable")
    ap.add_argument("--strict", action="store_true", help="a WARN is a failure too")
    args = ap.parse_args()

    root = cc.repo_root(args.root)
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 2
    for item in args.extra:
        if not Path(item).exists():
            print(f"--extra path not found: {item}", file=sys.stderr)
            return 2
    if args.from_cited:
        report = Path(args.from_cited)
        if not report.is_file():
            print(f"report not found: {report}", file=sys.stderr)
            return 2
        files = cited_files(report, root)
    else:
        files = tracked_files(root)
    files = sorted(set(files) | set(dotenv_files(root)))
    values = collect(root, files)
    targets = deliverables(root, root / args.audits, args.extra)
    hits = scan(targets, values, root)

    for h in hits:
        print(f"{h['level']:<5}  {h['where']}  value from {h['source']} (len {h['length']})  | {h['context']}")
    fails = sum(1 for h in hits if h["level"] == "FAIL")
    warns = len(hits) - fails
    print(f"{len(targets)} file(s) scanned, {len(values)} value(s) collected from {len(files)} file(s), "
          f"{fails} FAIL, {warns} WARN")
    if fails or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
