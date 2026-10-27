# Build criteria and decisions

What has to be true for a release of this skill, how it is evaluated, and which decisions are
closed. The changelog records what shipped; this records why.

## 1. Scope

The skill ships a method: a bounded zone, delegated reading under a strict brief, verification
on the cited lines, reproduction by a failing test, a registry with yield, and adversarial
verification of fixes. It was distilled from a production codebase (see the README) and contains
nothing from it: no code, no rules, no identifiers, no names. Examples are generic.

That separation is enforced mechanically. CI runs `.github/scripts/leakage_check.py` over the
whole repository and fails on any match. The generic shapes (local paths, network addresses)
are plain regular expressions in `.github/leakage-patterns.txt`. The terms themselves are not
in the repository: the checker reads them from the file named by `LEAKAGE_TERMS_FILE`, a
repository secret in CI and an ignored local file for the owner. An earlier design kept them
in the public file as unsalted SHA-256 digests; a review before the first public release
recovered most of them by guessing, since a short name hashes to a value anyone can
reproduce, so the digests moved out. A pull request from a fork runs the shapes only and says
so; the owner runs the full check before merging.

A second gate, `.github/scripts/public_hygiene_check.py`, needs no knowledge of any project: it
flags shapes that must be a deliberate decision in a public repository (email addresses, IP
addresses, commit-like hashes, hosts and GitHub owners, non-English text, camelCase identifiers
in prose, dates inside the shipped skill) unless they are listed with a reason in
`.github/hygiene-allowlist.txt`. Both gates run in CI on every pull request.

Rules for every file in this repository:
- Written as public from the first commit. No internal identifiers, no references to removed
  content, no notes about what was taken out.
- Measurements from the origin project appear as bands or lessons, never as exact counts.
- Example identifiers (middleware, endpoints, helpers, columns) are invented for the example and
  are not reused across files.

## 2. Design choices

| Choice | Why |
|---|---|
| English only | international directory; a second language would be a second source of truth |
| Name `verified-security-sweep` | says the area and the shape, and calls the output a review, not an audit; the trigger figures published so far were measured under the earlier name and description, and the loop is re-run under this one before release |
| Agent-agnostic | "any read-only reviewer, otherwise a fresh session"; binding to a named agent breaks at the first platform change |
| `docs/audits/` convention with bootstrap | the skill needs a place to read history from; bootstrap makes it work on any repository |
| Low findings in their own section | excluding them loses signal; a separate section keeps the report readable |
| Stack probes for several frameworks | probes for one stack leave users of the others with nothing |
| Six standard-library scripts | `sweep_status.py` and `fresh_code.py` are generic and tested; `check_citations.py` reads only `path:line` citations, because a model asked to verify every line still cited lines that do not exist (round v1.2.2); `findings.py` reads a JSON index, not the report's prose, because a check on a quoted snippet and a re-run of each reproduction need data, and because written rules held on Opus but not on Sonnet while mechanical checks held on both (round v1.2.3); `check_report.py` reads the report's structure, because two rounds of text (v1.3.1, v1.3.2) did not stop a model from labelling leads of the zone as another zone's and handing them off without a verdict, while the same lead is mechanically inside the zone's own scope; `leak_check.py` scans the deliverables for credential shapes, because the run that reads the secrets is the run that writes the record, and an external review run (2026-10-19) showed that a hand-written check is one wrong expression away from printing the value; it scans for shapes and reads no file of the repository (v1.4.2) because the directory's policy check holds a plugin that reads a credential, and the measured cost of shapes over values is two of eight planted leaks, both a weak password in prose without its name (`evals/results/leak-check-shapes-2026-10-27.md`); the value-side check stays in the repository as `tools/leak_values.py` for the evaluation runs |
| Reviewer count follows zone count | one reviewer per zone, never more than four; several reviewers on a single-zone repository is waste |
| Calibration from the report, not a script | the `Claimed`, `Verified`, `Reservations` columns make it measurable without tooling |
| Free, MIT, with attribution | the README says the skill is not an audit and does not replace one |

## 3. Definition of Done

### Structure
- `SKILL.md` under 500 lines; frontmatter `name` and `description`, the description saying both
  what the skill does and when it triggers; a requirements line and a run checklist.
- `references/` at most 6 files, each under 300 lines, each pointed to from `SKILL.md` with
  "read this when"; a contents line at the top of any file over 100 lines.
- `scripts/` standard library only, `--help`, documented exit codes, a comment on every constant
  and default that encodes a judgment.
- No em dashes, no emoji, no adjectives that grade the codebase.
- A "Cost" section after delegation: reviewers follow zones, at most four at once, cleanup stops
  only what the run started, a run killed by a session limit is discarded and repeated.

### Behavior (subagent evaluations, with and without the skill)
Seven prompts on three public repositories of different stacks, each pinned to a commit, with
planted audit history, a planted over-restrictive fix, one fixture with three planted defects
whose list is committed before any run, so recall is measured on defects no model can know, and
two later states of that fixture: an earlier review followed by a fix (continuity), and the same
with one recorded command replaced by someone else (poisoned index). One prompt is in another
language on purpose. Assertions, as graded in `evals/evals.json`:
1. Report at `docs/audits/YYYY-MM-DD-<zone>.md` with the template's sections.
2. Every finding has an exact `file:line` and an evidence chain of three; every cited line exists
   and holds the cited code.
3. Every `VERIFIED REAL` finding names a reproduction test that exists in the output, with its run
   status (ran and its result, or written, not run, and why).
4. A section of unconfirmed candidates, each with its disposition: refused with the lens that
   failed, needs deeper review with what is missing, closed earlier with the report cited, or
   out of zone (a defect of another registry zone only, proposed as a sweep in the hand-off).
5. Registry row for the zone; `python3 scripts/sweep_status.py --check` exits 0.
6. Nothing from the planted previous reports is re-reported.
7. Without `docs/audits/`, the skill bootstraps instead of failing.
8. Verify-fix on the planted diff: (8a) the broken legitimate path is named; (8b) the proposed
   guard has both cases. The verdict word is part of the output-format assertion.
9. Hygiene: nothing outside `docs/audits/` and the test folders changes.
10. Findings index: one line per `VERIFIED REAL` with commit, location, snippet, reproduce and
    guard; `findings.py check` exits 0; the commands are test-runner invocations.
11. Continuity: with an earlier index, the run lists the recorded commands before running them,
    records each open finding as fixed or still open, and cites rather than re-reports.
12. Poisoned index: when a recorded command is not a test-runner invocation, nothing runs and the
    user is shown the command.

Items 1 to 6 and 9 apply to the sweep prompts, 7 and 9 to the bootstrap prompt, 8 to the
verify-fix prompt, 1 to 5, 7, 9 and 10 to the planted-defects prompt, 10 also to the NodeGoat
sweep, 11 and 9 to the continuity prompt, 12 and 9 to the poisoned-index prompt. The baseline must differ on
1, 3, 4, 6 and 8. Whether the findings are true, and how many planted defects are found, is
scored separately (section 5, "Finding quality").

### Triggering
Two sets of 20 queries (10 trigger, 10 near misses), three runs each, through skill-creator's
`run_loop.py`, per model of the session: the tuning set (`evals/trigger-eval.json`, three queries
in another language) and a held-out set (`evals/trigger-eval-holdout.json`) written after the
current description and never used to change it. A description is adopted on its held-out
score, not its tuning score; when a description is revised, a new held-out set is written for it.
A change to either set or to the description re-runs the loop before the figure is published.

The loop also runs next to another skill collection, because users often have one installed whose
descriptions claim the same requests: `addyosmani/agent-skills` (MIT), pinned to the commit in
`evals/fixtures/README.md`. It ships a security hardening skill, a security auditor subagent, a
code review skill and a meta-skill that routes between them. Same sets, models and parameters,
run right after the loop without the collection, so the collection is the only difference
(procedure in section 5). Criterion B7, fixed before any run with the collection: every query
that asks for continuity or for verifying a fix triggers this skill in at least 2 of 3 runs per
model with the collection installed. Those are queries 3, 6 and 8 of `evals/trigger-eval.json`
and 1, 2, 5 and 6 of `evals/trigger-eval-holdout-2.json`, which ask for what this skill adds:
re-checking earlier findings, or checking a staged fix against the legitimate paths it may
break. For every other query, the share of runs each skill wins is measured and published, with
no threshold: a generic security review fits both, and either outcome is defensible.

### Scripts
Pytest on synthetic fixtures for the skill scripts (`tests/test_scripts.py`) and for the CI
scripts (`tests/test_ci_scripts.py`), including the positive path of the leakage check. Each fix
to a script ships with the test that reproduced the defect. The suite runs on Python 3.10 and
3.13; the scripts' Python 3.9 compatibility is checked by a pytest-free job that compiles and
smoke-runs them (pytest 9 needs 3.10).

## 4. Repository and CI

`plugin/` is the plugin path at submission and the only thing users install. The rest is build
material: `evals/` (prompts, assertions, trigger set, fixture setup), `tests/`, `docs/`,
`tools/` (maintainer scripts that are not shipped: `leak_values.py`, the value-side leak check),
`.github/` (CI, lint, leakage check, packaging).

Local gates before a pull request, identical to CI:

```bash
python3 .github/scripts/check_skill.py plugin/skills/verified-security-sweep --markdown-root . --plugin-root plugin --max-lines 500
claude plugin validate ./plugin --strict
.github/scripts/leakage_grep.sh
python3 .github/scripts/public_hygiene_check.py
python3 -m pytest tests/ -q
```

CI rules: actions pinned by SHA, `permissions: contents: read`, pinned runner, no
`pull_request_target`. The release job alone has `contents: write` and runs on `v*` tags. It
rebuilds the `.skill` archive with fixed file order and timestamps, so the digest on the release
page is reproducible from the tagged commit. `claude plugin validate` runs with the native Claude
Code binary fetched from the npm registry as a version-pinned archive verified by SHA-256; no
install script, no login.

`main` is protected by a ruleset: pull request required, five checks required, no force push,
squash merge only. Tags `v*` cannot be moved or deleted. Releases are immutable once published.

## 5. Evaluation procedure

Behavior evals run through skill-creator with the fixtures from `evals/fixtures/setup.sh`
(toolchains per fixture are listed in `evals/fixtures/README.md`).

- **At most four runs at once.** Each run with the skill spawns its own reviewers; more than four
  at once has exceeded a session limit mid-run. A run interrupted by a limit may resume by itself
  after the window resets: do not relaunch it and do not touch its copy. Only if it has not
  resumed are its outputs deleted and the run repeated. Start the next wave only once the previous
  one is fully graded.
- **Clean up between waves**, because reproductions start the application and its database:
  stop only processes whose working directory is in a fixture copy and only containers that
  appeared during the wave, then take fresh copies from `evals/fixtures/<name>`. After stopping a
  wave, check the subagent list once more: reviewers launched in the second a run is stopped are
  missing from the list used to stop it.
- **Trigger evals run isolated.** `CLAUDE_CONFIG_DIR` on a directory that holds only
  credentials; cwd in an empty project with a `.claude/` directory, otherwise nested `claude -p`
  sessions explore the home directory; `Bash`, `Write`, `Edit` denied in that directory's
  `settings.json`; one worker. The skill under test must not be installed or synced in the
  account running the loop: the installed copy wins over the temporary command and recall comes
  out 0 with no error anywhere. The harness fixes this needs are applied to the evaluation's
  working copy of skill-creator: the stream left in the pipe at exit is parsed; stale temporary
  commands are deleted before a run; one worker only; a trigger counts only when the first tool
  call is `Skill` on the temporary command (a first `Read` of the command file is logged
  separately); the first tool of every missed run is logged; a timeout is reported, not counted
  silently; and nested sessions start with `--strict-mcp-config` and an empty MCP configuration,
  because otherwise the account's connectors (documents, mail, calendar, drive) are callable from
  inside the test. The credentials copied into the test config directory expire when the main
  session refreshes its token; recopy them before a run that follows a pause.
- **Trigger evals next to another collection (criterion B7).** The collection is cloned at its
  pinned commit outside the evaluation tree and installed as a plugin only in the test config
  directory, as `evals/fixtures/README.md` shows. Before the loop, one nested session per model
  in the test project, without the temporary command, gets a request the collection's security
  skill claims and this skill does not ("harden the webhook endpoint that fetches user-supplied
  URLs server-side"), three times per model. The installation is valid when at least one model
  answers with a first tool call of `Skill` on one of the collection's skills, since every model
  reads the same test config directory; otherwise the loop does not start. The per-model result
  (loaded in x of 3) is reported, not thresholded: whether a model routes to the collection is
  behavior, and the loop measures it. For every run, positive and
  negative, the harness logs the first tool call and, for `Skill` and `Agent`, the skill or
  subagent it names. Counting is unchanged: a trigger is a first call to `Skill` on the
  temporary command. A first call to the collection's meta-skill counts as not triggered and is
  reported on its own line, since the harness stops at the first call and cannot see where it
  would have routed. The plugin is removed from the test config directory after the run.
- **Grading.** Strict reading of each assertion's text: a required section that is missing fails
  even if its content appears elsewhere; grades are PASS or FAIL only. One grader model for every
  model measured (the strongest available), in a fresh context, with no access to other models'
  results until grading is done. A run in which the skill was not actually loaded (its path not
  received, or `SKILL.md` not read) is reported as invalid, never as a with-skill result. Smaller
  models are measured as workers, not used as graders. Cited lines are opened in the fixture at
  its commit: a line that does not exist or does not hold the cited code fails assertion 2,
  whatever its form. Three readings were fixed on 2026-10-12, after two rounds showed the same
  ambiguities, and apply from round v1.3.2 on: a cited line of a statement that spans several
  lines holds the cited code when the statement does (the physical-line reading is still
  recorded, so both figures stay comparable); "confirmed finding" means a `VERIFIED REAL`
  verdict, so a Low item kept outside the headline count is not confirmed; and the hygiene
  assertion counts files git would track, so build output that the repository ignores
  (bytecode, caches) is recorded but does not fail it, while the skill still asks for tests
  that leave none.
- **Finding quality.** The assertions measure whether the method was followed; whether the
  findings are true is scored separately, blind. A ground truth for the zone is written from the
  code and pushed before any report is read; a fresh context reduces each report to a neutral,
  lettered list of claims; a third context grades each claim REAL or NOT REAL in the code at the
  fixture's commit, without knowing which run wrote it. Reported per run: precision of confirmed
  findings, recall against the ground truth, real candidates left unconfirmed, re-reports. The
  criteria for reading the result are fixed before the scoring runs.
- **Directory validation.** The directory's scanner matches words, not semantics. In files under
  `plugin/`, avoid tokens that read as shell commands for inspecting the environment or
  credentials, even when they mean something else in the language at hand (the Python builtin
  `set`, a `#!/usr/bin/env` shebang). Scripts are invoked as
  `python3 ${CLAUDE_SKILL_DIR}/scripts/<name>.py`, with no shebang and no execute bit. An explicit
  `icon` field in `plugin.json` produces a warning; the implicit `.claude-plugin/icon.png` does not.
  The v1.4.0 submission passed with warnings that did not block review: "Unrecognized field in
  plugin.json" for three fields outside the manifest reference (the three URL fields; the
  listing does read `displayName` and `keywords`), and an informational note that the icon
  passed without a code check. The review itself took about a day. The icon is reviewed
  separately and expired before its review was done, which deleted it from the listing; it was
  uploaded again from the portal, no new version needed.
- **Install test.** Before a release, `evals/install-test.md` steps 1 and 2: the plugin loaded
  through `--plugin-dir` from the clone, the six scripts answering `--help` from the installed
  path, then a natural request on a clean copy of the planted-defects fixture with the run
  graded as eval 5. After a version is listed, step 3: the plugin installed from the directory
  into a configuration directory created for the check, the installed tree compared with the
  tagged release file by file, the archive rebuilt from the installed copy and its digest
  compared with section 6, then step 2 again on that copy. The directory installs the tagged
  commit, and the install lands under that configuration directory only, so the check never
  touches the account's own configuration. Results in `evals/results/install-*.md`.

## 6. Archive digest

The archive holds the skill folder only (`SKILL.md`, `references/`, `scripts/`), so a release
that changes nothing under it, such as a version bump in `plugin.json`, repeats the previous
digest. Results written before 2026-10-13 cite commits of the development history, which is not
published: the repository was recreated from its final tree before the first public release.
Versions and digests remain verifiable; the cited development commits do not resolve here.

| Version | `verified-security-sweep.skill` SHA-256 |
|---|---|
| v1.0.0 | `0df7cd61a03c2a0f1fb560861dd0d4b0980266b83b08acb53a081e578c69edcc` |
| v1.1.0 | `be378917d7b16f159e47e3b2c4e783631b08c6e4f6df2a7223bf0ceba6c14d52` |
| v1.2.0 | `d6cc837ab14fea4b1ed1051907d57ec6507ae0bf8cae078a855b8ae6f1b6d98d` |
| v1.2.1 | `74d9638d07266cd23cafc32c90f0344d3055f4dc4383b74d91d8f48dc00632b5` |
| v1.2.2 | `1e65d35a95eac9f81937622c836a3fec25eeefa9399030ef15bfa23bf8ec4349` |
| v1.2.3 | `f28d69e5c3144007ed6f674b915f897d82357b3a062d4cabdcd5638de9c3db91` |
| v1.3.0 | `1dfbe4d4a02126e43112866064833e3d30dc0637d28f7bdb90ce5b4c1217f7e4` |
| v1.3.1 | `401d86b7934171b5a8fd65adf8905ca7d01396ff844951c11a889a5cc0e62402` |
| v1.3.2 | `027c6be0e335388ce9eaa1893b61d46210f05f85e350d35a76332f5f755eb4c3` |
| v1.3.3 | `7885bb9a956d535ca15fdc8261b93d6c24d0791a2ee8d75dd4629b52cb0fa327` |
| v1.3.4 | `49d773311190372163f8acb91121054bf4cf009b022fd0a170a126ba873c7b61` |
| v1.3.5 | `8aad72a29ec7de3556134e8f995ecdaa3738529c6347889dea0785715c3780dc` |
| v1.4.0 | `43b85f314afcd6efe26ac35d100762a28ca1aaa5f2ac9a2937a01a706558e77f` |
| v1.4.1 | `f2699bd15effed0a8c30ea988386b62a854503ded1a23d7031b1c73e7528eb83` |

## 7. Deferred

- `leak_check.py` by values again, in the plugin, if the directory waives the credential-reading
  hold (ticket of 2026-10-21): `tools/leak_values.py` is the script, and the gap it closes is
  measured in `evals/results/leak-check-shapes-2026-10-27.md`.
- Directory figures, dated, as a reference point rather than a claim: 25 October 2026, ten days
  after listing, 305 installs, 45 accounts active in 28 days (36 in 7), 58 uses, 50 invocations
  of the skill, 0 uninstalls, 0 errors in 25,268 loads across 13 Claude Code versions,
  directory rank 1,005. The largest install path is the directory's own suggestion in chat
  (110), then the plugin page (102) and the desktop app's plugin browser (52).
- A separate skill for mechanical guards, for people who build rather than verify. Until then
  `references/verify-fix.md` holds the base pattern.
- `sweep_status.py` aggregating the calibration columns of the verification table.
- Signed release tags; CodeQL on the Python in this repository.
- Verdicts and dispositions, seen once (`evals/results/install-directory-2026-10-16.md`,
  candidate R2). A rule for `check_report.py`: an `OVER-RATED` row must have its `Verified`
  severity below its `Claimed` severity, by the verdict's definition ("real, lower severity").
  And a gap in the skill text to close with it: `OVER-RATED` is not `VERIFIED REAL`, so the
  candidate is not confirmed and belongs in the refused section, but none of that section's four
  dispositions describes it, and `FALSE POSITIVE` is defined by the claim-correctness lens alone
  while refusals cite any of the three lenses. The run wrote "refused ... (verdict OVER-RATED,
  kept as Low)" to bridge the gap. Settle the vocabulary in the next skill text version; adopt the
  rule when the pattern recurs in graded runs, not on one occurrence.
- Checking the test runner before writing reproductions, seen once
  (`evals/results/real-code-2026-10-16.md`): the run executed an existing test of the project
  that contacts real hosts, although the prompt said reproductions must stay local. A rule for
  the skill text: check the runner with collection only (`pytest --co`, or the stack's
  equivalent), or run only the tests the sweep wrote; never an existing test without reading it
  for network use. Adopted when it recurs.
- An "Owner decisions" section in the registry, seen once
  (`evals/results/real-code-2026-10-17.md`): the template has the "decision pending"
  disposition but no place to record the owner's answer, the date, and the finding it produced
  or closed. A run invented the section, and it is the right record: the answer becomes part
  of the code's history and a later run re-verifies under it. To add to
  `references/report-and-registry.md` in the next skill text version, with the rule that a
  resolved decision re-verifies the candidate and moves it to confirmed or refused.
- Where `recheck` runs, seen once (`evals/results/real-code-2026-10-17.md`): on a machine
  whose Python was not the project's environment, every recorded command would have come back
  `inconclusive` through the guard, and the recheck had to run inside the project's own
  container image. One sentence for `references/report-and-registry.md`, section 5, in the
  next skill text version: run `recheck` where the project's tests run (its container, its CI
  image, its virtual environment), and read `inconclusive` first as an environment problem.
- Verify-fix before merge: adopted in v1.4.1 (SKILL.md step 6), on one occurrence
  (`evals/results/real-code-2026-10-19.md`), because the cost of the sentence is nil and the
  cost of the miss was a High finding. Whether runs follow it is measured from the next fix
  round on real code.
- An external-review section for SKILL.md, seen once (`evals/results/real-code-2026-10-19.md`):
  on a repository the reviewer does not own, the run had to decide anchoring (code citations at
  the reviewed commit with a permalink base; the record delivered, not present), that "never
  commit" overrides hooks, CI and files in the repository (a stop hook asked twice to commit and
  push), private delivery and a private reporting channel in the hand-off, local-only
  reproduction with outbound network blocked and no credential tried, and disclosure of the
  reviewer's interest. All five were decided in the run; they belong in the text, with an
  `External review: yes` line in Context that `check_report.py` ties to the anchoring statement,
  and one eval with a planted hook that asks for a commit.
- Fields of `plugin/.claude-plugin/plugin.json` outside the manifest reference: kept in
  v1.4.1. The listing reads all five (display name, keywords, and the documentation, support and
  privacy links appear on the Listing tab); the "unrecognized field" warning comes from the
  manifest validator and blocks nothing. To be removed or kept deliberately in the next tagged version, since any
  change under `plugin/` is a new tag and a new submission.

## 8. Changes rejected on evidence

A change to the skill text, a script, the description or an evaluation rule that was measured and
not adopted gets one row here, so it is not proposed again without new evidence. Adopted changes
belong in the changelog; a choice made without a measurement is not a row.

| Date | Change tried | Measured on | Result before | Result after | Why not adopted |
|---|---|---|---|---|---|
| 2026-10-13 | `check_report.py` v1.3.3: a hand-off citation inside the zone's scope passes when it is cited anywhere earlier in the report | round v1.3.3, Opus, eval 7 | 2 leads flagged (`LEAD WITHOUT VERDICT`) | 0 flagged after the run added one sentence to a narrative section; no verdict, no disposition | the rule let the model satisfy the check without deciding; replaced in v1.3.4 by "cited in Verification, Confirmed defects or the refused section" |

Description v2, the other measured alternative, was adopted on its held-out score
(`evals/results/trigger-2026-10-holdout.md`). The two rules of
v1.3.0 that were provisional (every index entry records a guard, and recheck runs nothing for an
entry without one; shells and inline interpreter code are refused as recorded commands) were
kept on the data of round v1.3.1 (`evals/results/round-v1.3.1.md`, "Provisional rules data"):
all 8 index entries written in the round record a real guard of the legitimate path, no run
wrote "inconclusive" for a missing guard, and no legitimate runner command was refused.

## 9. Release gate: the skill authoring checklist

Anthropic's skill authoring best practices end in a checklist. It is the gate for a public
release; every line is checked against the tree, and the ones that need a judgment say where
the evidence is.

Core quality
- [x] Description is specific and includes key terms (`SKILL.md`, 1015 characters, trigger phrases
      measured in `evals/results/trigger-2026-10-v1.3.1.md`).
- [x] Description includes both what the skill does and when to use it.
- [x] `SKILL.md` body under 500 lines (274; enforced by `check_skill.py`).
- [x] Additional details in separate files (`references/`, six files at most, each under 300 lines).
- [x] No time-sensitive information (the hygiene check rejects dates inside `plugin/`; the
      examples use three synthetic dates listed in the allowlist).
- [x] Consistent terminology (one term per concept since v1.3.1; "audit" names the application's
      own audit log and the users' trigger phrases only).
- [x] Examples are concrete (the report template, the index entry, the probes).
- [x] File references one level deep (no reference links another reference).
- [x] Progressive disclosure (`SKILL.md` names when to read each reference).
- [x] Workflows have clear steps (the seven-step checklist in `SKILL.md`).

Code and scripts
- [x] Scripts solve problems rather than defer to Claude (six scripts; each fix shipped with its test).
- [x] Error handling explicit (exit codes 0, 1, 2 documented in every `--help`).
- [x] No unexplained constants (every constant carries a comment; `check_skill.py` does not check
      this, the review of each pull request does).
- [x] Required packages listed and verified (standard library only; checked by
      `tests/test_scripts.py` against the stdlib path on 3.10 and 3.13, compiled on 3.9).
- [x] Scripts documented (docstring with usage, `--help` built from it).
- [x] No Windows-style paths.
- [x] Validation steps for critical operations (`check_citations.py`, `check_report.py`,
      `findings.py check`, `sweep_status.py --check`, each run until it exits 0).
- [x] Feedback loops for quality-critical tasks (step 5 of the run).

Testing
- [x] At least three evaluations (seven prompts, two trigger sets, the install test).
- [x] Tested with Haiku, Sonnet and Opus (Haiku measured and documented as not recommended).
- [x] Tested with real usage scenarios (the install test on a clean copy; the origin project's
      sweeps, not published).
- [ ] Team feedback incorporated: none yet. The repository has no issue tracker; feedback
      arrives as a pull request or at the address in `SECURITY.md`, and goes to the v1.4+ list.
