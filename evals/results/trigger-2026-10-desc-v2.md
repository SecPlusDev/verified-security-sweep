# Trigger evaluation per model, description v2, 2026-10

Trigger loop on `evals/trigger-eval.json` (20 queries: 10 should_trigger=true, 10 near misses;
three in Romanian), three runs per query, one worker, for three models of the nested sessions,
on the candidate description of branch `desc-v2` (`6fc5fcd`). The only difference from `main`
(`286a6a9`) is the `description` block of `plugin/skills/defensive-audit-sweep/SKILL.md`. Same
harness, environment, command and parameters as `evals/results/trigger-2026-10.md`, which
measured the `main` description earlier the same day.

## Description measured

```
Defensive security and correctness audit of a codebase as a repeatable, recorded sweep: pick a
zone, delegate the reading to fresh-context reviewers with a strict brief, verify every finding
on the actual code lines, reproduce the real ones with a failing test, record the run in an
audit registry, and verify fixes adversarially before they ship. Use it, before any grep or file
read, whenever someone asks in any language for a security review, code audit, pentest-style
read, "check this codebase", "find bugs in X, no fixes, just a report", a pre-launch or
pre-merge check, a "quick sanity check" of changed files, a review of recently shipped code,
"what did this fix break", "could this lock users out", a staged diff to verify before commit,
or an audit process that does not re-report what is already fixed. Also for any diff touching
auth, tenancy, money, concurrency or public endpoints, even if the user only says "review this
PR". The value is the discipline (verify, reproduce, record), not the reading.
```

The line breaks are those of the YAML block in `SKILL.md`; the harness reads the folded scalar as
one paragraph.

## Results

A run counts as a trigger only when the first tool call of the nested session is `Skill` on the
temporary command (column "Skill", comparable with BUILD.md section 5). Column "Skill or Read" also
counts a first `Read` of the temporary command file. Precision and recall are per run: 30
positive runs and 30 negative runs per model. A query fails when its trigger rate is on the wrong
side of 0.5. Rows are in run order.

| Model | Precision (Skill) | Recall (Skill) | Precision (Skill or Read) | Recall (Skill or Read) | Queries passed | Missed queries | False positives |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` | 0.97 (30/31) | 1.00 (30/30) | 0.97 (30/31) | 1.00 (30/30) | 20/20 | none (0/30 runs) | One run of three, the query still passes:<br>"review this PR, it's the new dark mode toggle and some tailwind cleanup in the settings page https://github.com/acme/portal/pull/418" (should_trigger=false, 1/3) |
| `claude-opus-5-5` | 1.00 (30/30) | 1.00 (30/30) | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none (0/30 runs) | none (0/30 runs) |
| `claude-haiku-4-5-20251001` | 0.75 (3/4) | 0.10 (3/30) | 0.75 (3/4) | 0.10 (3/30) | 11/20 | 9 of 10 positive queries fail:<br>"we're launching the billing module next tuesday, it's an express app with postgres under services/billing. can you do a proper security pass on it before we ship? last time we found an IDOR two days after release" (should_trigger=true, 0/3)<br>"Pune-te în locul unui auditor: ia repo-ul ăsta (Django, ~15k linii) și spune-mi ce ai găsi pe zona de autentificare, cu linie și fișier, nu păreri generale. Avem deja câteva rapoarte vechi în docs/audits, nu vreau să le reiei." (should_trigger=true, 0/3)<br>"I patched the double-submit race on /api/invites/accept (see git diff --cached). before I commit, what did this fix break? we have a few guard tests in tests/guards" (should_trigger=true, 0/3)<br>"review this PR please, it touches the session middleware and the org switch endpoint https://github.com/acme/portal/pull/412" (should_trigger=true, 0/3)<br>"our contractor delivered the vendor onboarding form yesterday (public token links, no login). I want someone to look at it with fresh eyes for enumeration, rate limiting, that kind of thing. repo is ~/work/vendorhub" (should_trigger=true, 0/3)<br>"ce a stricat fix-ul ăsta? am adăugat requirePaidPlan pe bulk PUT și acum nu mai sunt sigur că citirile pe plan expirat mai merg. diff-ul e staged." (should_trigger=true, 0/3)<br>"find bugs in the money path: invoices, plan changes, the monthly quota cron. rails app, app/models/invoice.rb and the jobs folder. no fixes, just a report I can hand to the team" (should_trigger=true, 0/3)<br>"pentest-style read of the public endpoints under src/routes/public/*.ts, I want evidence per finding not a checklist. go app is in the same monorepo under /gateway, ignore that for now" (should_trigger=true, 0/3)<br>"quick sanity check before I merge: 3 files changed in auth/, mostly moving the TOTP verify into a helper. is there anything that could lock legitimate users out?" (should_trigger=true, 0/3) | One run of three, the query still passes:<br>"scrie un raport de audit ISO 27001 pentru clientul X pe baza notelor mele din interviuri, format pentru certificare" (should_trigger=false, 1/3) |

The two counting rules give the same figures for all three models: no nested session opened the
temporary command with `Read` as its first tool.

## What the nested session did instead

For every positive run that did not trigger, the first tool call of the nested session. "No
tool" means the session answered in text without calling any tool. The query is named by its
opening words; the full text is in the table above.

`claude-sonnet-5-5`: no missed run.

`claude-opus-5-5`: no missed run.

`claude-haiku-4-5-20251001` (27 runs):
- "we're launching the billing module": `Skill` on `security-review`, twice; `Skill` on `import-memory`.
- "Pune-te în locul unui auditor": `Glob`, three times.
- "I patched the double-submit race": `Grep`; `Skill` on `code-review`; `Read` of the project folder.
- "review this PR please, it touches the session middleware": `Skill` on `code-review`, three times.
- "our contractor delivered the vendor onboarding form": `Glob`; `Skill` on `security-review`, twice.
- "ce a stricat fix-ul ăsta?": `Glob`; `Skill` on `code-review`, twice.
- "find bugs in the money path": `Glob`, three times.
- "pentest-style read of the public endpoints": `Glob`, twice; `Read` of a file in the nested session's own project folder under the config directory.
- "quick sanity check before I merge": `Skill` on `code-review`, twice; `Grep`.

In total, 13 of the 27 missed Haiku runs started with `Skill` on another skill (`code-review` 8,
`security-review` 4, `import-memory` 1); the other 14 started with a search or read tool.

## Comparison with the main description

Main: the `main` description, measured in `evals/results/trigger-2026-10.md` (runs started
10:37 to 10:49). v2: this file (runs started 13:13 to 13:25). Same day, same environment.

| Model | Recall (Skill), main | Recall (Skill), v2 | Precision (Skill), main | Precision (Skill), v2 | Queries passed, main | Queries passed, v2 |
|---|---|---|---|---|---|---|
| `claude-opus-5-5` | 0.97 (29/30) | 1.00 (30/30) | 1.00 (29/29) | 1.00 (30/30) | 20/20 | 20/20 |
| `claude-sonnet-5-5` | 0.73 (22/30) | 1.00 (30/30) | 1.00 (22/22) | 0.97 (30/31) | 17/20 | 20/20 |
| `claude-haiku-4-5-20251001` | 0.07 (2/30) | 0.10 (3/30) | 1.00 (2/2) | 0.75 (3/4) | 10/20 | 11/20 |

Missed positive runs per query (triggers out of 3) and the first tool of each missed run. Only
queries missed at least once under either description are listed.

`claude-opus-5-5`:

| Query | Main | First tool, main | v2 | First tool, v2 |
|---|---|---|---|---|
| "quick sanity check before I merge" | 2/3 | `Glob` | 3/3 | none missed |

`claude-sonnet-5-5`:

| Query | Main | First tool, main | v2 | First tool, v2 |
|---|---|---|---|---|
| "ce a stricat fix-ul ăsta?" | 0/3 | `Grep` x3 | 3/3 | none missed |
| "find bugs in the money path" | 1/3 | `Glob` x2 | 3/3 | none missed |
| "quick sanity check before I merge" | 0/3 | `Glob` x3 | 3/3 | none missed |

`claude-haiku-4-5-20251001`:

| Query | Main | First tool, main | v2 | First tool, v2 |
|---|---|---|---|---|
| "we're launching the billing module" | 0/3 | `Skill` `security-review`; `Glob`; `Explore` | 0/3 | `Skill` `security-review` x2; `Skill` `import-memory` |
| "Pune-te în locul unui auditor" | 0/3 | `Agent` (`Explore`); `Glob` x2 | 0/3 | `Glob` x3 |
| "I patched the double-submit race" | 1/3 | `Grep` x2 | 0/3 | `Grep`; `Skill` `code-review`; `Read` |
| "review this PR please, it touches the session middleware" | 0/3 | `Skill` `code-review` x3 | 0/3 | `Skill` `code-review` x3 |
| "our contractor delivered the vendor onboarding form" | 0/3 | `Glob` x3 | 0/3 | `Glob`; `Skill` `security-review` x2 |
| "ce a stricat fix-ul ăsta?" | 0/3 | `Glob`; `Grep`; no tool | 0/3 | `Glob`; `Skill` `code-review` x2 |
| "find bugs in the money path" | 0/3 | `Glob`; `Read`; `Glob` | 0/3 | `Glob` x3 |
| "we keep re-finding the same issues" | 1/3 | `Read`; `Glob` | 3/3 | none missed |
| "pentest-style read of the public endpoints" | 0/3 | `Glob` x3 | 0/3 | `Glob` x2; `Read` |
| "quick sanity check before I merge" | 0/3 | `Skill` `code-review`; `Glob`; `Skill` `code-review` | 0/3 | `Skill` `code-review` x2; `Grep` |

False positives: none under main for any model. Under v2, one run of three for Sonnet ("review
this PR, it's the new dark mode toggle", should_trigger=false) and one for Haiku ("scrie un raport
de audit ISO 27001", should_trigger=false); both queries still pass.

Under v2, Haiku's missed runs start with another skill more often than under main (13 of 27
against 6 of 28), mostly `code-review` and `security-review`.

Note on what these figures measure. Several phrases of v2 match queries of this set almost word
for word: "find bugs in X, no fixes, just a report" (the money path query), "quick sanity check"
and "could this lock users out" (the TOTP query), "what did this fix break" and "a staged diff to
verify before commit" (the double-submit race query and the Romanian staged-diff query),
"pre-merge check" ("before I merge"), "in any language" (the Romanian queries). The loop ran with
`--holdout 0`, so no query was held out from the description. The v2 figures show how v2 scores on
this query set; they do not show how it generalizes beyond it. BUILD.md section 3 keeps the
description with the best held-out score.

## Procedure

Environment, all in one working folder outside this repository (written below as `<work>`):

- Claude Code 2.1.294, Python 3.13.12, Linux.
- This repository at branch `desc-v2` `6fc5fcd` during all three runs; `git diff main..desc-v2
  --stat` shows only `plugin/skills/defensive-audit-sweep/SKILL.md` (11 insertions, 11
  deletions), all inside the `description` block.
- Skill harness: the same working copy of skill-creator's scripts as in
  `evals/results/trigger-2026-10.md`, with the same four changes (pipe drained to the end at
  process exit; stale temporary commands deleted before each run; one worker only; a trigger
  counts only when the first tool is `Skill` on the temporary command, a first `Read` of the
  command file counted apart, first tool logged per run). No change since that measurement: the
  working copy has no modified tracked file.
- `<work>/trigger-config` and `<work>/trigger-project`: the same directories as in that
  measurement, reused as they were.

Isolation checks before the runs:

- `ls ~/.claude/skills ~/.claude/plugins 2>/dev/null | grep -i audit` returns nothing; a recursive
  search of the user config folder (skills, plugins, commands), of the test config directory and
  of the test project finds no copy of the skill, so it has not reappeared in `~/.claude/skills`.
- `claude -p "list the skills available to you, names only"` with the test `CLAUDE_CONFIG_DIR`,
  run twice: no `defensive-audit-sweep` and no `audit-sweep` in the answer.

Command, one model at a time, in this order: Sonnet, Opus, Haiku. Each run started after the
previous one finished and its row was written.

```bash
cd <work>/trigger-project
CLAUDE_CONFIG_DIR=<work>/trigger-config PYTHONPATH=<work>/skill-creator-work \
python3 -m scripts.run_loop \
  --eval-set <work>/repo/evals/trigger-eval.json \
  --skill-path <work>/repo/plugin/skills/defensive-audit-sweep \
  --model <model> \
  --num-workers 1 --runs-per-query 3 --holdout 0 --max-iterations 1 --timeout 120 \
  --report none --results-dir <work>/results-desc-v2/<model> --verbose
```

The first line of each run's log shows the v2 description as the one evaluated. Trigger threshold
0.5 (the default).

| Model (`--model`) | Started (results folder) | Eval time | Exit |
|---|---|---|---|
| `claude-sonnet-5-5` | 2026-10-08 13:13 | 341 s | 0 |
| `claude-opus-5-5` | 2026-10-08 13:19 | 324 s | 0 |
| `claude-haiku-4-5-20251001` | 2026-10-08 13:25 | 318 s | 0 |

## Incidents

- **Reruns:** none. Each model ran once, to completion.
- **Timeouts (120 s):** 0 for `claude-sonnet-5-5`, 0 for `claude-opus-5-5`, 0 for
  `claude-haiku-4-5-20251001`.
- **Errors:** none. No harness warning, no failed query, no stale temporary command found at any
  start, and none left after any run.
- **Other account skills in the nested sessions.** As in the earlier measurement, the account's
  skills are synced into the test config directory at session start. The same 17 were present
  during all three runs: the app's own (browser, computer use, research, document formats,
  skill-creator) and 3 specific to the account; their names are not listed here. The built-in skills of Claude Code (for example `code-review`, `security-review`) are
  present as well. One missed Haiku run started with `import-memory`, one of the synced skills.
- **Denied tool attempted.** In 2 Sonnet runs on the negative query "run npm audit and semgrep"
  the first tool call was `Bash`, which the config denies (5 such runs in the earlier
  measurement). The harness ends the session at the first tool call, so nothing ran; no file
  appeared in the test project.
- **Account connector called.** In 1 Opus run on the negative query "scrie un raport de audit ISO
  27001" the first tool call was a document creation call to a document connector of the account
  (`mcp__claude_ai_Claude_Docs__batch`): the account's connectors, like its skills, are available
  to the nested sessions. The run counts as not triggered, which is correct for that query. The
  harness ended the session at that call; the account's artifact list, checked after the runs,
  shows no document with the requested title. That list is the only view available; the connector
  offers no search by title.
- **Model not confirmed from transcripts.** As in the earlier measurement, the harness stops each
  nested session at its first tool call, before the turn is written to the session transcript;
  the model is the one passed with `--model`.
