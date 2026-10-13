"""Rank recently changed source files as sweep candidates.

Fresh code is the zone with the highest audit yield: the author's assumptions are still in it
and no guard exists yet. This script lists files changed in the last N days, ranked by number of
commits touching them, and flags files whose basename is not mentioned by any test file.

    python3 fresh_code.py                     # last 3 days, src-like paths, top 40
    python3 fresh_code.py --days 14 --top 60
    python3 fresh_code.py --src api/src web/src --tests api/tests web/src
    python3 fresh_code.py --json             # machine-readable

The "no test mentions it" flag is a heuristic (the file's stem searched as a whole word across
test files), good enough to decide where to read first, not a coverage measurement.

Exit codes: 0 ran, 2 not a git repository or no commits to read.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# Files worth reading in a sweep: application code, SQL and shell. Markup, styles, lockfiles and
# generated assets churn constantly and are not where defects live, so they are left out.
SOURCE_EXT = {".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rb", ".java", ".kt", ".cs", ".php", ".sql", ".sh"}
# A path containing any of these is a test, in the conventions of the ecosystems above
# (pytest, Jest, RSpec, Go tests, and a "guards" folder for invariant tests).
TEST_MARKERS = ("test", "spec", "__tests__", "guards")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_files(days: int) -> tuple[Counter, dict[str, dict[str, None]]]:
    log = git("log", f"--since={days}.days", "--name-only", "--pretty=format:@@%h %an")
    commits: Counter = Counter()
    authors: dict[str, dict[str, None]] = defaultdict(dict)
    current = None
    for line in log.splitlines():
        if line.startswith("@@"):
            current = line[2:].split(" ", 1)
            continue
        f = line.strip()
        if not f or current is None:
            continue
        p = Path(f)
        if p.suffix not in SOURCE_EXT:
            continue
        commits[f] += 1
        authors[f][current[1] if len(current) > 1 else "?"] = None
    return commits, authors


def is_test(path: str) -> bool:
    low = path.lower()
    return any(m in low for m in TEST_MARKERS)


def under(path: str, roots: list[str]) -> bool:
    return not roots or any(path.startswith(r.rstrip("/") + "/") or path == r for r in roots)


def test_corpus(test_roots: list[str]) -> str:
    chunks = []
    for root in test_roots:
        rp = Path(root)
        if not rp.exists():
            continue
        for p in rp.rglob("*"):
            if p.is_file() and p.suffix in SOURCE_EXT and is_test(str(p)):
                try:
                    chunks.append(p.read_text(encoding="utf-8", errors="ignore"))
                except OSError:
                    pass
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=3, help="window in days; 3 covers a long weekend of commits and stays readable in one sweep (default 3)")
    ap.add_argument("--top", type=int, default=40, help="files listed; 40 is about what one reviewer reads in a session (default 40)")
    ap.add_argument("--src", nargs="*", default=[], help="restrict to these roots (default: all non-test source)")
    # Roots scanned for test files; only files whose path carries a test marker count, so a
    # source root in the list costs a walk and nothing else. Missing roots are skipped.
    ap.add_argument("--tests", nargs="*", default=["tests", "test", "spec", "src", "app", "lib"], help="roots to scan for test files (default: tests, test, spec, src, app, lib)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    try:
        git("rev-parse", "--is-inside-work-tree")
    except subprocess.CalledProcessError:
        print("not a git repository", file=sys.stderr)
        return 2

    try:
        commits, authors = changed_files(a.days)
    except subprocess.CalledProcessError as e:
        print(f"git log failed (no commits yet?): {e.stderr.strip() or e}", file=sys.stderr)
        return 2
    corpus = test_corpus(a.tests)
    rows = []
    for f, n in commits.most_common():
        if is_test(f) or not under(f, a.src):
            continue
        stem = Path(f).stem
        # whole-word match, so `app.py` is not "mentioned" by a test that says "application"
        mentioned = re.search(rf"(?<![A-Za-z0-9_]){re.escape(stem)}(?![A-Za-z0-9_])", corpus) is not None
        rows.append({"file": f, "commits": n, "authors": len(authors[f]), "test_mentions": mentioned})
    rows = rows[: a.top]

    by_dir: Counter = Counter()
    for r in rows:
        by_dir[str(Path(r["file"]).parent)] += r["commits"]

    if a.json:
        print(json.dumps({"days": a.days, "files": rows, "dirs": by_dir.most_common()}, indent=2))
        return 0

    print(f"files changed in the last {a.days} days (top {len(rows)}), ranked by commits:\n")
    print(f"{'commits':>7} {'authors':>7}  {'tests?':<7} file")
    for r in rows:
        print(f"{r['commits']:>7} {r['authors']:>7}  {'yes' if r['test_mentions'] else 'NO':<7} {r['file']}")
    print("\nchurn by directory:")
    for d, n in by_dir.most_common(12):
        print(f"{n:>7}  {d}")
    untested = [r["file"] for r in rows if not r["test_mentions"]]
    if untested:
        print(f"\n{len(untested)} changed files not mentioned by any test; read these first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
