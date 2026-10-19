"""Every file:line a report cites, opened in the repository.

A citation that names a line the file does not have is a citation nobody opened. This script
reads a report, finds every `path:line` and `path:start-end`, opens each one in the repository
and prints the cited text next to it, so the author sees what each citation points at before
the report ships.

    python3 check_citations.py docs/audits/2026-01-15-money.md
    python3 check_citations.py docs/audits/2026-01-15-money.md --root path/to/repo
    python3 check_citations.py docs/audits/2026-01-15-money.md --quiet   # problems only

A citation is a path with a file extension followed by `:line`, `:start-end` or a comma list of
those (`src/billing/invoice.ts:42`, `app/routes/session.js:25-34,116`). Paths are relative to
the repository root, which is the git top level of the current directory unless --root is
given. A shorter path (`invoice.ts:42`, `billing/invoice.ts:42`) is resolved when exactly one
file in the repository ends with it, and reported as AMBIGUOUS when several do.

Status per citation:
    OK            the file exists and every cited line is inside it
    MISSING       no file in the repository matches the path
    AMBIGUOUS     several files match a shortened path
    OUT OF RANGE  the file exists but a cited line is past its end, or a range runs backwards
    APPROXIMATE   the line is marked approximate (`:~42`); an exact line is required

Each OK line shows the text of the first cited line. A comment, a blank line or a closing brace
at the location of a finding is a citation to correct even though it exists: the script prints
the text so that a reader catches it, it does not judge it.

A cited line that looks like it holds a credential is printed masked, as `OK (masked)`: every
string literal and every value after `=` or `:` is replaced by `<masked, N chars>`. A line is
treated that way when it is in a dotenv-style file (`.env`, `.env.*`, `*.env`), when it names a
secret (password, secret, token, api key, private key, credential, a DSN with `user:password@`)
and carries a literal value, or when it holds a key-like token. There is no option to print the
value: a hard-coded credential finding cites the line that holds the credential, and the script's
output goes into the session transcript. The author who needs the value opens the file.

Exit codes: 0 every citation resolves to existing lines (also when the report cites none),
1 at least one citation is not OK, 2 setup error (report missing, root not a directory).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# A path segment, then a dot and an extension that starts with a letter (so a dotted address
# with a port, or a time such as `10:30`, is not a citation), then the line part. The stem may
# be empty, so that a dotenv file (`app/.env:3`) is a citation too. The lookbehind keeps URLs
# out: a citation never starts right after a slash, a dot or a word character.
CITATION_RE = re.compile(
    r"(?<![\w/.~-])"
    r"((?:[\w.-]+/)*(?:[\w-][\w.-]*)?\.[A-Za-z][A-Za-z0-9]*)"
    r":(~?)(\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)"
)

# Folders that hold dependencies or build output, not the code under audit. Searching them for
# a shortened path would turn `session.js` into an ambiguity with a library's own file.
SKIPPED_DIRS = (".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build")

# Credential handling, shared with findings.py and leak_check.py. The shapes below decide when a
# line is printed masked; they err on the side of masking, because an over-masked line costs the
# reader one file open and an under-masked one puts a credential in the transcript.
#
# A key-like token: 24 or more characters of the alphabets keys are written in, mixing letters
# and digits (the letter/digit test is in keylike()). 24 is below the shortest common API key.
KEYLIKE_RE = re.compile(r"[A-Za-z0-9+/_=-]{24,}")
# Words that name a secret when they appear in a key, a variable or a field name.
SECRET_WORDS = (
    r"(?:passw(?:or)?d|pwd|secret|token|api[_-]?key|apikey|private[_-]?key|credential|"
    r"client[_-]?secret|auth[_-]?key|access[_-]?key|dsn|connection[_-]?string)"
)
SECRET_NAME_RE = re.compile("(?i)" + SECRET_WORDS)
# A DSN or URL that carries user:password@ before the host.
DSN_RE = re.compile(r"://([^/\s:@]+):([^/\s@]+)@")
# Quoted string literals; the content is what gets masked.
LITERAL_RE = re.compile(r"\"((?:[^\"\\]|\\.)*)\"|'((?:[^'\\]|\\.)*)'")
# `name = value` or `name: value` where the name holds a secret word; the value runs to the end.
ASSIGN_RE = re.compile(r"(?i)^(\s*[\w.\[\]\"'-]*" + SECRET_WORDS + r"[\w.\[\]\"'-]*\s*[=:]\s*)(.*)$")
# Values that reference configuration rather than hold it, left unmasked.
REFERENCE_RE = re.compile(
    r"^(?:None|null|nil|true|false|\"\"|'')?$|^\$|^\$?\{|^os\.|^env\b|^process\.env|^settings\."
    r"|^config\b|^get[A-Za-z_]*\(|^secrets\.|^request\.|^req\.|^self\.|^this\."
)
MASK = "<masked, {n} chars>"


def is_dotenv(path: str) -> bool:
    name = Path(path).name
    return name == ".env" or name.startswith(".env.") or name.endswith(".env")


def keylike(text: str) -> bool:
    """A token of key alphabet, 24 characters or more, that mixes letters and digits."""
    return any(re.search(r"[A-Za-z]", m) and re.search(r"\d", m) for m in KEYLIKE_RE.findall(text))


def name_like(value: str) -> bool:
    """A literal that is a name, not a value: a secret word used as a field or variable name
    (`"password"`), or an environment-variable name (`"SECRET_KEY"`, `"DATABASE_URL"`)."""
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
        return False
    return bool(SECRET_NAME_RE.search(value)) or value == value.upper()


def literal_values(text: str) -> list[str]:
    """Quoted literals on the line that are values, not names: a literal that is only a secret
    word (`"password"`, `'SECRET_KEY'`) is a field or variable name and does not count."""
    out = []
    for m in LITERAL_RE.finditer(text):
        value = m.group(1) if m.group(1) is not None else m.group(2)
        if not value:
            continue
        if name_like(value):
            continue
        out.append(value)
    return out


def sensitive(path: str, text: str) -> bool:
    """True when the line may hold a credential: a dotenv file, a secret name with a literal
    value, a DSN with user:password@, or a key-like token."""
    if is_dotenv(path) and "=" in text and not text.lstrip().startswith("#"):
        return True
    if DSN_RE.search(text) or keylike(text):
        return True
    if not SECRET_NAME_RE.search(text):
        return False
    if literal_values(text):
        return True
    m = ASSIGN_RE.match(text)
    if m:
        value = m.group(2).strip().rstrip(",;")
        return bool(value) and not REFERENCE_RE.match(value)
    return False


def mask(text: str, path: str = "") -> str:
    """The line with every string literal that is a value, every value after `name =` or
    `name:` (any name in a dotenv file, a secret name elsewhere), every DSN password and every
    key-like token replaced by `<masked, N chars>`; names and structure stay."""
    def lit(m: re.Match) -> str:
        value = m.group(1) if m.group(1) is not None else m.group(2)
        quote = m.group(0)[0]
        if not value or name_like(value):
            return m.group(0)
        return f"{quote}{MASK.format(n=len(value))}{quote}"

    out = LITERAL_RE.sub(lit, text)
    m = ASSIGN_RE.match(out)
    if not m and is_dotenv(path):
        m = re.match(r"^(\s*[\w.-]+\s*=\s*)(.*)$", out)
    if m:
        value = m.group(2)
        core = value.strip().rstrip(",;")
        if core and "<masked" not in core and not REFERENCE_RE.match(core):
            out = m.group(1) + value.replace(core, MASK.format(n=len(core)), 1)
    out = DSN_RE.sub(lambda m: f"://{m.group(1)}:{MASK.format(n=len(m.group(2)))}@", out)
    out = KEYLIKE_RE.sub(lambda m: MASK.format(n=len(m.group(0))) if keylike(m.group(0)) else m.group(0), out)
    return out


def shown_text(path: str, text: str) -> tuple[str, bool]:
    """(text to print, masked?) for a line read from the repository."""
    if sensitive(path, text):
        return mask(text, path), True
    return text, False


def repo_root(given: str | None) -> Path:
    if given:
        return Path(given)
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, capture_output=True, text=True
        ).stdout.strip()
        return Path(out)
    except (OSError, subprocess.CalledProcessError):
        return Path.cwd()


def index_files(root: Path) -> list[str]:
    """Repository-relative paths of every file outside the skipped folders, with / separators."""
    found = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIPPED_DIRS]
        rel_dir = Path(current).relative_to(root)
        for name in files:
            found.append((rel_dir / name).as_posix())
    return found


def resolve(path: str, root: Path, files: list[str]) -> tuple[str, list[str]]:
    """('direct', [path]) when the path exists as given, otherwise the files that end with it."""
    if (root / path).is_file():
        return "direct", [path]
    bare = path[2:] if path.startswith("./") else path
    return "suffix", [f for f in files if f == bare or f.endswith("/" + bare)]


def parse_lines(spec: str) -> list[tuple[int, int]]:
    spans = []
    for part in spec.replace(" ", "").split(","):
        if "-" in part:
            a, b = part.split("-", 1)
            spans.append((int(a), int(b)))
        else:
            spans.append((int(part), int(part)))
    return spans


def read_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8", errors="replace").splitlines()


def check(report: Path, root: Path) -> list[dict]:
    files = index_files(root)
    cache: dict[str, list[str]] = {}
    results = []
    for n, line in enumerate(read_lines(report), 1):
        for m in CITATION_RE.finditer(line):
            path, approx, spec = m.group(1), m.group(2), m.group(3)
            item = {"report_line": n, "citation": m.group(0), "resolved": "", "status": "OK", "text": ""}
            results.append(item)
            if approx:
                item["status"] = "APPROXIMATE"
                continue
            how, matches = resolve(path, root, files)
            if not matches:
                item["status"] = "MISSING"
                continue
            if len(matches) > 1:
                item["status"] = "AMBIGUOUS"
                item["text"] = ", ".join(sorted(matches)[:5]) + (" ..." if len(matches) > 5 else "")
                continue
            target = matches[0]
            if how == "suffix":
                item["resolved"] = target
            if target not in cache:
                cache[target] = read_lines(root / target)
            content = cache[target]
            spans = parse_lines(spec)
            bad = [(a, b) for a, b in spans if a < 1 or b < a or b > len(content)]
            if bad:
                item["status"] = "OUT OF RANGE"
                item["text"] = f"file has {len(content)} lines"
                continue
            text, masked = shown_text(target, content[spans[0][0] - 1].strip())
            item["text"] = text
            if masked:
                item["status"] = "OK (masked)"
    return results


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("report", help="the report to check, for example docs/audits/2026-01-15-money.md")
    ap.add_argument("--root", help="repository root (default: git top level of the current directory)")
    ap.add_argument("--quiet", action="store_true", help="print only the citations that are not OK")
    args = ap.parse_args()

    report = Path(args.report)
    if not report.is_file():
        print(f"report not found: {report}", file=sys.stderr)
        return 2
    root = repo_root(args.root)
    if not root.is_dir():
        print(f"root is not a directory: {root}", file=sys.stderr)
        return 2

    results = check(report, root)
    if not results:
        print(f"{report}: no file:line citations found")
        return 0
    problems = [r for r in results if not r["status"].startswith("OK")]
    for r in results:
        if args.quiet and r["status"].startswith("OK"):
            continue
        shown = r["citation"] + (f" -> {r['resolved']}" if r["resolved"] else "")
        print(f"{r['status']:<12}  R:{r['report_line']:<4} {shown}  | {r['text']}")
    print(f"{len(results)} citation(s), {len(problems)} not OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
