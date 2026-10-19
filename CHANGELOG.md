# Changelog

All notable changes to this skill. Versions follow semver; each release attaches the `.skill`
archive built by CI from the tagged commit.

## Unreleased

Candidates for v1.4.1, from an external review run on 2026-10-19 (a first sweep of a third-party
repository that holds committed credentials) and from the real-code runs of 2026-10-16 and
2026-10-17. Each lands as its own pull request; the version is tagged once the round is measured.

- `check_citations.py` prints credential-like lines masked, as `OK (masked)`: dotenv files, a
  secret name with a literal value, a DSN with `user:password@`, a key-like token. Every string
  literal that is a value, every value after `=` or `:`, every DSN password and every key-like
  token becomes `<masked, N chars>`; names and structure stay. No option to unmask. The same
  predicate and mask are used by `findings.py`: `check` refuses a snippet that holds a literal
  next to a secret name or a DSN (`"password":` alone stays allowed), and the lines it prints go
  through the mask. A dotenv path (`app/.env:3`) is now a citation. SKILL.md step 5 says never to
  print such a line by other means. Found by an external run where the mandatory citation check
  printed an app password and a key default into the session transcript.
- `leak_check.py`, the sixth script: collects credential-like values from the repository (dotenv
  values whose key names a secret, literals next to secret names, DSN passwords, key-like
  tokens; `--from-cited <report>` limits the files to the ones the report cites) and searches
  `docs/audits/`, the test files git reports as changed, and any `--extra` path (zip containers
  such as a workbook member by member) for them. `FAIL` for a value of 8 characters or more,
  `WARN` for a shorter one that may be a coincidence (`--strict` makes it a failure); sources,
  lengths and masked context printed, never a value, nothing written. Checklist step 6 requires
  it to exit 0; `references/finding-verification.md` says how a credential is verified: by shape
  and boolean, never by printing it, never by trying it. Six tests.

## v1.4.0 (2026-10-13)

The release of the v1.3 line. Versions 1.2.x and 1.3.x below were built and measured but never
tagged; this is the first release since v1.1.0 and carries everything from them. Measured on
Opus 5.5 and Sonnet 5.5 (`evals/results/round-v1.3.4.md`, `trigger-2026-10-v1.3.1.md`,
`install-2026-10-13.md`); the README has the figures and the known gaps.

### Since v1.1.0, in short
- Renamed `verified-security-sweep`: a verified, recorded security review, not an audit.
- `docs/audits/findings.jsonl`, one line per confirmed finding anchored to a commit, with the
  reproduction and the legitimate-path guard as test-runner commands; `findings.py` checks it,
  re-runs it (`recheck`, open, fixed or inconclusive, with a log) and writes SARIF. Shells and
  inline interpreter code are refused as recorded commands; a recorded command that is not the
  test runner is shown to the user and nothing runs.
- `check_citations.py`: every cited `file:line` opened and printed. `check_report.py`: every
  section present, every verification row with one of the four verdicts, every refused entry
  with a disposition, no lead of the zone cited only in the hand-off.
- A recheck is a run of the zone (slug in the file name, registry row updated); a refused
  recorded command is quoted exactly; tests leave no build output; one term per concept.
- Stack probes for Java, C#, Rust and PHP next to Node, Python, Ruby, Go, infrastructure and
  frontend.
- The description is the one measured in `trigger-2026-10-v1.3.1.md`, alone and next to
  another skill collection.

### Changed before the first public commit
- Two figures in the references that came from the origin project as exact counts are now
  bands, and `fresh_code.py`'s example and default roots are generic: a pre-publication read
  found them specific enough to fingerprint the project.
- The leakage term list left the repository (`docs/BUILD.md`, section 1): a hashed list of
  short names is recovered by guessing, so the terms are a repository secret and an ignored
  local file, and the public list keeps the generic shapes only.
- Evaluation artifacts: machine paths, local clock offsets, reviewer transcript ids and the
  account's skill inventory were replaced by neutral wording. No figure changed.

## v1.3.5 (2026-10-13)

### Added
- `references/stack-probes.md`: probe sections for Java / Spring, C# / ASP.NET Core / EF Core,
  Rust / axum or actix / sqlx, and PHP / Laravel, in the shape of the existing ones (query
  building, lookups by id without an owner, endpoints without authorization, mass assignment,
  deserialization, dates without a zone). Each block was checked for shell syntax and against
  small samples; none has been measured in an evaluation run.

### Changed
- `scripts/check_report.py --help` now carries the full description, the usage examples and the
  exit codes, like the other four scripts; the install test (B6) found it was the only one
  without them.

The description is unchanged; held-out set 2 stays valid.

## v1.3.4 (2026-10-13)

### Changed
- `scripts/check_report.py`: a hand-off citation inside the zone's scope now has to appear in
  Verification, Confirmed defects or the refused section, where verdicts and dispositions
  live. v1.3.3 accepted "cited anywhere earlier in the report", and in the first run with it
  (round v1.3.3, eval 7) the model answered the two flagged lines by adding a sentence to a
  narrative section instead of a verdict. One test reproduces that answer.

The description is unchanged; held-out set 2 stays valid.

## v1.3.3 (2026-10-12)

### Added
- `scripts/check_report.py`: reads the report and fails it when a template section is missing,
  a verification row carries anything but one of the four verdicts, a refused entry names no
  disposition, or a `file:line` inside the zone's scope (the paths named in Context and the
  files cited in Verification, Confirmed defects and the refused section) is cited only in the
  hand-off. The last check is mechanical because two rounds of text (v1.3.1, v1.3.2) did not
  stop the model from labelling leads of the zone as another zone's and handing them off
  without a verdict. Step 5 runs it until it exits 0, next to `check_citations.py`.

The description is unchanged; held-out set 2 stays valid.

## v1.3.2 (2026-10-12)

Text corrections from round v1.3.1 (`evals/results/round-v1.3.1.md`); the method is unchanged.

### Changed
- Every candidate inside the zone gets one of the four verdicts; "no verdict here" is reserved
  for a defect of another registry zone, which now has its own disposition in the refused
  section ("out of zone: proposed sweep of <zone>") and goes to the hand-off as that proposal.
  In the round, candidates of the swept zone were being left unverdicted under that rule.
- A recheck of earlier findings is a run of the zone: its report carries the zone slug and
  updates the registry row. Both continuity runs had left the slug out on purpose, so the
  registry did not see them.
- When a recorded command is not a test-runner invocation, the user is shown the command
  quoted exactly as recorded, not a description of it.
- Tests run by a sweep leave no build output (`PYTHONDONTWRITEBYTECODE=1` for Python); the
  only files left behind are under `docs/audits/` and in test folders.
- Verify-fix: the over-restriction line names the legitimate path by the code that walks it
  (`file:line` of the caller, view or spec).

The description is unchanged; held-out set 2 stays valid.

## v1.3.1 (2026-10-12)

Wording only; no change to what the skill does or checks.

### Changed
- One term per concept in the skill text, following Anthropic's skill authoring guidance: the
  run is a sweep, the zone is swept, the folder is `docs/audits/`, the coverage matrix column is
  "last run". "Audit" stays where it names the application's own audit log, and in the
  description's trigger phrases, which are the user's words.
- `references/report-and-registry.md`: one complete `findings.jsonl` entry as an example, with
  the report row and the two tests it corresponds to.

The description is unchanged, so the held-out trigger set written for it stays valid.

## v1.3.0 (2026-10-09)

Renamed, and the record became data a later sweep can re-verify.

### Changed
- The skill is now `verified-security-sweep` ("Verified Security Sweep"). Its output is a verified,
  recorded security review, not an audit in the formal sense; the name says what was measured.
  The description keeps every trigger phrase.

### Added
- `docs/audits/findings.jsonl`: one line per confirmed finding with its location, the exact code
  on that line, the reproduction command and an optional legitimate-path guard.
- `scripts/findings.py check`: each cited line must hold its quoted code, and the report and the
  index must agree. In the rounds, citations that exist but point at the wrong line were the
  remaining citation defect on both models.
- `scripts/findings.py recheck`: re-runs each open finding's reproduction and records open, fixed
  or inconclusive in `docs/audits/recheck-log.jsonl`; a sweep starts with it, so an earlier
  finding is shown fixed or still open instead of being re-read.
- `scripts/findings.py sarif`: the open findings as SARIF 2.1.0, at the current line when the
  snippet is found, with a fingerprint that survives line moves.

### Safeguards
- Entries record the commit they describe and are checked there, so they stay valid after the
  code changes; a commit missing from the clone is reported as not verifiable, not as wrong.
- `guard` is required: a deleted test or a broken setup reads as inconclusive, never as still open.
- Recorded commands that start a shell or pass inline code are refused; the skill lists the
  commands before running them and stops if they are not test-runner invocations.
- A snippet that looks like a key or token fails the check; the recheck log records whether the
  working tree had uncommitted changes; a second report of the same zone on the same day gets a
  suffix instead of overwriting the first.

## v1.2.3 (2026-10-09)

Fixes found by the graded round on v1.2.2 (`evals/results/round-v1.2.2.md`).

### Added
- `scripts/check_citations.py`: opens every `file:line` a report cites and prints the cited text;
  exits 1 on a file or line that does not exist, a shortened path that matches several files, or
  an approximate line. Standard library only, Python 3.9 or newer. Run before the report is final
  (checklist step 6). In the round, a model told to open every cited line still cited lines past
  the end of the file.

### Changed
- Reports cite paths from the repository root.
- "By design" is written as a refusal under claim correctness, with the code or document that
  shows the intent; a file checked with no candidate goes in Coverage, not among refused
  candidates. In the round, no run named a lens for those entries.

### Repository
- Round v1.2.2 graded for two models (`evals/results/round-v1.2.2.md`): criteria B1, B2, B4 pass;
  B3 fails on cited lines (one model), B5 fails on recall (one model, 0.89 against 1.00).
- Assertion 8b accepts any test case of the runner, not only `it(...)`.
- CI runs the new script's help, a Python 3.9 smoke run, and its tests.

## v1.2.2 (2026-10-09)

Fixes found by scoring the evaluation reports against a ground truth.

### Changed
- Every cited line is opened in its own file during verification, the evidence chain included;
  reviewers give line numbers as the file shows them, never offsets in a listing of several files.
  A line that does not exist or does not hold the cited code is corrected, or the claim fails
  claim correctness.
- The reproduction test is written at the lowest layer that runs with the project's own test
  runner, before an end-to-end tool that is not installed.
- Defects of another class or zone seen during a run get no verdict and do not count in the
  zone's yield; they go to the hand-off with `file:line`, as proposed sweeps of their zone.

### Repository
- Finding quality scored blind against a ground truth for the NodeGoat runs
  (`evals/results/quality-2026-10-nodegoat.md`); the procedure is in BUILD.md section 5.
- Assertion 2 of `evals/evals.json` requires every cited line to exist and hold the cited code.
- The hygiene check flags Romanian typed without diacritics.

## v1.2.1 (2026-10-09)

Fixes found by the per-model behavior evaluations.

### Changed
- Reports state the status of every piece of evidence: `ran, fails as expected`, `ran, passes`,
  or `written, not run: <reason>`, with the expected result per test case. A test that was not run
  is never presented as proof on its own; a finding with nothing observed is not `VERIFIED REAL`.
- Unconfirmed candidates carry one of three dispositions: refused with the lens that failed,
  needs deeper review with what is missing to decide, or closed earlier with the report cited.
- Delegation: on a single small zone the orchestrator may read the code itself, and says so in
  the report; verification, reproduction and the report never move to a reviewer.

### Repository
- Behavior evaluation per model (Opus 5.5, Sonnet 5.5, Haiku 4.5) in `evals/results/`; README table.
- Assertions 3 and 4 of `evals/evals.json` follow the two report rules above; the note on eval 4's
  language corrected. BUILD.md records the grading rules (strict reading, one grader model, invalid
  runs reported as invalid).

## v1.2.0 (2026-10-09)

### Changed
- Skill description rewritten for recall on smaller models: it names the request shapes that
  were missed (a pre-merge sanity check of changed files, "what did this fix break", "could this
  lock users out", "find bugs, no fixes, just a report", a staged diff to verify before commit)
  and tells the model to load the skill before searching the code. Measured per model on the
  tuning set and on a held-out set written after the description; results in `evals/results/`.

### Repository
- Trigger evaluation per model (Opus 5.5, Sonnet 5.5, Haiku 4.5) and a held-out trigger set
  (`evals/trigger-eval-holdout.json`), with procedure and incidents for every run.
- CI: pytest 9 (fixes the pytest tmpdir advisory, GHSA below 9.0.3); the suite runs on Python
  3.10 and 3.13, and a pytest-free job compiles and smoke-runs the two scripts under Python 3.9,
  so the skill's "3.9 or newer" statement stays tested. Dependabot keeps the SHA-pinned actions
  current, weekly, grouped.
- `public_hygiene_check.py`: shape-based gate for a public repository (addresses, IPs, hashes,
  hosts, non-English text, identifiers in prose, dates in the skill), with an allowlist that
  records every deliberate exception; runs in CI with the lint job; five tests.

## v1.1.0 (2026-10-08)

Result of a sweep run on this repository with the skill's own method (one fresh-context reviewer,
every finding verified on the cited lines). Twelve blocking findings, all fixed here.

### Fixed
- `sweep_status.py`: the candidates table was also read from a "Candidates verified and refused"
  heading when the candidates table was empty; zones matched report slugs on substrings
  (`auth` took its date from `oauth-callbacks`); a registry row with a declared date and no
  report was not a divergence; a filename with an invalid calendar date crashed the script.
- `fresh_code.py`: a repository with no commits produced a traceback instead of exit 2; the
  "mentioned by a test" flag matched substrings (`app` inside `application`); it is a whole-word
  match now.
- `leakage_check.py`: terms of three tokens could be hashed but never matched; outside a git
  repository the script crashed instead of exiting 2.
- `evals/fixtures/setup.sh`: `--help` dropped its last line; `--bare` on an existing planted
  clone silently kept the planted commit.

### Changed
- References: examples and yield figures rewritten so that none describes a specific product;
  the categories table carries generic examples; template prose moved out of the fenced block.
- `SKILL.md`: requirements line, run checklist, verification table columns named in full.
- References over 100 lines open with a contents line; script constants carry their rationale.
- Trigger set: four identifiers in the near-miss queries renamed; one evaluation prompt is
  declared as a deliberate non-English test.
- Tests: `tests/test_ci_scripts.py` covers the leakage check (including the positive path), the
  skill lint and the packaging script; six new tests reproduce the script defects above.
- Leakage list: four more hashed terms, path shapes for macOS and Windows.
- Documentation: `docs/BUILD.md` rewritten as criteria and decisions only; README, SECURITY.md
  and PRIVACY.md aligned (one voice, install paths, no references to disabled features).

## v1.0.0 (2026-10-07)

First public release.

- Skill `defensive-audit-sweep`: workflow, reviewer brief, verification lenses, verify-fix,
  report and registry formats, stack probes, two standard-library scripts
  (`sweep_status.py`, `fresh_code.py`).
- Plugin bundle for the Claude directory under `plugin/`, with listing icon, privacy policy,
  support and documentation links.
- Evaluation material: behavior evals on three pinned public repositories, 20-query trigger set,
  fixture setup with planted audit history and over-restrictive fix.
- CI: skill lint, em dash and leakage checks, `claude plugin validate --strict`, pytest on
  Python 3.9 and 3.13, reproducible `.skill` packaging, release job on `v*` tags.
