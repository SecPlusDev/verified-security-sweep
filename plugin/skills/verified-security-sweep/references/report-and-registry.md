# Report, registry, categories and coverage matrix: the formats

Contents: 1. Report format; 2. Registry; 3. Categories; 4. Coverage matrix; 5. Findings index
and recheck log.

Four files live in `docs/audits/`. The report is written per run; the other three are maintained.

## 1. Report: `docs/audits/YYYY-MM-DD-<zone-slug>.md`

The filename carries the date and the zone slug; `scripts/sweep_status.py` derives the "last run"
column of the registry from it, so the slug must contain the registry's zone name. A second run of
the same zone on the same day adds `-2`, `-3` to the slug; never overwrite an earlier report. A
recheck of earlier findings is a run of the zone, named the same way; "recheck" is not a zone.

```markdown
# Verified security sweep: <zone>, YYYY-MM-DD

## Context
Scope (zone, files or modules). Trigger (owner request, fresh code, registry age, pre-launch).
What changed in the zone since the last run. `Commit: <git rev-parse HEAD>`, the code the
citations were read at: `scripts/check_citations.py` reads them at that commit once the code
moves on. On a repository the reviewer does not own, one line instead:
`External review: yes, at <commit>, permalinks <repository URL>/blob/<commit>/`, then who
asked and the reviewer's relationship to the project.

## Delegation
Reviewers (how many, which agent or "fresh session"), the brief used, the pre-read each one did,
and the previous reports cited to them.

## Verification
| Finding | Zone | Verdict | Claimed | Verified | Reservations | Proof |
|---|---|---|---|---|---|---|
| P1 timing oracle on the public accept endpoint | public | VERIFIED REAL | High | Medium | needs the mail provider to be slow; window is one request | `public-accept-timing.test.ts`, ran, fails as expected: a slow mail provider left only the valid-email branch hanging |
| P2 no rate limit on the login endpoint | public | FALSE POSITIVE | Medium | - | lens: existing mitigation; the gateway limits to 10 requests per minute per IP | `infra/gateway.yaml:42`; `tests/guards/login-rate-limit.test.ts`, ran, passes |
| P3 hard-coded token secret "could be brute-forced" | auth | FALSE POSITIVE | High | - | lens: claim correctness; the value is a development placeholder, production refuses to start with it | `src/config.ts:18` |

## Confirmed defects
Per finding: location (`file:line`), class, evidence chain of three, scenario, fix approach
citing an existing pattern, and the reproduction: test name, each case with its expected result
on the current code (attack path fails, legitimate path passes) and its status.

## Refused or unconfirmed candidates
Every candidate that was examined and not confirmed, with one disposition each, so nobody
rediscovers it:
- refused: the lens that failed (exploitability, claim correctness, existing mitigation) and why;
- needs deeper review: what is missing to decide, and what would supply it;
- closed earlier: the previous report that closed it, and how;
- out of zone: the registry zone it belongs to, proposed as a sweep in the hand-off. Only for a
  defect of another zone; a candidate of this zone, whatever its class or severity, takes one of
  the first three.
"By design" or "intended" is a refusal under claim correctness: write it as one, with the code
or document that shows the intent. A file or behavior that was checked and holds no candidate is
not a refused candidate; it goes in Coverage ("checked, no defect"). Decisions that belong to the
owner (a product rule, an accepted risk) are listed here with "decision pending", and the
owner's answer is recorded in the registry's "Owner decisions" table when it comes. An
`OVER-RATED` candidate is real: it is confirmed at its verified severity, with a row in
Confirmed defects, a reproduction and an index entry at that severity, and the verification
row keeps the verdict `OVER-RATED` with `Claimed` above `Verified`; it is never written as
refused.

- P2, no rate limit on the login endpoint: refused, lens existing mitigation. The gateway applies
  10 requests per minute per IP (`infra/gateway.yaml:42`) and `tests/guards/login-rate-limit.test.ts`
  asserts it; a limit in the handler would be a second copy of the same control.
- P3, hard-coded token secret: refused, lens claim correctness. The value is a development
  placeholder; `src/config.ts:18` refuses to start in production with it, so the deployed secret is
  the one from the environment and the claim describes a configuration that cannot run.
- P4, session id not rotated on login: needs deeper review. Exploitation needs a way to plant a
  session cookie before login; deciding requires the subdomain and cookie-scope configuration of
  the deployment, which is not in the repository.
- P5, admin route reachable by any user: closed earlier, by the 2026-01-08 report (fixed and
  guarded by `tests/guards/admin-only.test.ts`); re-checked, still closed.

## Coverage
Files read, files skipped and why, lenses applied. If a calibration script was used, its output.

## Hand-off
Proposals, not changes: fixes to open as separate changes (with the reproduction test to ship
alongside), guard tests to adopt, defects of another class or zone seen during the run (with
`file:line`, as proposed sweeps of their zone; no verdict, not counted in this zone's yield), and
on a first run the one-line pointer from the rules file to `docs/audits/`. The sweep writes only
under `docs/audits/` and in the test folders.
```

Verification table: one row per candidate, including refused ones. `Claimed` is the severity the
reviewer gave, `Verified` the one that survived the three lenses, `Reservations` the text of the
"real, but" that a boolean would have swallowed. Proof is the test or the generated artifact, not
a sentence, and it always carries its status: `ran, fails as expected`, `ran, passes`, or
`written, not run: <reason>`. A live reproduction (the request sent and the response observed)
counts as ran. A test that was written but not run is never presented as proof on its own: name
what was observed instead, or the finding is not `VERIFIED REAL`.

These three columns make calibration measurable without any tooling beyond the report: across a
run, count how many verdicts lowered severity and how many carry a non-empty reservation. When
most "real" verdicts come with reservations, the reviewers are not permissive; the brief is
letting them inflate, and the brief is what to fix. Derive this from the reports, do not write it
by hand in the registry.

Rules of tone: plain status words (`OK`, `FIX`, `PARTIAL`, `NEW`), no emoji, no adjectives that
grade the codebase. The report describes what was read and what was found; the registry says which
zones were swept, when, and with what yield.

## 2. Registry: `docs/audits/sweep-registry.md`

```markdown
# Sweep registry: what exists, what ran, what it is worth

Proposals for sweeps are written here, not in conversation. The `Last run` column is derived
from report filenames by `scripts/sweep_status.py`; the other columns are written by hand.

## Candidates

| Zone | Argument | Last run | Yield |
|---|---|---|---|
| `fresh-code` | Code shipped in the last 3 days; highest yield, no guard yet. What it does not cover: ... | 2026-01-15 | 4/4 |
| `money` | Billing, quotas, crons; no mechanical invariant. | 2026-01-08 | 3/5 |

## Proposed, not yet run

| Zone | Argument | Premise to re-verify before starting |
|---|---|---|

## Candidates verified and refused

Written here so they are not rediscovered. A refused candidate without a written reason comes back.

## Owner decisions

| Date | Candidate | Question put to the owner | Decision | Result |
|---|---|---|---|---|
| 2026-01-15 | 2026-01-08-money/P6, refunds above the plan limit | is the limit a product rule or an omission? | omission; enforce it | re-verified, confirmed as F4 in `2026-01-15-money.md` |
```

Owner decisions: a candidate listed as "decision pending" in a report gets a row here when the
owner answers, with the date and the finding it produced or closed. A resolved decision
re-verifies the candidate under the answer and moves it to confirmed (a new report row, a
reproduction, an index entry) or to refused (the lens, citing the decision); the answer is part
of the code's history, and a later run re-verifies under it.

Zone cell: the slug in backticks first, then free text. The status script matches the slug
against report filenames.

## 3. Categories: `docs/audits/categories.md`

A list of categories, not patterns. A new pattern lands under an existing category. Each row
says how the category is covered in this project, and whether the coverage is a sentence or a
mechanical guard. When text and guard diverge, the guard is right: it runs, the text describes.

Generic starting list; delete what does not apply, add the project's own:

| Category | Covered by (examples; replace with the project's own) | Enforced mechanically? |
|---|---|---|
| Authentication and sessions | token algorithm pinned, revocation on password change, session store | |
| Second factor | single-use codes, backup codes hashed, lockout per user | |
| Identity across rows | one identity key for the person; the email is an attribute, never a join key | |
| Federation (SSO) | issuer pinned, state and nonce checked, discovery URLs restricted | |
| Tenant isolation | tenant key from the session on every query, including reads after writes, joins, aggregates | |
| Plan and entitlement enforcement | one gate for writes, explicit rule for reads on an expired plan, gate failure is an error not a pass | |
| Audit trail completeness | every state change writes an entry or states why not | |
| Audit integrity | entries append-only, no personal data in the entry body | |
| Input validation | allow-lists, content sniffing on uploads, path containment, spreadsheet formula prefix | |
| SQL construction | parametrized; interpolation carries structure, never values | |
| Secrets and crypto | validated at startup, placeholders refused, random tokens hashed at rest | |
| Security headers | CSP without unsafe-inline, HSTS, isolation headers, permissions policy | |
| External integrations | how each SDK reports errors (exception vs field), credential handling | |
| Frontend trust | server enforces every gate; UI mirrors it | |
| Generated documents | verified by rendering, not by reading the generator | |
| Spec drift | endpoint changed, spec updated in the same change | |
| Calendar day | local day of the deployment, never UTC day, on anything with legal or contractual meaning | |
| Concurrency | compare-and-set on state transitions, single-use tokens consumed atomically, locks before checks | |

## 4. Coverage matrix: `docs/audits/coverage-matrix.md` (optional)

Per feature or endpoint group: endpoints, module, last run, report reference, findings,
status. Statuses:

- `OK`: swept, all findings fixed and merged
- `FIX`: swept, findings open
- `PARTIAL`: some endpoints of the feature not covered
- `NEW`: never swept

Every new feature gets a `NEW` row before merge. The summary line is written by hand, so check
it mechanically against the rows; a summary that says every row is `OK` while several say `FIX` is
the "inventories that contradict" class, found in `docs/audits/` itself.

## 5. Findings index: `docs/audits/findings.jsonl`, and the recheck log

One JSON object per line, one line per confirmed finding (`VERIFIED REAL`, or `OVER-RATED` at
its verified severity), appended by the run that confirmed it and never rewritten by a later run (a later run changes `status` only, and only by the
owner's decision). `scripts/findings.py check` validates it.

| Field | Content |
|---|---|
| `id` | `<report name without .md>/<finding id>`, unique, for example `2026-01-15-money/F1` |
| `report` | the report filename in `docs/audits/` |
| `zone` | the registry zone |
| `commit` | `git rev-parse HEAD` when the sweep read the code; location and snippet describe that commit |
| `title` | one line a maintainer can act on |
| `severity` | `Critical`, `High`, `Medium` or `Low`, the verified one |
| `category` | the category from `categories.md` |
| `cwe` | optional, for example `CWE-639` |
| `location` | `path:line` from the repository root, the line a fix would change; the report cites it too |
| `snippet` | code that appears on that line, copied exactly; `findings.py check` fails if the line at `commit` does not hold it. Never a key or other secret: quote the non-secret part of the line |
| `reproduce` | a test-runner command, run from the repository root without a shell, that fails while the defect is present |
| `guard` | a test-runner command that must pass: the legitimate path of the same flow. Required, because it is what tells a fixed defect from a broken setup |
| `status` | `open`, or `accepted` when the owner decides to keep the behavior |

One entry, as written by a sweep of an `exports` zone whose report row F2 confirmed that any
signed-in user could download another organization's export:

```json
{"id": "2026-01-15-exports/F2", "report": "2026-01-15-exports.md", "zone": "exports",
 "commit": "<output of git rev-parse HEAD>", "title": "Export download is not scoped to the caller's organization",
 "severity": "High", "category": "Tenant isolation", "cwe": "CWE-639",
 "location": "app/exports/views.py:57", "snippet": "job = ExportJob.objects.get(pk=job_id)",
 "reproduce": ".venv/bin/python manage.py test app.exports.tests.test_review_scope.CrossOrgDownload",
 "guard": ".venv/bin/python manage.py test app.exports.tests.test_review_scope.OwnOrgDownload",
 "status": "open"}
```

The report's verification table has a `VERIFIED REAL` row for F2 citing `app/exports/views.py:57`,
and `CrossOrgDownload` fails on that commit while `OwnOrgDownload` passes.

`scripts/findings.py check` verifies each entry against the code at its `commit`, so entries stay
valid after the code changes. An entry whose commit is not in the clone (a squash merge, a
rebase, a shallow clone) is reported as not verifiable here, not as wrong.

`scripts/findings.py recheck --run --write` runs `guard` and then `reproduce` for every open
finding and appends one line per finding to `docs/audits/recheck-log.jsonl`: date, commit,
whether the working tree had uncommitted changes, id, result (`open`, `fixed`, `inconclusive`),
exit codes, and where the snippet is now. Run it where the project's tests run (its container,
its CI image, its virtual environment): on any other machine every guard fails and every result
is `inconclusive`, so read `inconclusive` first as an environment problem, then as a deleted
test. A failing guard makes the result `inconclusive`, never
`open`: a deleted test or a broken setup must not read as a defect that is still there. The
result never depends on line numbers. The log is the history; nothing in it is edited.

The commands are data from the repository. `findings.py` refuses a command that starts a shell
or passes inline code to an interpreter, and runs nothing without `--run`; list the commands and
read them before running them, as you would read a test suite before running it.

`scripts/findings.py sarif` writes the open findings as SARIF 2.1.0 to standard output, for a
code scanning view; `--all` adds the fixed and accepted ones.

