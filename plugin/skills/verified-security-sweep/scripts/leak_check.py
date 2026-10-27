"""No value of the repository in what the sweep delivers.

The report, the tests and the findings index are written by the same session that read the
repository. This script scans the deliverables for the value shapes of shapes.json and reports
each hit masked. It reads the deliverables only, never the repository's dotenv files or sources,
and nothing it prints is a value.

    python3 leak_check.py                              # docs/audits/ and the changed test files
    python3 leak_check.py --extra out/report.xlsx --extra out/handoff/
    python3 leak_check.py --strict                     # a WARN is a failure too

Shapes found (the same ones check_citations.py masks when it prints a cited line):
    a long token: TOKEN_MIN_LENGTH or more token-alphabet characters, letters and digits mixed,
        with both cases, base64 padding or `+`, and not an identifier of word-like segments (a
        dated id, a path, a test name); a 40-character lowercase hexadecimal run is a commit id
        and is skipped; a 64-character one that git does not know as an object of the
        repository is reported as a WARN (a digest or a hexadecimal token: read the context);
    the userinfo value of a URL: `scheme://user:value@host`;
    a quoted literal assigned to or passed next to a name listed in shapes.json: `name="..."`,
        `"name": '...'`, `NAME = "..."`;
    an unquoted value after a listed name and `=` anywhere (`NAME=...` in inline code), or
        after a listed name and `:` at the start of the line, when it is one token; prose after
        a colon has spaces and is not one.
    Placeholders and names are not values: `changeme`, `<your-key>`, `${NAME}`, `********`,
    an ALL_CAPS name, a word in the stoplist of shapes.json.

Files scanned: everything under docs/audits/; the test files git reports as added, modified or
untracked under a folder named test, tests, spec or __tests__; and every --extra path (a file,
or a folder walked). A zip container (an .xlsx, .docx or .zip) is scanned member by member.
In a test file only the token and URL shapes count: the tests the sweep adds log in with
invented values next to their names, by the skill's own rule, and a real value copied into a
test is token-shaped or a URL far more often than a word.

Result per hit, one line: the output file and line, the shape, the length, and the output line
with the value replaced by `<masked, N chars>`.
    FAIL   a value of 8 characters or more
    WARN   a shorter value, or a lone hexadecimal run: possibly a coincidence (an ordinary word
           next to a listed name, a digest), possibly a leak; read the context
Exit codes: 0 no FAIL (and no WARN with --strict); 1 at least one FAIL, or a WARN with --strict;
2 setup error (root not a directory, --extra path missing).

What this does not see: a value written in prose without its name ("the admin value is apple"
is caught when "value" is a listed word, "it is apple" is not), and a short value copied into a
test next to its name. The value-side check that catches both, by reading the repository's
own values, is kept outside the plugin (tools/leak_values.py in the repository); the evaluation
runs recorded with the skill compare the two on the same records.

Why a script: a value inspected by hand goes through a hand-written masking expression, and in
the run that prompted this script that expression was wrong and the value was printed. The
script answers with shapes and lengths; nothing else is needed to decide.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_citations as cc  # noqa: E402  (sibling script: the value shapes and the mask)

# Values shorter than this are reported as WARN, not FAIL.
MIN_FAIL_LENGTH = 8
# Values shorter than this, or without any letter or digit, are not values: `---`, `***`.
MIN_VALUE_LENGTH = 5
# Files larger than this are not read.
MAX_FILE_BYTES = 1_000_000
TEST_DIR_NAMES = ("test", "tests", "spec", "__tests__")
ZIP_SUFFIXES = (".xlsx", ".docx", ".pptx", ".zip", ".odt", ".ods")
# A placeholder, not a value: one character repeated, an angle-bracket slot, an ellipsis, a
# masked span this script or check_citations.py already printed.
PLACEHOLDER_RE = re.compile(r"^(.)\1*$|^<[^<>]*>$|^\.{3,}$|^x{4,}$|^X{4,}$|<masked, \d+ chars>")
# A 40-character lowercase hexadecimal run is a commit id: the record cites commits everywhere
# (`"commit": "..."` in the logs). A 64-character one is a digest or a hexadecimal key.
# `NAME=value` anywhere on the line (inline code in a report), the name holding a listed word,
# the value one token. Only `=`: `name: rotated` in prose is a sentence.
INLINE_ASSIGN_RE = re.compile(r"(?i)(?<![\w.-])([\w.-]*" + cc.NAME_WORDS + r"[\w.-]*)=([^\s\"'`,;)]+)")
COMMIT_ID_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


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


def git_lines(root: Path, *args: str) -> list[str] | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True)
    except (OSError, subprocess.CalledProcessError):
        return None
    return out.stdout.splitlines()


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


def shown_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def is_value(text: str) -> bool:
    """A string that counts as a value: long enough, with a letter or digit, not a name, a
    reference or a placeholder."""
    text = text.strip()
    if len(text) < MIN_VALUE_LENGTH or not re.search(r"[A-Za-z0-9]", text):
        return False
    if cc.name_like(text) or cc.REFERENCE_RE.match(text) or PLACEHOLDER_RE.search(text):
        return False
    return True


class GitObjects:
    """Whether a 40- or 64-character hexadecimal token names an object of the repository."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.cache: dict[str, bool] = {}

    def knows(self, token: str) -> bool:
        if token not in self.cache:
            try:
                subprocess.run(["git", "-C", str(self.root), "cat-file", "-e", token],
                               check=True, capture_output=True)
                self.cache[token] = True
            except (OSError, subprocess.CalledProcessError):
                self.cache[token] = False
        return self.cache[token]


def shapes_in(line: str, objects: GitObjects, in_tests: bool = False) -> list[tuple[str, str, str]]:
    """(shape, value, level) for every value shape on the line. In a test file only the token
    and URL shapes count: a test the sweep adds logs in with an invented value next to its name,
    by the skill's own rule."""
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(shape: str, value: str, level: str | None = None) -> None:
        value = value.strip()
        if value in seen or not is_value(value):
            return
        seen.add(value)
        out.append((shape, value, level or ("FAIL" if len(value) >= MIN_FAIL_LENGTH else "WARN")))

    for m in cc.URL_AUTH_RE.finditer(line):
        add("URL userinfo value", m.group(2))
    for m in cc.NAMED_LITERAL_RE.finditer(line) if not in_tests else ():
        name = re.match(r"[\w-]+", m.group(0))
        add(f"literal next to `{name.group(0) if name else 'name'}`", m.group(2))
    m = cc.ASSIGN_RE.match(line) if not in_tests else None
    if m:
        value = m.group(2).strip().rstrip(",;").strip()
        if value and not cc.LITERAL_RE.search(value) and not re.search(r"\s", value):
            name = cc.NAME_RE.search(m.group(1))
            add(f"value after `{name.group(0) if name else 'name'}`", value.rstrip("`)"))
    for m in INLINE_ASSIGN_RE.finditer(line) if not in_tests else ():
        add(f"value after `{m.group(1)}=`", m.group(2))
    for m in cc.TOKEN_RE.finditer(line):
        token = m.group(0)
        if not cc.tokenlike(token):
            continue
        if COMMIT_ID_RE.match(token):
            continue  # a commit id, by the record's convention
        if SHA256_RE.match(token):
            if objects.knows(token):
                continue
            add("hexadecimal run of 64, not a git object", token, "WARN")
        else:
            add("long token", token)
    # A URL userinfo value inside a long token, a literal inside a URL: report the longer one only
    values = [v for _, v, _ in out]
    return [(s, v, lv) for s, v, lv in out if not any(v != w and v in w for w in values)]


def scan(targets: list[Path], root: Path) -> list[dict]:
    objects = GitObjects(root)
    hits = []
    for target in targets:
        in_tests = any(p in TEST_DIR_NAMES for p in Path(shown_path(target, root)).parts[:-1])
        for label, text in texts_of(target):
            label = label.replace(str(target), shown_path(target, root), 1)
            for n, line in enumerate(text.splitlines(), 1):
                found = shapes_in(line, objects, in_tests)
                if not found:
                    continue
                context = line
                for _, v, _ in sorted(found, key=lambda t: len(t[1]), reverse=True):
                    context = context.replace(v, cc.MASK.format(n=len(v)))
                for shape, v, level in found:
                    hits.append({"level": level, "where": f"{label}:{n}", "shape": shape,
                                 "length": len(v), "context": context.strip()})
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("--root", help="repository root (default: git top level of the current directory)")
    ap.add_argument("--audits", default="docs/audits", help="audits folder, relative to the root (default: docs/audits)")
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
    targets = deliverables(root, root / args.audits, args.extra)
    hits = scan(targets, root)

    for h in hits:
        print(f"{h['level']:<5}  {h['where']}  {h['shape']} (len {h['length']})  | {h['context']}")
    fails = sum(1 for h in hits if h["level"] == "FAIL")
    warns = len(hits) - fails
    print(f"{len(targets)} file(s) scanned, {fails} FAIL, {warns} WARN")
    if fails or (args.strict and warns):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
