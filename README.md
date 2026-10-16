# Verified Security Sweep

[![CI](https://github.com/SecPlusDev/verified-security-sweep/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/SecPlusDev/verified-security-sweep/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/SecPlusDev/verified-security-sweep?display_name=tag&color=2563eb)](https://github.com/SecPlusDev/verified-security-sweep/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-16a34a)](LICENSE)
[![Python 3.9+](https://img.shields.io/badge/python-3.9%2B-3776ab?logo=python&logoColor=white)](plugin/skills/verified-security-sweep/scripts/)
[![Dependencies: none](https://img.shields.io/badge/dependencies-none-6b7280)](plugin/skills/verified-security-sweep/scripts/)
[![Claude skill](https://img.shields.io/badge/Claude-skill-d97706)](plugin/skills/verified-security-sweep/SKILL.md)
[![Security policy](https://img.shields.io/badge/security-policy-dc2626)](SECURITY.md)

<!-- The release badge is served by shields.io and renders only while the repository is public.
     The CI badge is served by GitHub and renders for anyone who can see the repository. -->

**A Claude skill for security reviews you can verify, hand over and resume: one zone at a time,
every confirmed finding located on its exact line and reproduced by a failing test, every run
recorded so the next one re-checks the last instead of starting from zero.**

Claude finds the defects; the skill makes each finding checkable, keeps the record, and gives
the next review a starting point. It complements an audit and the project's own tests. The
skill reports, reproduces and proposes; the fixes go through your normal change process.

Listed in the Claude directory: `claude plugin install verified-security-sweep@anthropic-plugin-directory`.

## What it adds to Claude, measured

Same prompt, same code (a Django service with three planted access-control defects), same model
(Opus), once without the skill and once with it. Both runs found all three defects, and both
wrote and ran reproduction tests. The difference is in what a reader can check and what the next
review starts from:

| | Without the skill | With the skill |
|---|---|---|
| Planted defects found | 3 of 3 | 3 of 3 |
| Findings with an exact `file:line` | 0 of 3 (file and function only) | 3 of 3 |
| Citations a reader can check mechanically | 0 | 69, all resolve |
| Candidates examined and dismissed | 5 notes, no lines | 11, each with the lens that failed and the line |
| Where the record goes | `docs/security/`, one file | `docs/audits/`: dated report, registry, categories |
| What the next review starts from | a one-row status log | a registry: zones, last run, yield, three proposed next sweeps |

Both documents are in [`docs/showcase/`](docs/showcase/), unchanged, and every number above is
tied to a line in [`COMPARISON.md`](docs/showcase/COMPARISON.md).

Across the evaluation rounds ([`evals/results/`](evals/results/)):
- **Method, with and without the skill** (round v1.2.2, the one with baselines, same prompts,
  same code, same model): Opus met 86% of the graded checks with the skill and 24% without;
  Sonnet 74% and 16%. The current version, measured on 2026-10-13 against the assertions as
  they are now, which include the findings index, continuity and the poisoned index: Opus 23 of
  27 (85%), Sonnet 21 of 27 (78%). The misses are listed below.
- **No false findings:** every confirmed finding, on both models, in every round, was real when
  graded blind against the code (16 of 16 Opus runs, 14 of 14 Sonnet runs clean).
- **No code changes:** no run changed application code (26 of 26 Opus runs, 18 of 18 Sonnet
  runs); everything else is a proposal in the report.
- **Detection:** the same as Claude without the skill, on both a well-known vulnerable app and
  planted defects no model could know (Opus 3 of 3 planted defects in every run; Sonnet 3 of 3
  in 5 of 7 runs, the same as without the skill).
- **Continuity:** with an earlier review and a fix in the history, both models listed the
  recorded reproduction commands before running them, recorded the fixed finding as fixed and
  the open ones as open, and cited them instead of re-reporting them. With one recorded command
  replaced by a script that is not the test runner, neither model ran it; both showed the
  command to the user.
- **Install:** installed through `--plugin-dir` on a clean copy, the skill loaded on the first
  tool call and the full run passed every check from the installed copy
  (`evals/results/install-2026-10-13.md`). Installed from the Claude directory after the
  listing, the copy matched the v1.4.0 release file for file and by archive digest, and a run on
  it passed 9 of 9 checks with the three planted defects on their lines
  (`evals/results/install-directory-2026-10-16.md`).
- **Real code, once:** one run on a parked personal project that is not a fixture, reviewed
  with `evals/real-code-rubric.md` by its author, who is also this skill's author: 2 confirmed
  findings, both judged real, 9 dismissed candidates all with sound reasons, report accepted
  as is, 13 minutes against an estimate of days by hand
  (`evals/results/real-code-2026-10-16.md`). One data point from a non-independent reviewer;
  read it as such.

What the current version still misses, so you know what to read with care:
- **Leads the reviewer raises but the sweep does not verify.** Both models record them with
  their `file:line` in the refused-candidates section, which `check_report.py` enforces, but
  often label them "out of zone" when the file is in the zone, instead of giving them a
  verdict. Read an "out of zone" entry as unverified. Opus misses 1 of 9 checks
  on each sweep prompt for this; Sonnet the same plus, on one prompt, a reproduction run with a
  runner that is not the project's.
- **Line precision.** One Opus citation in the last round pointed into a block of commented-out
  code; `check_citations.py` prints the cited text so a reader catches it, but the script
  cannot tell a comment from code.
- **Sonnet re-verdicts.** On the recheck prompt Sonnet gave new verdicts to findings that the
  earlier report had already confirmed, where Opus cited them; the recheck log is right in both.

Use it on Opus or Sonnet. On Haiku the description rarely loads the skill, and when it was
loaded the model did not follow it reliably; it is not recommended there. On Sonnet, written
rules are followed less reliably than on Opus, which is why the skill's checks are scripts.

**Does it load when it should?** Precision / recall of the skill's description, 20 queries,
three runs each, per model of the session, on the current name and description
(`evals/results/trigger-2026-10-v1.3.1.md`; the Haiku column is from the earlier description,
`evals/results/trigger-2026-10-desc-v2.md`):

| Query set | Opus 5.5 | Sonnet 5.5 | Haiku 4.5 |
|---|---|---|---|
| Tuning set (`evals/trigger-eval.json`) | 1.00 / 1.00 | 1.00 / 1.00 | 0.75 / 0.10 |
| Held-out set, written after the description | 1.00 / 1.00 | 1.00 / 1.00 | not measured |

The same loop with a popular skill collection installed next to it (`addyosmani/agent-skills`,
which has its own security hardening skill and security auditor subagent) gives the same figures
on both models: every request for a recheck of earlier findings or for verifying a staged fix
loads this skill in 3 of 3 runs, and no request for a security review went to the collection.
On Opus the collection did load for its own kind of request, so it was a real competitor; on
Sonnet it did not load even for that, so the Sonnet result only shows that this skill does not
lose.

## Where it fits

| You want | Use |
|---|---|
| A one-time security pass on your branch | `/security-review` |
| A deep multi-agent scan with verified findings and suggested patches | the Claude Security plugin |
| A security review you can hand over and resume: exact lines, reproduction tests, dismissed candidates with reasons, a registry of what was reviewed when, a re-check of earlier findings, and a check that a fix does not break legitimate paths | this skill |

They are not alternatives. A scan tells you what may be wrong today; this skill keeps the
verified record across reviews.

## Why this exists

Three things go wrong with security reviews in practice. A false positive gets fixed and the
fix breaks a legitimate path. A report with twenty "critical" items and three real ones trains
the team to skip the next report. A review done every quarter by someone new finds the same
closed issues again. The skill comes from thirty sweeps on one production multi-tenant SaaS over
five months, where each of the three was observed, and it keeps the practices that stopped them:
verification on the cited lines, a reproduction test per finding, and a record the next review
reads first.

## How it works

1. **Pick a zone.** One bounded area (a feature, a set of routes, fresh code), not "everything".
   Fresh code has the highest yield of any zone, every time it has been measured.
2. **Pre-read and re-check.** The project's rules file, the categories and every previous
   report, so closed items are not reported again; the reproduction of every open finding is run
   again, so a fixed one is recorded as fixed.
3. **Delegate the reading.** One read-only reviewer per zone, in a fresh context, with a strict
   brief: severity calibration, an evidence chain of three per finding, explicit disqualifications.
4. **Verify every candidate.** Each claim is checked against the cited lines through three lenses:
   exploitability, claim correctness, existing mitigation. Default is to refuse.
5. **Reproduce.** Every confirmed finding gets a test that fails on the current code. Races get an
   interleaving test; documents (PDF, CSV, email) are generated and inspected.
6. **Record and hand off.** A dated report, a registry row with the yield and one index line per
   confirmed finding; every cited line is checked by script. Fixes and other changes are written
   as proposals for the team's normal change process.

The same skill verifies a staged fix before commit ("what did this fix break?") and returns
`CLEAN`, `RISK` or `BROKEN`, with a guard test that asserts both the blocked attack path and the
intact legitimate path. Over-restriction, closing the hole and the legitimate path together, is
the most common way a fix does harm, and the one almost nobody tests.

## What you get after a run

- **A report** at `docs/audits/YYYY-MM-DD-<zone>.md`: context, delegation, a verification table
  (claimed severity, verified severity, reservations, proof), confirmed defects with a single-line
  location and a three-part evidence chain, refused candidates with the lens that failed,
  coverage and hand-off.
- **A registry** at `docs/audits/sweep-registry.md`: zones, last run date (derived from report
  filenames by `scripts/sweep_status.py`, so it cannot drift) and yield.
- **A reproduction test per confirmed finding**, in the project's own test folders, plus a
  proposed guard where the defect class can recur.
- **A findings index** at `docs/audits/findings.jsonl`: location, the exact code on that line,
  the reproduction command. `scripts/findings.py recheck` re-runs those commands later and records
  in `docs/audits/recheck-log.jsonl` which findings are fixed; `scripts/findings.py sarif` writes the
  open ones as SARIF for a code scanning view.

A real report from the evaluation runs, with its registry and reproduction tests:
[`docs/showcase/with-skill/`](docs/showcase/with-skill/).

## Try it in ten minutes

```bash
git clone https://github.com/SecPlusDev/verified-security-sweep && cd verified-security-sweep
evals/fixtures/setup.sh --defects healthchecks
cp -a evals/fixtures/healthchecks /tmp/hc && cd /tmp/hc
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
claude
```

With the skill installed, ask for a security check of the API-key protected API under `hc/api`.
Then compare the report with the three planted defects listed in
`evals/ground-truth/healthchecks-api-planted.md`; read that file after the run, not before.

## Install

**From the Claude directory.** The plugin is listed for Claude Code, Cowork and the Claude apps.
In Claude Code:

```bash
claude plugin install verified-security-sweep@anthropic-plugin-directory
```

or `/plugin`, Discover, "Verified Security Sweep". The directory installs the tagged commit of
the listed version, not this repository's `main`; the installed copy of v1.4.0 was compared with
the release file by file and by archive digest
(`evals/results/install-directory-2026-10-16.md`).

**From a release, for the Claude apps.** Download `verified-security-sweep.skill` from the
[latest release](https://github.com/SecPlusDev/verified-security-sweep/releases/latest) and upload it as a
skill. Compare the file's SHA-256 with the digest shown on the release page; the archive is
rebuilt from the tagged commit, so the two must match.

**From the repository, for Claude Code.** The skill lives in the plugin folder, `plugin/`:

```bash
cp -r plugin/skills/verified-security-sweep ~/.claude/skills/
```

Use `.claude/skills/` in a project instead of `~/.claude/skills/` to make it available in that
project only. The scripts need Python 3.9 or newer and nothing else.

Install one copy only. A copy synced in your account and a copy in the repository have the same
name and description; Claude picks one of them at trigger time, and you cannot tell which version
ran.

## Usage

Ask in your own words. Requests like these trigger the skill:

- "we're launching the billing module next tuesday, it's an express app with postgres under
  services/billing. can you do a proper security pass on it before we ship?"
- "I patched the double-submit race on /api/invites/accept (see git diff --cached). before
  I commit, what did this fix break?"
- "review this PR please, it touches the session middleware and the org switch endpoint"

Requests like these do not, by design:

- "add rate limiting to the login endpoint, 10 per 15 minutes per IP" (implementation, not review)
- "review this PR, it's the new dark mode toggle and some tailwind cleanup in the settings page"
  (no security-relevant surface)

Five helper scripts ship with the skill and run on their own:

```bash
S=plugin/skills/verified-security-sweep/scripts
python3 $S/fresh_code.py --days 3          # recently changed files ranked by churn, flagged when no test mentions them
python3 $S/sweep_status.py --check          # registry rows vs report filenames; exit 1 on divergence, for CI
python3 $S/check_citations.py docs/audits/2026-01-15-money.md   # every cited file:line opened; exit 1 on a line that does not exist
python3 $S/check_report.py docs/audits/2026-01-15-money.md      # sections, verdicts, dispositions; exit 1 on a lead of the zone left in the hand-off
python3 $S/findings.py check                # findings index: each cited line holds the quoted code
python3 $S/findings.py recheck --run --write   # re-run each open finding's reproduction: open, fixed or inconclusive
python3 $S/findings.py sarif > findings.sarif  # open findings as SARIF 2.1.0
```

## Cost and limits

- **Reviewers follow zones.** One reviewer per zone, never more than four at once. A single-zone
  sweep on the evaluation fixtures used roughly 100k tokens and 4 to 11 minutes.
- **Reproduction may start the application and its database.** The skill starts them under
  run-specific names or ports and stops only what it started, by PID or container name.
- **Evaluation runs:** at most four at once. Each run with the skill spawns its own reviewers;
  eight parallel runs have already exhausted a session limit.
- **Session limits.** A run interrupted by a usage limit is not a result. Do not grade a
  half-written report: discard that run's output and start it again once the limit resets. Check
  for stray dev servers or containers left by the interrupted run.
- **No sandbox of its own.** The skill runs with the permissions of the session that loads it;
  see [`SECURITY.md`](SECURITY.md).
- **Any language with a test runner.** The method and the scripts do not depend on the language:
  the reproduction is whatever the project's own runner executes (`pytest`, `npx jest`, `go
  test`, `cargo test`, `mvn test`, `dotnet test`, `rspec`, `php artisan test`). Quick probes
  ship for Node, Python, Ruby, Go, Java, C#, Rust, PHP, infrastructure and frontend; for any
  other stack the skill derives them from the project's rules file. It was evaluated on Node,
  Python and Ruby fixtures only. A project with no automated tests gets reports whose
  reproductions are marked `written, not run`, with the reason.

## Evaluation

The behavior figures come from seven prompts on three public repositories pinned to a commit
(an Express app, a Rails app and a Django service): planted review history, a planted
over-restrictive fix for the verify-fix prompt, a fixture with three planted defects whose list
was committed before any run, and two later states of it (an earlier review followed by a fix,
and the same with one recorded command replaced by someone else). Runs are graded against the
assertions of `docs/BUILD.md`, section 3, and their findings are scored blind against the code
(section 5). The trigger figures come from two sets of 20 queries (10 that should trigger, 10
near misses), three runs each: the tuning set the description was written against, and a
held-out set written afterwards and never used to change it; the loop also runs with another
skill collection installed next to the skill (criterion B7). Changes that a round rejected are
listed in `docs/BUILD.md`, section 8.

To run them:

```bash
evals/fixtures/setup.sh                        # clone the fixtures at their pinned commits
evals/fixtures/setup.sh --bare                 # fixtures without audit history (bootstrap case)
evals/fixtures/setup.sh --verify-fix nodegoat  # stage the planted fix for the verify-fix prompt
evals/fixtures/setup.sh --defects healthchecks # one commit, three planted defects (eval 5)
```

Prompts and assertions are in `evals/evals.json`, the trigger sets in `evals/trigger-eval.json`
and `evals/trigger-eval-holdout-2.json`, the results in `evals/results/`. The plugin was also
installed and run the way a user gets it, through `--plugin-dir` on a clean copy of the
planted-defects fixture (`evals/install-test.md`, result in `evals/results/install-2026-10-13.md`):
the skill loaded on the first tool call, the three planted defects came back on their lines with
failing tests, and every script passed from the installed copy. After the listing, the same
check ran on the copy the directory installs (`evals/results/install-directory-2026-10-16.md`).
Run trigger evaluations only from an empty project directory, with a Claude config directory that
denies `Bash`, `Write` and `Edit`, from an account where this skill is not installed or synced,
with one worker at a time, and with nested sessions started without any MCP server of the
account. Otherwise nested sessions explore the surrounding directories, the installed copy wins
over the test copy, and connectors such as mail or documents are within reach of the test. The full procedure and the harness fixes it needs are
in [`docs/BUILD.md`](docs/BUILD.md), section 5.

## Repository layout

```
plugin/                     the plugin folder, the only part users install
  .claude-plugin/plugin.json    plugin manifest
  README.md                     listing description: what the plugin runs and reads
  LICENSE                       copy of the repository license
  skills/verified-security-sweep/
    SKILL.md                    the skill: workflow, brief, report rules
    references/                 zones and yield, verification lenses, verify-fix, stack probes, report and registry formats
    scripts/                    sweep_status.py, fresh_code.py, check_citations.py, findings.py; standard library only
tests/                      pytest for the skill scripts and the CI scripts, on synthetic fixtures
evals/                      prompts, assertions, trigger set, fixture setup and planted patches
docs/                       build criteria and decisions (BUILD.md), example report, showcase
.github/                    CI, lint, leakage and hygiene checks, packaging script, pattern and allow lists
```

## Contributing

Changes go through a pull request against `main`. Five checks must pass before merge: the lint
job (frontmatter, line limits, em dash check, the Claude directory's plugin folder checks,
`claude plugin validate`, leakage check, public hygiene check), pytest on Python 3.10 and 3.13,
the Python 3.9 compatibility job, and the packaging job. The leakage check reads generic shapes from `.github/leakage-patterns.txt` and
a private term list that is not in the repository (a fork's pull request runs the shapes only);
it has no file exceptions: if it flags your change, change the text; the list stays as it is. The hygiene check flags shapes that need a deliberate decision in a public repository
(addresses, hashes, hosts, identifiers in prose, non-English text); if it flags your change,
either remove the value or add it to `.github/hygiene-allowlist.txt` with a comment saying why.
Run the same gates locally:

```bash
python3 .github/scripts/check_skill.py plugin/skills/verified-security-sweep --markdown-root . --plugin-root plugin --max-lines 500
claude plugin validate ./plugin --strict
.github/scripts/leakage_grep.sh
python3 .github/scripts/public_hygiene_check.py
python3 -m pytest tests/ -q
```

Security issues go through the process in [`SECURITY.md`](SECURITY.md), never through a public
pull request. The repository has no issue tracker: questions, bug reports and feedback come as a
pull request (a change, or a note added under `docs/`), or by email to the address in
[`SECURITY.md`](SECURITY.md).

## License

MIT, see [`LICENSE`](LICENSE); copyright 2026 SecPlusDev. If you build on this skill, keep the
copyright notice and the license text with your copy.
