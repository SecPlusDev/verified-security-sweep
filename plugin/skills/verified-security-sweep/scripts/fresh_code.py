"""Rank recently changed source files as sweep candidates.

Fresh code is the zone with the highest audit yield: the author's assumptions are still in it
and no guard exists yet. This script lists files changed in the last N days, ranked by number of
commits touching them, and flags files whose basename is not mentioned by any test file.

    python3 fresh_code.py                     # last 3 days, src-like paths, top 40
    python3 fresh_code.py --days 14 --top 60
    python3 fresh_code.py --src api/src web/src --tests api/tests web/src
    python3 fresh_code.py --ext .proto .tf    # more extensions than the built-in list
    python3 fresh_code.py --json             # machine-readable

The "no test mentions it" flag is a heuristic (the file's stem searched as a whole word across
test files), good enough to decide where to read first, not a coverage measurement.

When every commit of the repository falls inside the window (a single commit, a fresh import),
churn ranks nothing: every file has the same count. The script says so and ranks by size
instead, largest first, with the test flag; a first sweep of an imported tree reads the big
untested files first. When changed files exist but none has a listed extension, the script says
how many were filtered and which extensions they had, so an empty list is never silent; a
field report blamed a single commit for an empty list whose cause was a `.rs` extension.

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

# Files worth reading in a sweep: application code, SQL and shell, in the languages a sweep is
# likely to meet. Markup, styles, lockfiles and generated assets churn constantly and are not
# where defects live, so they are left out; --ext adds to the list for a stack missing here.
SOURCE_EXT = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".vue", ".svelte",
    ".py", ".go", ".rb", ".java", ".kt", ".kts", ".scala", ".cs", ".php", ".sql", ".sh", ".bash",
    ".rs", ".c", ".h", ".cc", ".cpp", ".hpp", ".m", ".mm", ".swift", ".dart", ".zig",
    ".ex", ".exs", ".erl", ".hs", ".clj", ".lua", ".pl", ".r", ".jl", ".sol", ".groovy", ".ps1",
}
# A path containing any of these is a test, in the conventions of the ecosystems above
# (pytest, Jest, RSpec, Go tests, and a "guards" folder for invariant tests).
TEST_MARKERS = ("test", "spec", "__tests__", "guards")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def changed_files(days: int, exts: set[str]) -> tuple[Counter, dict[str, dict[str, None]], Counter, int]:
    """(commits per source file, authors per source file, filtered-out extensions with counts,
    number of commits in the window)."""
    log = git("log", f"--since={days}.days", "--name-only", "--pretty=format:@@%h %an")
    commits: Counter = Counter()
    authors: dict[str, dict[str, None]] = defaultdict(dict)
    filtered: Counter = Counter()
    current = None
    n_commits = 0
    for line in log.splitlines():
        if line.startswith("@@"):
            current = line[2:].split(" ", 1)
            n_commits += 1
            continue
        f = line.strip()
        if not f or current is None:
            continue
        p = Path(f)
        if p.suffix not in exts:
            filtered[p.suffix or "(none)"] += 1
            continue
        commits[f] += 1
        authors[f][current[1] if len(current) > 1 else "?"] = None
    return commits, authors, filtered, n_commits


def total_commits() -> int:
    try:
        return int(git("rev-list", "--count", "HEAD").strip() or 0)
    except (subprocess.CalledProcessError, ValueError):
        return 0


def file_size(path: str) -> int:
    try:
        return Path(path).stat().st_size
    except OSError:
        return 0


def is_test(path: str) -> bool:
    low = path.lower()
    return any(m in low for m in TEST_MARKERS)


def under(path: str, roots: list[str]) -> bool:
    return not roots or any(path.startswith(r.rstrip("/") + "/") or path == r for r in roots)


def test_corpus(test_roots: list[str], exts: set[str]) -> str:
    """The text of every tracked test file (a path with a test marker and a listed extension),
    under the given roots or anywhere in the repository when none is given."""
    chunks = []
    try:
        tracked = git("ls-files", "-z").split("\0")
    except subprocess.CalledProcessError:
        tracked = []
    for f in tracked:
        if not f or not is_test(f) or Path(f).suffix not in exts or not under(f, test_roots):
            continue
        try:
            chunks.append(Path(f).read_text(encoding="utf-8", errors="ignore"))
        except OSError:
            pass
    return "\n".join(chunks)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=3, help="window in days; 3 covers a long weekend of commits and stays readable in one sweep (default 3)")
    ap.add_argument("--top", type=int, default=40, help="files listed; 40 is about what one reviewer reads in a session (default 40)")
    ap.add_argument("--src", nargs="*", default=[], help="restrict to these roots (default: all non-test source)")
    # Roots whose tracked test files are read (a path with a test marker counts); the default
    # is the whole repository, so a workspace with tests under each crate or package is covered.
    ap.add_argument("--tests", nargs="*", default=[], help="roots to scan for test files (default: every tracked test file)")
    ap.add_argument("--ext", nargs="*", default=[], metavar="EXT", help="extensions to read in addition to the built-in list (for example .proto .tf)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    exts = SOURCE_EXT | {e if e.startswith(".") else "." + e for e in a.ext}

    try:
        git("rev-parse", "--is-inside-work-tree")
    except subprocess.CalledProcessError:
        print("not a git repository", file=sys.stderr)
        return 2

    try:
        commits, authors, filtered, n_commits = changed_files(a.days, exts)
    except subprocess.CalledProcessError as e:
        print(f"git log failed (no commits yet?): {e.stderr.strip() or e}", file=sys.stderr)
        return 2
    # Every commit inside the window: churn is the same for every file, size ranks instead.
    whole_history = n_commits > 0 and n_commits >= total_commits()
    corpus = test_corpus(a.tests, exts)
    rows = []
    for f, n in commits.most_common():
        if is_test(f) or not under(f, a.src):
            continue
        stem = Path(f).stem
        # whole-word match, so `app.py` is not "mentioned" by a test that says "application"
        mentioned = re.search(rf"(?<![A-Za-z0-9_]){re.escape(stem)}(?![A-Za-z0-9_])", corpus) is not None
        rows.append({"file": f, "commits": n, "authors": len(authors[f]), "test_mentions": mentioned,
                     "bytes": file_size(f)})
    if whole_history:
        rows.sort(key=lambda r: (r["test_mentions"], -r["bytes"]))
    rows = rows[: a.top]
    note = ""
    if not rows and filtered:
        shown = ", ".join(f"{e} ({n})" for e, n in filtered.most_common(6))
        note = (f"no file with a listed extension changed; {sum(filtered.values())} changed path(s) were "
                f"filtered out by extension: {shown}; add one with --ext")
    elif whole_history:
        note = (f"every commit of the repository ({n_commits}) is inside the window, so churn ranks nothing: "
                f"files ranked by size, untested first")

    by_dir: Counter = Counter()
    for r in rows:
        by_dir[str(Path(r["file"]).parent)] += r["commits"]

    if a.json:
        print(json.dumps({"days": a.days, "files": rows, "dirs": by_dir.most_common(), "note": note,
                          "filtered": filtered.most_common()}, indent=2))
        return 0

    ranked = "size (every file is fresh)" if whole_history else "commits"
    print(f"files changed in the last {a.days} days (top {len(rows)}), ranked by {ranked}:\n")
    if note:
        print(f"note: {note}\n")
    print(f"{'commits':>7} {'authors':>7} {'bytes':>8}  {'tests?':<7} file")
    for r in rows:
        print(f"{r['commits']:>7} {r['authors']:>7} {r['bytes']:>8}  {'yes' if r['test_mentions'] else 'NO':<7} {r['file']}")
    print("\nchurn by directory:")
    for d, n in by_dir.most_common(12):
        print(f"{n:>7}  {d}")
    untested = [r["file"] for r in rows if not r["test_mentions"]]
    if untested:
        print(f"\n{len(untested)} changed files not mentioned by any test; read these first.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
