# Trigger evaluation per model, 2026-10

Trigger loop on `evals/trigger-eval.json` (20 queries: 10 should_trigger=true, 10 near misses;
three in Romanian), three runs per query, one worker, for three models of the nested sessions.
The description in `plugin/skills/defensive-audit-sweep/SKILL.md` was measured as it is on `main`
at `8b169d1`; it was not changed and no alternative was proposed. This closes the "per-model
evaluation figures" item deferred in `docs/BUILD.md` section 7.

## Results

A run counts as a trigger only when the first tool call of the nested session is `Skill` on the
temporary command (column "Skill", the figure comparable with BUILD.md section 5). Column "Skill
or Read" also counts a first `Read` of the temporary command file. Precision and recall are per
run: 30 positive runs and 30 negative runs per model. A query fails when its trigger rate is on
the wrong side of 0.5.

| Model | Precision (Skill) | Recall (Skill) | Precision (Skill or Read) | Recall (Skill or Read) | Queries passed | Missed queries | False positives |
|---|---|---|---|---|---|---|---|
| `claude-opus-5-5` | 1.00 (29/29) | 0.97 (29/30) | 1.00 (29/29) | 0.97 (29/30) | 20/20 | No query fails. One run of three missed, the query still passes:<br>"quick sanity check before I merge: 3 files changed in auth/, mostly moving the TOTP verify into a helper. is there anything that could lock legitimate users out?" (should_trigger=true, 2/3) | none (0/30 runs) |
| `claude-haiku-4-5-20251001` | 1.00 (2/2) | 0.07 (2/30) | 1.00 (2/2) | 0.07 (2/30) | 10/20 | All 10 positive queries fail:<br>"we're launching the billing module next tuesday, it's an express app with postgres under services/billing. can you do a proper security pass on it before we ship? last time we found an IDOR two days after release" (should_trigger=true, 0/3)<br>"Pune-te în locul unui auditor: ia repo-ul ăsta (Django, ~15k linii) și spune-mi ce ai găsi pe zona de autentificare, cu linie și fișier, nu păreri generale. Avem deja câteva rapoarte vechi în docs/audits, nu vreau să le reiei." (should_trigger=true, 0/3)<br>"I patched the double-submit race on /api/invites/accept (see git diff --cached). before I commit, what did this fix break? we have a few guard tests in tests/guards" (should_trigger=true, 1/3)<br>"review this PR please, it touches the session middleware and the org switch endpoint https://github.com/acme/portal/pull/412" (should_trigger=true, 0/3)<br>"our contractor delivered the vendor onboarding form yesterday (public token links, no login). I want someone to look at it with fresh eyes for enumeration, rate limiting, that kind of thing. repo is ~/work/vendorhub" (should_trigger=true, 0/3)<br>"ce a stricat fix-ul ăsta? am adăugat requirePaidPlan pe bulk PUT și acum nu mai sunt sigur că citirile pe plan expirat mai merg. diff-ul e staged." (should_trigger=true, 0/3)<br>"find bugs in the money path: invoices, plan changes, the monthly quota cron. rails app, app/models/invoice.rb and the jobs folder. no fixes, just a report I can hand to the team" (should_trigger=true, 0/3)<br>"we keep re-finding the same issues every quarter and nobody remembers what was already fixed. can you set up an audit process for this repo that tracks what was swept and when, and run the first pass on the API layer" (should_trigger=true, 1/3)<br>"pentest-style read of the public endpoints under src/routes/public/*.ts, I want evidence per finding not a checklist. go app is in the same monorepo under /gateway, ignore that for now" (should_trigger=true, 0/3)<br>"quick sanity check before I merge: 3 files changed in auth/, mostly moving the TOTP verify into a helper. is there anything that could lock legitimate users out?" (should_trigger=true, 0/3) | none (0/30 runs) |
| `claude-sonnet-5-5` | 1.00 (22/22) | 0.73 (22/30) | 1.00 (22/22) | 0.73 (22/30) | 17/20 | Three positive queries fail:<br>"ce a stricat fix-ul ăsta? am adăugat requirePaidPlan pe bulk PUT și acum nu mai sunt sigur că citirile pe plan expirat mai merg. diff-ul e staged." (should_trigger=true, 0/3)<br>"find bugs in the money path: invoices, plan changes, the monthly quota cron. rails app, app/models/invoice.rb and the jobs folder. no fixes, just a report I can hand to the team" (should_trigger=true, 1/3)<br>"quick sanity check before I merge: 3 files changed in auth/, mostly moving the TOTP verify into a helper. is there anything that could lock legitimate users out?" (should_trigger=true, 0/3) | none (0/30 runs) |

The two counting rules give the same figures for all three models: no nested session opened the
temporary command with `Read` as its first tool.

## What the nested session did instead

For every positive run that did not trigger, the first tool call of the nested session. "No
tool" means the session answered in text without calling any tool. The query is named by its
opening words; the full text is in the table above.

`claude-opus-5-5` (1 run):
- "quick sanity check before I merge": `Glob` (`**/auth/**`).

`claude-haiku-4-5-20251001` (28 runs):
- "we're launching the billing module": `Skill` on `security-review`; `Glob`; `Explore` (agent, mapping the module).
- "Pune-te în locul unui auditor": `Agent` (subagent `Explore`); `Glob`; `Glob`.
- "I patched the double-submit race" (2 misses): `Grep`; `Grep`.
- "review this PR please, it touches the session middleware": `Skill` on `code-review`, three times.
- "our contractor delivered the vendor onboarding form": `Glob`, three times.
- "ce a stricat fix-ul ăsta?": `Glob`; `Grep`; no tool.
- "find bugs in the money path": `Glob`; `Read` of `app/models/invoice.rb`; `Glob`.
- "we keep re-finding the same issues" (2 misses): `Read` of a file in the nested session's own project folder under the config directory; `Glob`.
- "pentest-style read of the public endpoints": `Glob`, three times.
- "quick sanity check before I merge": `Skill` on `code-review`; `Glob`; `Skill` on `code-review`.

In total, 6 of the 28 missed Haiku runs started with `Skill` on another skill (`code-review` 5,
`security-review` 1); the other 22 started with a search or read tool, an agent, or no tool.

`claude-sonnet-5-5` (8 runs):
- "ce a stricat fix-ul ăsta?": `Grep` for `requirePaidPlan`, three times.
- "find bugs in the money path" (2 misses): `Glob` on `app/{models,jobs}/**/*.rb`, twice.
- "quick sanity check before I merge": `Glob` (`**/auth/**`), three times.

No missed Sonnet or Opus run started with another skill.

## Procedure

Environment, all in one working folder outside this repository (written below as `<work>`):

- Claude Code 2.1.294, Python 3.13.12, Linux.
- This repository cloned at `main` `8b169d1`; skill under test `plugin/skills/defensive-audit-sweep`
  with its description unchanged.
- Skill harness: a working copy of skill-creator's scripts (`run_loop.py`, `run_eval.py`) taken from
  the copy available in the account, with four changes, each committed separately in the working
  copy and tested offline against a fake `claude` before any real run:
  1. the stream left in the pipe when the nested process exits is parsed to the end, including a
     final line without a newline (the `Skill` call can be in the last fragment; the original
     version counted 0/3 on that case, the corrected one 3/3);
  2. temporary commands left by a stopped run (`<skill>-skill-*.md` in the project's
     `.claude/commands/`) are deleted before each run;
  3. one worker only: the default of `--num-workers` is 1 and any other value is refused;
  4. a trigger counts only when the first tool is `Skill` on the temporary command; a first `Read`
     of the command file is counted apart; the first tool and its input are logged for every run.
  A timeout is counted as not triggered and logged with a warning.
- `<work>/trigger-config`: `CLAUDE_CONFIG_DIR` for the nested sessions, created with only the
  credentials file and a `settings.json` denying `Bash`, `Write`, `Edit`. Skills synced from the
  account are added to it by Claude Code at session start (see Incidents).
- `<work>/trigger-project`: empty project with an empty `.claude/` directory, cwd of the nested
  sessions; the skill under test is mounted there as the harness's temporary command, not installed.

Isolation checks before the runs:

- `ls ~/.claude/skills ~/.claude/plugins 2>/dev/null | grep -i audit` returns nothing, and a
  recursive search of the same folders finds no copy of the skill.
- `claude -p "list the skills available to you, names only"` with the test `CLAUDE_CONFIG_DIR`,
  run three times after the account change (see Incidents): no `defensive-audit-sweep` and no
  `audit-sweep` in the answer.

Command, one model at a time, in this order: Opus, Haiku, Sonnet. Each run started after the
previous one finished and its row was written.

```bash
cd <work>/trigger-project
CLAUDE_CONFIG_DIR=<work>/trigger-config PYTHONPATH=<work>/skill-creator-work \
python3 -m scripts.run_loop \
  --eval-set <work>/repo/evals/trigger-eval.json \
  --skill-path <work>/repo/plugin/skills/defensive-audit-sweep \
  --model <model> \
  --num-workers 1 --runs-per-query 3 --holdout 0 --max-iterations 1 --timeout 120 \
  --report none --results-dir <work>/results/<model> --verbose
```

`--model` is the harness's own parameter: `run_eval.py` passes it to the nested session as
`claude -p --model <model>`. With `--max-iterations 1` and `--holdout 0` the loop evaluates the
current description once on all 20 queries and exits before the description improvement step.
Trigger threshold 0.5 (the default).

| Model (`--model`) | Started (results folder) | Eval time | Exit |
|---|---|---|---|
| `claude-opus-5-5` | 2026-10-08 10:37 | 332 s | 0 |
| `claude-haiku-4-5-20251001` | 2026-10-08 10:43 | 367 s | 0 |
| `claude-sonnet-5-5` | 2026-10-08 10:49 | 308 s | 0 |

## Incidents

- **Isolation failure before the first run (no loop had run).** The first isolation check passed,
  then the nested session synced the account's skills into the test config directory, among them
  `defensive-audit-sweep`; the next check listed it. The skill was installed in the account that
  runs the loop, the case BUILD.md section 5 warns about (recall 0 with no error). The account
  owner removed it from the account; the test config directory was recreated from the credentials
  file alone; the stale local copy left in the user config folder was moved out of it (not
  deleted). The isolation check was then run three times with no match.
- **Other account skills in the nested sessions.** Claude Code syncs the account's skills into
  any `CLAUDE_CONFIG_DIR` at session start, so the test config directory does not stay
  credentials-only. Accepted as a realistic environment: a skill that loses queries to others has
  a description problem, not a harness problem. The 17 synced skills present during all three
  runs are the app's own (browser, computer use, research, document formats, skill-creator)
  and 3 specific to the account; their names are not listed here. The built-in
  skills of Claude Code (for example `code-review`, `security-review`) are present as well.
- **Reruns:** none. Each model ran once, to completion.
- **Timeouts (120 s):** 0 for `claude-opus-5-5`, 0 for `claude-haiku-4-5-20251001`, 0 for
  `claude-sonnet-5-5`.
- **Errors:** none. No harness warning, no failed query, no stale temporary command found at any
  start, and none left after any run.
- **Denied tool attempted.** In 5 Sonnet runs on negative queries (the npm audit and log sweep
  queries) the first tool call was `Bash`, which the config denies. The harness ends the session at
  the first tool call, so nothing ran; no file was created in the test project. A direct probe with
  the same config confirmed that `Bash` is not offered to the nested session at all.
- **Model not confirmed from transcripts.** The harness stops each nested session at its first tool
  call, before the turn is written to the session transcript, so the model actually serving each
  run is not recorded there. The model is the one passed with `--model`; the three runs show
  clearly different behavior.
