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
# with a port, or a time such as `10:30`, is not a citation), then the line part. The lookbehind
# keeps URLs out: a citation never starts right after a slash, a dot or a word character.
CITATION_RE = re.compile(
    r"(?<![\w/.~-])"
    r"((?:[\w.-]+/)*[\w-][\w.-]*\.[A-Za-z][A-Za-z0-9]*)"
    r":(~?)(\d+(?:-\d+)?(?:,\s?\d+(?:-\d+)?)*)"
)

# Folders that hold dependencies or build output, not the code under audit. Searching them for
# a shortened path would turn `session.js` into an ambiguity with a library's own file.
SKIPPED_DIRS = (".git", "node_modules", ".venv", "venv", "__pycache__", ".tox", "dist", "build")


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
            item["text"] = content[spans[0][0] - 1].strip()
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
    problems = [r for r in results if r["status"] != "OK"]
    for r in results:
        if args.quiet and r["status"] == "OK":
            continue
        shown = r["citation"] + (f" -> {r['resolved']}" if r["resolved"] else "")
        print(f"{r['status']:<12}  R:{r['report_line']:<4} {shown}  | {r['text']}")
    print(f"{len(results)} citation(s), {len(problems)} not OK")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
