"""Sweep registry, checked against the real reports in the audits folder.

A hand-written registry goes stale. Here the zone and its argument are written by hand (they
cannot be derived), but the date of the last run is read from report filenames
(`YYYY-MM-DD-<slug>.md`), and any divergence between the registry text and the files is flagged.

    python3 sweep_status.py                      # report, defaults: docs/audits, sweep-registry.md
    python3 sweep_status.py --check              # exit code 1 on divergence (for CI)
    python3 sweep_status.py --audits docs/audits --registry docs/audits/registry.md
    python3 sweep_status.py --stale-days 60      # flag zones older than N days

Registry format: a Markdown table whose first column holds the zone slug in backticks, e.g.
`| `money` | Billing, quotas, crons | 2026-01-15 | 3/5 |`. Only the first table under the
candidates heading is read: a heading that contains "candidate" and none of "proposed",
"refused", "rejected", "verified". Parsing stops at the next heading after that section, so the
proposed and refused tables are never read.

A zone matches a report when the hyphen-separated tokens of one are a contiguous run of the
other's: `money` matches `2026-01-15-money.md` and `2026-01-15-money-crons.md`, but `auth` does
not match `2026-01-15-oauth-callbacks.md`.

Exit codes: 0 no divergence (or --check not given), 1 divergence with --check, 2 setup error
(missing folder or registry, no dated reports, no candidate rows).
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date
from pathlib import Path

REPORT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})-(.+)\.md$")
DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")


def reports(audits: Path) -> list[tuple[date, str]]:
    out = []
    for p in audits.glob("20*.md"):
        m = REPORT_RE.match(p.name)
        if not m:
            continue
        try:
            out.append((date(int(m[1]), int(m[2]), int(m[3])), m[4]))
        except ValueError:
            print(f"skipping {p.name}: not a calendar date", file=sys.stderr)
    return sorted(out)


NOT_CANDIDATES = ("proposed", "refused", "rejected", "verified")


def is_candidates_heading(line: str) -> bool:
    text = line.lstrip("#").strip().lower()
    return "candidate" in text and not any(word in text for word in NOT_CANDIDATES)


def registry_rows(registry: Path) -> list[dict]:
    """Rows of the first table under the candidates heading (see the module docstring)."""
    rows, in_section, in_table, seen_section = [], False, False, False
    for line in registry.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            if seen_section:
                break
            in_section = is_candidates_heading(line)
            seen_section = in_section
            continue
        if not in_section:
            continue
        if line.startswith("|"):
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            if len(cells) < 3 or all(c in "-: " for c in cells[0]):
                in_table = True
                continue
            slug_m = re.search(r"`([^`]+)`", cells[0])
            if not slug_m:
                if in_table:
                    continue  # header row
                continue
            in_table = True
            dates = DATE_RE.findall(cells[2]) if len(cells) > 2 else []
            rows.append({"zone": slug_m[1], "declared": dates[-1] if dates else None, "argument": cells[1]})
        elif in_table and line.strip() == "":
            break
    return rows


def _is_run(short: list[str], long: list[str]) -> bool:
    n = len(short)
    return n > 0 and any(long[i:i + n] == short for i in range(len(long) - n + 1))


def slug_matches(zone: str, slug: str) -> bool:
    a, b = zone.lower().split("-"), slug.lower().split("-")
    return _is_run(a, b) or _is_run(b, a)


def last_run(zone: str, reps: list[tuple[date, str]]) -> date | None:
    hits = [d for d, slug in reps if slug_matches(zone, slug)]
    return max(hits) if hits else None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--audits", default="docs/audits")
    ap.add_argument("--registry", default=None, help="default: <audits>/sweep-registry.md")
    ap.add_argument("--stale-days", type=int, default=60, help="flag zones not swept for this many days; 60 is two release cycles for most teams (default 60)")
    ap.add_argument("--min-reports", type=int, default=1, help="below this, extraction is considered broken")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()

    audits = Path(a.audits)
    registry = Path(a.registry) if a.registry else audits / "sweep-registry.md"
    if not audits.is_dir():
        print(f"audits folder not found: {audits}", file=sys.stderr)
        return 2
    if not registry.is_file():
        print(f"registry not found: {registry}", file=sys.stderr)
        return 2

    reps = reports(audits)
    if len(reps) < a.min_reports:
        print(f"only {len(reps)} dated reports found in {audits}; extraction looks broken", file=sys.stderr)
        return 2
    rows = registry_rows(registry)
    if not rows:
        print(f"no candidate rows with a backticked zone slug found in {registry}", file=sys.stderr)
        return 2

    today = date.today()
    divergent, stale = [], []
    print(f"{'zone':<34} {'declared':<12} {'from reports':<12} {'age':>5}  note")
    for r in rows:
        derived = last_run(r["zone"], reps)
        note = []
        if derived is None and r["declared"]:
            note.append("registry declares a run but no report matches slug")
            divergent.append(r["zone"])
        elif derived is None:
            note.append("no report matches slug")
        elif r["declared"] and r["declared"] != derived.isoformat():
            note.append("registry text differs from reports")
            divergent.append(r["zone"])
        age = (today - derived).days if derived else None
        if age is not None and age > a.stale_days:
            note.append(f"stale > {a.stale_days}d")
            stale.append(r["zone"])
        print(f"{r['zone']:<34} {r['declared'] or '-':<12} {derived.isoformat() if derived else '-':<12} {str(age) if age is not None else '-':>5}  {'; '.join(note)}")

    print()
    print(f"{len(rows)} zones, {len(reps)} dated reports, {len(divergent)} divergent, {len(stale)} stale")
    if a.check and divergent:
        print("registry text and report filenames disagree for: " + ", ".join(divergent), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
