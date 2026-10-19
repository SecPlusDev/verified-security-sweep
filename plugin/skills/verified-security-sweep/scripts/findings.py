"""Confirmed findings as data: checked against the code, re-verified later, written as SARIF.

The report is for people. Next to it, docs/audits/findings.jsonl holds one JSON object per
confirmed finding, so that a later sweep, a CI job or another tool can use the findings without
parsing prose. Three subcommands:

    python3 findings.py check                    # entries well formed; each cited line holds its snippet
    python3 findings.py recheck                  # list the reproduction commands; nothing runs
    python3 findings.py recheck --run --write    # run them, append the results to recheck-log.jsonl
    python3 findings.py sarif > findings.sarif   # open findings as SARIF 2.1.0, for code scanning

One entry per line (fields described in references/report-and-registry.md, section 5):

    {"id": "2026-01-15-money/F1", "report": "2026-01-15-money.md", "zone": "money",
     "title": "Any member can read another tenant's invoice", "severity": "High",
     "category": "authorization", "cwe": "CWE-639",
     "commit": "<git rev-parse HEAD at the sweep>",
     "location": "src/billing/invoice.ts:42", "snippet": "where: { id: req.params.id }",
     "reproduce": "npx vitest run tests/billing/invoice-scope.test.ts -t 'other tenant'",
     "guard": "npx vitest run tests/billing/invoice-scope.test.ts -t 'own invoice'",
     "status": "open"}

check: every entry has the required fields, a known severity and status, and a unique id; its
report exists and cites its location; the location resolves to one file and a line inside it;
and that line contains the snippet (whitespace collapsed). A report's count of `VERIFIED REAL`
rows must equal its number of entries. The location and snippet describe the code at the entry's
`commit` and are checked there (git show), so an entry stays valid after the code moves on; an
entry without a commit is checked against the working tree. A commit missing from this clone
(squashed or rebased away, or a shallow clone) makes the entry unverifiable here, reported as
SKIP; --strict makes that a failure. A snippet that looks like a key or token, or that carries a
literal value on a line naming a secret (`"password": "abc def"`, a DSN with `user:password@`),
fails: the index must not copy a credential. `"password":` alone, the name without the value, is
fine. Lines the script prints (OK rows, "the line reads:") go through the same mask as
check_citations.py when they look like a credential.

recheck: for every entry whose status is "open", `reproduce` is a command that fails while the
defect is present. A failure means still open, a pass means fixed. `guard` runs first and must
pass; if it fails the result is inconclusive, because a deleted test, a missing dependency or a
broken legitimate path would otherwise read as "still open". Commands come from the repository's
audit folder, so they are only as trustworthy as the repository: they run only with --run,
without a shell, from the repository root, with a timeout, and a command that starts a shell or
passes inline code to an interpreter (`bash -c`, `python -c`, `node -e`) is refused, by check and
by recheck. That is a guard rail, not a sandbox: read the list before adding --run. Each result
records the commit and whether the working tree had uncommitted changes.
Line numbers play no part in the result. recheck also looks for the snippet in the current file
and prints where it is now ("now at path:N"), or that the code there changed; the index is never
rewritten.

sarif: entries still open (by status and by the latest recheck result) as SARIF results; --all
adds fixed and accepted ones. Written to standard output.

Exit codes: 0 done (for check: no invalid entry); 1 check found an invalid entry, or recheck
--fail-on-open found a finding still open; 2 setup error (no index, no audits folder).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import check_citations as cc  # noqa: E402  (sibling script: path resolution and file reading)

REQUIRED = ("id", "report", "zone", "title", "severity", "location", "snippet", "reproduce", "guard", "status")
SEVERITIES = ("Critical", "High", "Medium", "Low")
# "accepted": the owner decided to keep the behavior; recheck skips it and SARIF marks it suppressed.
STATUSES = ("open", "accepted")
# SARIF levels for the verified severity; Low findings are notes, never failures of a CI gate.
LEVELS = {"Critical": "error", "High": "error", "Medium": "warning", "Low": "note"}
LOCATION_RE = re.compile(r"^(.+):(\d+)$")
# Key-like tokens, secret names with literal values and the mask are shared with
# check_citations.py (cc.keylike, cc.sensitive, cc.mask); an index line quoting a credential
# would copy it into another file and into SARIF.
# Interpreters that run code given on the command line, and the flags that do it. A reproduction
# is a test file run by the project's runner; inline code in the index is refused.
INLINE_CODE = {"python": ("-c",), "node": ("-e", "--eval", "-p", "--print"), "ruby": ("-e",),
               "perl": ("-e", "-E"), "php": ("-r",), "npx": ("-c", "--call"), "npm": ("-c", "--call")}
# Default per-command timeout: a reproduction that needs more than five minutes is not a unit or
# integration test, and a hung command must not hang the whole recheck.
DEFAULT_TIMEOUT = 300


def squash(text: str) -> str:
    return " ".join(text.split())


def git_out(root: Path, *args: str) -> str | None:
    try:
        return subprocess.run(
            ["git", *args], cwd=root, check=True, capture_output=True, text=True, errors="replace"
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return None


def match_path(path: str, files: list[str]) -> list[str]:
    """The path itself if listed, otherwise every listed file that ends with it."""
    bare = path[2:] if path.startswith("./") else path
    if bare in files:
        return [bare]
    return [f for f in files if f.endswith("/" + bare)]


class Snapshot:
    """The code an entry was written against: its commit when it has one, else the working tree."""

    def __init__(self, root: Path):
        self.root = root
        self.tree_files = cc.index_files(root)
        self.commit_files: dict[str, list[str] | None] = {}

    def files(self, commit: str) -> list[str] | None:
        if not commit:
            return self.tree_files
        if commit not in self.commit_files:
            out = git_out(self.root, "ls-tree", "-r", "--name-only", commit)
            self.commit_files[commit] = out.splitlines() if out is not None else None
        return self.commit_files[commit]

    def lines(self, commit: str, path: str) -> list[str] | None:
        if not commit:
            target = self.root / path
            return cc.read_lines(target) if target.is_file() else None
        out = git_out(self.root, "show", f"{commit}:{path}")
        return out.splitlines() if out is not None else None


def relocate(entry: dict, snap: Snapshot) -> tuple[str, int | None]:
    """Where the snippet is in the working tree now: (message, line or None)."""
    m = LOCATION_RE.match(str(entry.get("location", "")))
    if not m:
        return "", None
    matches = match_path(m.group(1), snap.tree_files)
    if len(matches) != 1:
        return f"{m.group(1)} is no longer in the working tree", None
    lines = snap.lines("", matches[0]) or []
    needle = squash(str(entry.get("snippet", "")))
    hits = [i for i, text in enumerate(lines, 1) if needle and needle in squash(text)]
    recorded = int(m.group(2))
    if recorded in hits:
        return f"still at {matches[0]}:{recorded}", recorded
    if len(hits) == 1:
        return f"now at {matches[0]}:{hits[0]}", hits[0]
    if hits:
        shown = ", ".join(str(h) for h in hits[:5])
        return f"no longer at {entry['location']}; the snippet appears on lines {shown} of {matches[0]}", None
    return f"the code at {entry['location']} changed; the snippet is no longer in {matches[0]}", None


def load_index(index: Path) -> list[tuple[int, dict | None, str]]:
    """(line number, entry or None, parse error) for every non-blank line."""
    out = []
    for n, raw in enumerate(index.read_text(encoding="utf-8").splitlines(), 1):
        if not raw.strip():
            continue
        try:
            entry = json.loads(raw)
        except json.JSONDecodeError as e:
            out.append((n, None, f"not valid JSON: {e.msg}"))
            continue
        if not isinstance(entry, dict):
            out.append((n, None, "not a JSON object"))
            continue
        out.append((n, entry, ""))
    return out


def verified_real_rows(report: Path) -> int:
    return sum(1 for line in cc.read_lines(report) if line.lstrip().startswith("|") and "VERIFIED REAL" in line)


def refused(command: str) -> str:
    """Why a recorded command must not run, or "" when it is an ordinary program invocation."""
    try:
        argv = shlex.split(command)
    except ValueError as e:
        return f"cannot parse: {e}"
    if not argv:
        return "empty command"
    exe = Path(argv[0]).name.lower()
    if exe.endswith("sh"):
        return f"starts a shell ({exe})"
    for name, flags in INLINE_CODE.items():
        if exe == name or (exe.startswith(name) and exe[len(name):].replace(".", "").isdigit()):
            if any(a in flags for a in argv[1:]):
                return f"passes inline code to {exe}"
    return ""


def credential_in(snippet: str) -> str:
    """Why a snippet may copy a credential into the index, or '' when it does not."""
    if cc.keylike(snippet):
        return "snippet looks like a key or token; quote the non-secret part of the line"
    if cc.DSN_RE.search(snippet):
        return "snippet holds a DSN with user:password@; quote the non-secret part of the line"
    if cc.SECRET_NAME_RE.search(snippet) and cc.sensitive("", snippet):
        return "snippet holds a literal value next to a secret name; quote the name, never the value"
    return ""


def shown(path: str, text: str) -> str:
    """A line of repository text, masked when it looks like a credential."""
    return cc.shown_text(path, text)[0]


def check_entry(entry: dict, audits: Path, snap: Snapshot, strict: bool = False) -> tuple[list[str], str]:
    """(problems, skip reason): a skip means the entry cannot be verified in this clone."""
    problems = [f"missing field '{f}'" for f in REQUIRED if not str(entry.get(f, "")).strip()]
    if problems:
        return problems, ""
    for field in ("reproduce", "guard"):
        why = refused(str(entry[field]))
        if why:
            problems.append(f"{field} {why}; write the reproduction as a test the project's runner executes")
    why = credential_in(str(entry["snippet"]))
    if why:
        problems.append(why)
    if entry["severity"] not in SEVERITIES:
        problems.append(f"severity '{entry['severity']}' is not one of {', '.join(SEVERITIES)}")
    if entry["status"] not in STATUSES:
        problems.append(f"status '{entry['status']}' is not one of {', '.join(STATUSES)}")
    report = audits / entry["report"]
    if not report.is_file():
        problems.append(f"report {entry['report']} not found in {audits}")
    elif entry["location"] not in report.read_text(encoding="utf-8", errors="replace"):
        problems.append(f"report {entry['report']} does not cite {entry['location']}")
    m = LOCATION_RE.match(entry["location"])
    if not m:
        problems.append(f"location '{entry['location']}' is not path:line (one line)")
        return problems, ""
    path, line = m.group(1), int(m.group(2))
    commit = str(entry.get("commit", "")).strip()
    files = snap.files(commit)
    if files is None:
        why = f"commit {commit} is not in this clone (squashed, rebased or shallow history)"
        if strict:
            problems.append(why)
            return problems, ""
        return problems, why + "; not verifiable here"
    where = f" at {commit[:12]}" if commit else ""
    matches = match_path(path, files)
    if not matches:
        problems.append(f"{path}: no such file{where}")
        return problems, ""
    if len(matches) > 1:
        problems.append(f"{path}: matches several files{where} ({', '.join(sorted(matches)[:3])})")
        return problems, ""
    content = snap.lines(commit, matches[0]) or []
    if not 1 <= line <= len(content):
        problems.append(f"{entry['location']}: line out of range, file has {len(content)} lines")
        return problems, ""
    if squash(entry["snippet"]) not in squash(content[line - 1]):
        problems.append(f"{entry['location']} does not hold the snippet; the line reads: "
                        f"{shown(matches[0], content[line - 1].strip())}")
    return problems, ""


def cmd_check(entries, audits: Path, root: Path, strict: bool = False) -> int:
    snap = Snapshot(root)
    seen: dict[str, int] = {}
    per_report: dict[str, int] = {}
    bad = skipped = 0
    for n, entry, error in entries:
        if entry is None:
            print(f"FAIL  line {n}: {error}")
            bad += 1
            continue
        problems, skip = check_entry(entry, audits, snap, strict)
        ident = str(entry.get("id", f"line {n}"))
        if ident in seen:
            problems.append(f"duplicate id, first used on line {seen[ident]}")
        seen.setdefault(ident, n)
        if entry.get("report"):
            per_report[entry["report"]] = per_report.get(entry["report"], 0) + 1
        if problems:
            bad += 1
            for p in problems:
                print(f"FAIL  {ident}: {p}")
        elif skip:
            skipped += 1
            print(f"SKIP  {ident}: {skip}")
        else:
            at = f"@{str(entry['commit'])[:12]}" if str(entry.get("commit", "")).strip() else "(working tree)"
            print(f"OK    {ident}  {entry['location']} {at}  | {shown(entry['location'], squash(entry['snippet']))}")
    for name, count in sorted(per_report.items()):
        report = audits / name
        if report.is_file():
            rows = verified_real_rows(report)
            if rows != count:
                print(f"FAIL  {name}: {rows} VERIFIED REAL row(s) in the report, {count} entr(y/ies) in the index")
                bad += 1
    print(f"{len(entries)} entr(y/ies), {bad} problem(s), {skipped} not verifiable here")
    return 1 if bad else 0


def run_command(command: str, root: Path, timeout: int) -> tuple[int | None, str]:
    try:
        r = subprocess.run(shlex.split(command), cwd=root, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return None, "command not found"
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout} s"
    except ValueError as e:
        return None, f"cannot parse command: {e}"
    return r.returncode, ""


def head_commit(root: Path) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def cmd_recheck(entries, audits: Path, root: Path, args) -> int:
    open_entries = [e for _, e, _ in entries if e and e.get("status") == "open"]
    if not open_entries:
        print("no open findings in the index")
        return 0
    snap = Snapshot(root)
    if not args.run:
        for e in open_entries:
            print(f"{e.get('id')}  {e.get('location')}  | {relocate(e, snap)[0]}")
            if e.get("guard"):
                print(f"    guard:     {e['guard']}")
            print(f"    reproduce: {e.get('reproduce')}")
        print(f"{len(open_entries)} open finding(s); nothing was run (add --run)")
        return 0
    today, commit = date.today().isoformat(), head_commit(root)
    changes = git_out(root, "status", "--porcelain", "--", ".", f":(exclude){args.audits}")
    dirty = None if changes is None else bool(changes.strip())
    results = []
    for e in open_entries:
        guard_exit, note = None, ""
        if not str(e.get("guard", "")).strip():
            why = "no guard recorded"
        else:
            why = refused(str(e.get("reproduce", ""))) or refused(str(e["guard"]))
        if why:
            result, repro_exit = "inconclusive", None
            note = f"not run: {why}"
            where, _ = relocate(e, snap)
            print(f"{result.upper():<13} {e['id']}  {e.get('location')}  | {note}; {where}")
            results.append({"date": today, "commit": commit, "dirty": dirty, "id": e["id"], "result": result,
                            "reproduce_exit": None, "guard_exit": None, "where": where})
            continue
        guard_exit, note = run_command(e["guard"], root, args.timeout)
        if guard_exit != 0:
            result, repro_exit = "inconclusive", None
            note = note or f"guard failed (exit {guard_exit}): legitimate path or test setup broken"
        else:
            repro_exit, note = run_command(e["reproduce"], root, args.timeout)
            if repro_exit is None:
                result = "inconclusive"
            elif repro_exit == 0:
                result, note = "fixed", "reproduction passes"
            else:
                result, note = "open", f"reproduction still fails (exit {repro_exit})"
        where, _ = relocate(e, snap)
        print(f"{result.upper():<13} {e['id']}  {e.get('location')}  | {note}; {where}")
        results.append({"date": today, "commit": commit, "dirty": dirty, "id": e["id"], "result": result,
                        "reproduce_exit": repro_exit, "guard_exit": guard_exit, "where": where})
    if args.write:
        with (audits / "recheck-log.jsonl").open("a", encoding="utf-8") as fh:
            for r in results:
                fh.write(json.dumps(r) + "\n")
        print(f"appended {len(results)} result(s) to {audits / 'recheck-log.jsonl'}")
    counts = {k: sum(1 for r in results if r["result"] == k) for k in ("open", "fixed", "inconclusive")}
    print(f"{counts['open']} open, {counts['fixed']} fixed, {counts['inconclusive']} inconclusive")
    return 1 if args.fail_on_open and counts["open"] else 0


def latest_results(audits: Path) -> dict[str, str]:
    log = audits / "recheck-log.jsonl"
    latest: dict[str, str] = {}
    if log.is_file():
        for raw in log.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(r, dict) and r.get("id"):
                latest[r["id"]] = r.get("result", "")
    return latest


def cmd_sarif(entries, audits: Path, root: Path, args) -> int:
    snap = Snapshot(root)
    latest = latest_results(audits)
    rules: dict[str, dict] = {}
    results = []
    for _, e, _ in entries:
        if not e or any(not str(e.get(f, "")).strip() for f in REQUIRED):
            continue
        last = latest.get(e["id"], "")
        if not args.all and (e["status"] != "open" or last == "fixed"):
            continue
        rule_id = e.get("category") or "finding"
        if rule_id not in rules:
            rule = {"id": rule_id, "shortDescription": {"text": rule_id}}
            if e.get("cwe"):
                rule["properties"] = {"tags": ["external/cwe/" + str(e["cwe"]).lower()]}
            rules[rule_id] = rule
        m = LOCATION_RE.match(e["location"])
        path, line = (m.group(1), int(m.group(2))) if m else (e["location"], 1)
        matches = match_path(path, snap.tree_files)
        uri = matches[0] if len(matches) == 1 else path
        _, now = relocate(e, snap)
        line = now or line  # where the code is today, when the snippet is found once
        fingerprint = hashlib.sha256("\n".join((e["id"], uri, squash(e["snippet"]))).encode()).hexdigest()
        result = {
            "ruleId": rule_id,
            "level": LEVELS.get(e["severity"], "warning"),
            "message": {"text": e["title"]},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": uri}, "region": {"startLine": line}}}],
            "partialFingerprints": {"snippetHash/v1": fingerprint},
            "properties": {"id": e["id"], "report": e["report"], "zone": e["zone"], "severity": e["severity"],
                           "reproduce": e["reproduce"], "status": e["status"], "lastRecheck": last},
        }
        if e["status"] == "accepted":
            result["suppressions"] = [{"kind": "external", "justification": "accepted by the owner"}]
        results.append(result)
    sarif = {"version": "2.1.0", "runs": [{"tool": {"driver": {"name": "verified-security-sweep",
             "rules": list(rules.values())}}, "results": results}]}
    print(json.dumps(sarif, indent=2))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        epilog=__doc__.split("\n\n", 1)[1],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ap.add_argument("command", choices=("check", "recheck", "sarif"))
    ap.add_argument("--audits", default="docs/audits", help="audits folder, relative to the root (default: docs/audits)")
    ap.add_argument("--root", help="repository root (default: git top level of the current directory)")
    ap.add_argument("--run", action="store_true", help="recheck: run the commands (default: only list them)")
    ap.add_argument("--write", action="store_true", help="recheck --run: append the results to recheck-log.jsonl")
    ap.add_argument("--fail-on-open", action="store_true", help="recheck --run: exit 1 if a finding is still open")
    ap.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT, help=f"recheck: seconds per command (default: {DEFAULT_TIMEOUT})")
    ap.add_argument("--all", action="store_true", help="sarif: include fixed and accepted findings")
    ap.add_argument("--strict", action="store_true", help="check: an entry whose commit is not in this clone fails")
    args = ap.parse_args()

    root = cc.repo_root(args.root)
    audits = root / args.audits
    if not audits.is_dir():
        print(f"audits folder not found: {audits}", file=sys.stderr)
        return 2
    index = audits / "findings.jsonl"
    if not index.is_file():
        print(f"no findings index: {index}", file=sys.stderr)
        return 2
    if args.write and not args.run:
        print("--write needs --run", file=sys.stderr)
        return 2
    entries = load_index(index)
    if args.command == "check":
        return cmd_check(entries, audits, root, args.strict)
    if args.command == "recheck":
        return cmd_recheck(entries, audits, root, args)
    return cmd_sarif(entries, audits, root, args)


if __name__ == "__main__":
    sys.exit(main())
