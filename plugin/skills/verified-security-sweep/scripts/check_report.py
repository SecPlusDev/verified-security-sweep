"""Check a sweep report's structure: sections, verdicts, dispositions, and no lead of the zone
left in the hand-off without a verdict.

    python3 check_report.py docs/audits/2026-01-15-money.md
    python3 check_report.py docs/audits/2026-01-15-money.md --quiet

What it checks, in order:

1. The level-2 sections of the template are present: Context, Delegation, Verification,
   Confirmed defects, Refused or unconfirmed candidates, Coverage, Hand-off.
2. Every row of the Verification table carries one of the four verdicts: VERIFIED REAL,
   FALSE POSITIVE, OVER-RATED, NEEDS DEEPER REVIEW. Anything else ("LOW, recorded", "seen",
   "no verdict") is a row without a verdict.
3. Every entry of the refused section names its disposition: refused, needs deeper review,
   closed earlier, out of zone, or decision pending.
4. No candidate of the zone hides in the hand-off. The zone's scope is every path the report
   names in Context and every file it cites in Verification, Confirmed defects and the refused
   section (Coverage is left out: it also lists the files that were skipped). A `file:line` cited
   in the hand-off that is inside that scope must also be cited in one of those three sections,
   the ones where verdicts and dispositions live (a fix proposal reuses the location of its
   finding), or the hand-off item must name a finding of the Verification table (F2, R3, AC-1).
   A citation in any other section (Context, Coverage, a recheck narrative) does not count: a
   first version of this check accepted "cited anywhere earlier", and a run answered it by
   adding a sentence elsewhere instead of a verdict. Otherwise it is a lead of this zone that
   never got a verdict, and the report fails.
5. An external review is anchored. A Context line `External review: yes` (a repository the
   reviewer does not own, SKILL.md "External review") must come with the commit reviewed (a
   hexadecimal id of 7 to 40 characters) and the permalink base the citations resolve against
   (an `http(s)://` URL) in the same section; without both, a `file:line` in the delivered
   record points at nothing the maintainer can open.

Exit codes: 0 no problem; 1 at least one problem (each printed with its line number); 2 the
report could not be read.

The script reads only the report; it needs no repository and runs nothing.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.dont_write_bytecode = True  # no __pycache__ inside the installed plugin folder
sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_citations as cc  # noqa: E402  (sibling script: the citation pattern and line spans)

# The seven level-2 sections of references/report-and-registry.md, matched on their first word(s)
# so that "## Refused or unconfirmed candidates" and "## Refused candidates" both count.
REQUIRED_SECTIONS = (
    ("context", "Context"),
    ("delegation", "Delegation"),
    ("verification", "Verification"),
    ("confirmed", "Confirmed defects"),
    ("refused", "Refused or unconfirmed candidates"),
    ("coverage", "Coverage"),
    ("hand-off", "Hand-off"),
)

# The four verdicts of references/finding-verification.md; nothing else is a verdict.
VERDICTS = ("VERIFIED REAL", "FALSE POSITIVE", "OVER-RATED", "NEEDS DEEPER REVIEW")

# The dispositions of the refused section (report-and-registry.md, section 1), plus the owner's
# "decision pending". Matched case-insensitively anywhere in the entry.
DISPOSITIONS = ("refused", "needs deeper review", "closed earlier", "out of zone", "decision pending")

# A backticked token counts as a path when it has a directory part or a file extension and no
# spaces: `hc/api/views.py`, `src/billing/`, `manage.py`. Symbols like `Check.to_dict` have a dot
# but no slash and a capitalised first segment; they are excluded by the lowercase-start rule
# below, which is a heuristic: a path the report writes as `Models/Thing.py` is missed, and a
# missed scope entry can only make the hand-off check more lenient, never stricter.
BACKTICK_RE = re.compile(r"`([^`\s]+)`")
PATH_LIKE_RE = re.compile(r"^(?:[a-z0-9_.-]+/)+[\w.-]*$|^[a-z0-9_-]+\.[a-z0-9]{1,6}$")

# The Context line that declares a review of someone else's repository, and its two anchors.
EXTERNAL_RE = re.compile(r"(?i)^\s*(?:[-*]\s*)?\**external review\**\s*:\s*\**\s*yes\b")
COMMIT_RE = re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{7,40}(?![0-9a-zA-Z])")
URL_RE = re.compile(r"https?://\S+")

# A finding id as the Verification table writes it in its first column: F1, R12, AC-2, P4.
FINDING_ID_RE = re.compile(r"^\s*\**`?([A-Z]{1,4}-?\d{1,3})\b")


def section_key(heading: str) -> str | None:
    text = heading.lower()
    for key, _ in REQUIRED_SECTIONS:
        if text.startswith(key):
            return key
    return None


def split_sections(lines: list[str]) -> dict[str, tuple[int, int]]:
    """Map section key -> (first line index after the heading, end index), 0-based."""
    heads = [(i, line[3:].strip()) for i, line in enumerate(lines) if line.startswith("## ")]
    out: dict[str, tuple[int, int]] = {}
    for n, (i, title) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        key = section_key(title)
        if key and key not in out:
            out[key] = (i + 1, end)
    return out


def strip_cell(cell: str) -> str:
    return cell.strip().strip("`*_ ").strip()


def table_rows(lines: list[str], start: int, end: int) -> tuple[list[str], list[tuple[int, list[str]]]]:
    """The first markdown table in the span: its header cells and (line number, cells) rows."""
    header: list[str] = []
    rows: list[tuple[int, list[str]]] = []
    i = start
    while i < end:
        line = lines[i]
        if line.lstrip().startswith("|"):
            cells = [c for c in line.strip().strip("|").split("|")]
            if not header:
                header = [strip_cell(c) for c in cells]
            elif re.fullmatch(r"[\s|:-]+", line.strip()):
                pass
            else:
                rows.append((i + 1, [c.strip() for c in cells]))
            i += 1
            continue
        if header:
            break
        i += 1
    return header, rows


def bullets(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    """Top-level list items in the span, each as (line number, full text with continuation)."""
    items: list[tuple[int, str]] = []
    for i in range(start, end):
        line = lines[i]
        if re.match(r"^(?:[-*]|\d+\.)\s+", line):
            items.append((i + 1, line.strip()))
        elif items and line.startswith((" ", "\t")) and line.strip():
            n, text = items[-1]
            items[-1] = (n, text + " " + line.strip())
    return items


def paragraphs(lines: list[str], start: int, end: int) -> list[tuple[int, str]]:
    """Bullets where there are bullets, otherwise blank-line separated paragraphs."""
    items = bullets(lines, start, end)
    if items:
        return items
    out: list[tuple[int, str]] = []
    cur: list[str] = []
    first = 0
    for i in range(start, end):
        if lines[i].strip():
            if not cur:
                first = i + 1
            cur.append(lines[i].strip())
        elif cur:
            out.append((first, " ".join(cur)))
            cur = []
    if cur:
        out.append((first, " ".join(cur)))
    return out


def citations(text: str) -> list[tuple[str, list[tuple[int, int]]]]:
    out = []
    for m in cc.CITATION_RE.finditer(text):
        try:
            out.append((m.group(1), cc.parse_lines(m.group(3))))
        except ValueError:
            continue
    return out


def path_tokens(text: str) -> set[str]:
    out = set()
    for m in BACKTICK_RE.finditer(text):
        tok = m.group(1)
        if PATH_LIKE_RE.match(tok):
            out.add(tok)
    return out


def in_scope(path: str, scope_files: set[str], scope_dirs: set[str]) -> bool:
    if path in scope_files:
        return True
    return any(path.startswith(d) for d in scope_dirs)


def overlaps(a: list[tuple[int, int]], b: list[tuple[int, int]]) -> bool:
    return any(x1 <= y2 and y1 <= x2 for x1, x2 in a for y1, y2 in b)


def check(report: Path) -> tuple[list[tuple[int, str]], dict]:
    lines = report.read_text(encoding="utf-8").splitlines()
    problems: list[tuple[int, str]] = []
    sections = split_sections(lines)
    summary = {"verified_real": 0, "rows": 0, "refused_entries": 0, "handoff_citations": 0, "external": False}

    for key, name in REQUIRED_SECTIONS:
        if key not in sections:
            problems.append((0, f"MISSING SECTION: no '## {name}' heading"))

    # 5. An external review names its anchors
    if "context" in sections:
        s, e = sections["context"]
        for i in range(s, e):
            if EXTERNAL_RE.match(lines[i]):
                summary["external"] = True
                text = "\n".join(lines[s:e])
                missing = [what for what, rx in (("the commit reviewed", COMMIT_RE), ("the permalink base URL", URL_RE))
                           if not rx.search(text)]
                if missing:
                    problems.append((i + 1, "EXTERNAL REVIEW WITHOUT ANCHOR: 'External review: yes' needs "
                                            + " and ".join(missing) + " in Context"))
                break

    # 2. Verdicts
    finding_ids: set[str] = set()
    if "verification" in sections:
        s, e = sections["verification"]
        header, rows = table_rows(lines, s, e)
        if not header:
            problems.append((s, "NO TABLE: the Verification section has no table"))
        else:
            try:
                v_col = [h.lower() for h in header].index("verdict")
            except ValueError:
                v_col = -1
                problems.append((s, "NO VERDICT COLUMN: the Verification table has no 'Verdict' column"))
            for n, cells in rows:
                summary["rows"] += 1
                m = FINDING_ID_RE.match(cells[0]) if cells else None
                if m:
                    finding_ids.add(m.group(1))
                if v_col < 0 or v_col >= len(cells):
                    continue
                verdict = strip_cell(cells[v_col]).upper()
                if verdict == "VERIFIED REAL":
                    summary["verified_real"] += 1
                if verdict not in VERDICTS:
                    problems.append((n, f"NOT A VERDICT: '{strip_cell(cells[v_col])}' (one of {', '.join(VERDICTS)})"))

    # 3. Dispositions
    if "refused" in sections:
        s, e = sections["refused"]
        for n, text in bullets(lines, s, e):
            summary["refused_entries"] += 1
            low = text.lower()
            if not any(d in low for d in DISPOSITIONS):
                problems.append((n, f"NO DISPOSITION: entry names none of {', '.join(DISPOSITIONS)}"))

    # 4. Leads of the zone in the hand-off
    if "hand-off" in sections:
        hs, he = sections["hand-off"]
        scope_files: set[str] = set()
        scope_dirs: set[str] = set()
        for key in ("context",):
            if key in sections:
                s, e = sections[key]
                for tok in path_tokens("\n".join(lines[s:e])):
                    if tok.endswith("/") or "." not in tok.rsplit("/", 1)[-1]:
                        scope_dirs.add(tok.rstrip("/") + "/")
                    else:
                        scope_files.add(tok)
        verdict_cites: list[tuple[str, list[tuple[int, int]]]] = []
        for key in ("verification", "confirmed", "refused"):
            if key in sections:
                s, e = sections[key]
                for path, spans in citations("\n".join(lines[s:e])):
                    scope_files.add(path)
                    verdict_cites.append((path, spans))
        for n, text in paragraphs(lines, hs, he):
            named = {t for t in re.findall(r"\b([A-Z]{1,4}-?\d{1,3})\b", text)} & finding_ids
            for path, spans in citations(text):
                summary["handoff_citations"] += 1
                if not in_scope(path, scope_files, scope_dirs):
                    continue
                if named:
                    continue
                if any(p == path and overlaps(sp, spans) for p, sp in verdict_cites):
                    continue
                shown = f"{path}:{','.join(str(a) if a == b else f'{a}-{b}' for a, b in spans)}"
                problems.append((n, f"LEAD WITHOUT VERDICT: hand-off cites {shown}, inside the zone's scope and absent from "
                                    "Verification, Confirmed defects and the refused section; a candidate of this zone takes "
                                    "a verdict or a disposition there, not a hand-off"))
    return problems, summary


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("report", help="path of the report (docs/audits/YYYY-MM-DD-<zone>.md)")
    ap.add_argument("--quiet", action="store_true", help="print only the problems")
    args = ap.parse_args()
    report = Path(args.report)
    if not report.is_file():
        print(f"cannot read {report}", file=sys.stderr)
        return 2
    try:
        problems, summary = check(report)
    except UnicodeDecodeError as exc:
        print(f"cannot read {report}: {exc}", file=sys.stderr)
        return 2
    for n, msg in problems:
        print(f"{report}:{n}: {msg}")
    if not args.quiet:
        print(f"{summary['rows']} verification rows ({summary['verified_real']} VERIFIED REAL), "
              f"{summary['refused_entries']} refused entries, {summary['handoff_citations']} hand-off citations, "
              f"{'external review, ' if summary['external'] else ''}{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
