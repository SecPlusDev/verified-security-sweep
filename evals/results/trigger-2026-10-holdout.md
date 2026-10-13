# Trigger evaluation on the held-out set, 2026-10

Trigger loop on `evals/trigger-eval-holdout.json` (20 queries: 10 should_trigger=true, 10 near
misses; one in Romanian), three runs per query, one worker, for two models and two descriptions:
the description on `main` and the candidate description v2 of branch `desc-v2` (pull request #5).
The held-out set was written after v2 and was not used to write either description. No
description was changed. Haiku was not measured.

## Results

A run counts as a trigger only when the first tool call of the nested session is `Skill` on the
temporary command (comparable with BUILD.md section 5). Precision and recall are per run: 30
positive runs and 30 negative runs per row. A query fails when its trigger rate is on the wrong
side of 0.5. Counting a first `Read` of the temporary command file as well ("Skill or Read") gives
the same figures in every row: no nested session opened the command file first. Rows are in run
order.

| Model | Description | Precision | Recall | Queries passed | Missed queries | False positives |
|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` | main | 1.00 (25/25) | 0.83 (25/30) | 19/20 | One query fails:<br>"I have a staged change that adds a login rate limit; I'm nervous it also blocks SSO users who hit the same route. can you check it before I commit?" (should_trigger=true, 0/3)<br>Two queries miss one run of three and still pass:<br>"go through src/payments and the cron jobs and give me a list of real defects I can hand to the team. no patches, they will do the fixing" (should_trigger=true, 2/3)<br>"we closed the IDOR on /orders/:id yesterday (see the last commit). is the fix solid, and did it break anything for admins who legitimately open other people's orders?" (should_trigger=true, 2/3) | none (0/30 runs) |
| `claude-sonnet-5-5` | v2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 (train 12/12, test 8/8) | none (0/30 runs) | none (0/30 runs) |
| `claude-opus-5-5` | main | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none (0/30 runs) | none (0/30 runs) |
| `claude-opus-5-5` | v2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 (train 12/12, test 8/8) | none (0/30 runs) | none (0/30 runs) |

The two v2 rows ran with `--holdout 0.4`, the two main rows with `--holdout 0` (see Procedure).
With one iteration the split changes no figure: all 20 queries are evaluated three times either
way, and the loop only reports them in two groups. The 8 queries of the test group (fixed seed of
the harness, the same in both v2 rows): positives "Vreau o verificare serioasă pe modulul de
facturare", "we had an incident last month on the public upload endpoint", "I have a staged
change that adds a login rate limit", "new contractor code landed in services/export"; negatives
"rotate the JWT signing secret", "add structured logging to the payments service", "set up
semgrep in GitHub Actions", "review this PR, it only updates the README". The only query that
fails under main (Sonnet, staged rate limit) is in the test group, and passes 3/3 under v2.

## What the nested session did instead

For every positive run that did not trigger and every negative run that did, the first tool call
of the nested session. The query is named by its opening words; the full text is in the table.

`claude-sonnet-5-5`, main (5 missed runs, no false positive):
- "I have a staged change that adds a login rate limit": `Grep` for rate limit and SSO terms; `Glob` (`**/*`), twice.
- "go through src/payments and the cron jobs" (1 miss): `Glob` (`src/payments/**`).
- "we closed the IDOR on /orders/:id yesterday" (1 miss): `Grep` for `/orders/`.

`claude-sonnet-5-5`, v2: no missed run, no false positive.

`claude-opus-5-5`, main: no missed run, no false positive.

`claude-opus-5-5`, v2: no missed run, no false positive.

No missed run started with another skill. On negative queries, the only skills called first were
`code-review` (the README pull request query: Opus main 1 run, Opus v2 2 runs, Sonnet v2 1 run)
and the synced `docs` skill (the rules-of-engagement letter query: Opus main 3 runs, Opus v2 3
runs); these are correct non-triggers for this skill.

## Procedure

Environment, all in one working folder outside this repository (written below as `<work>`):

- Claude Code 2.1.294, Python 3.13.12, Linux. Runs on 2026-10-09.
- This repository: `main` at `286a6a9` for the main rows; `desc-v2` at `6a7d8f0` for the v2 rows
  (the v2 description, introduced in `6fc5fcd`; the later commit on that branch adds only a
  results file). Before each combination the branch was checked out and the first words of the
  description in `SKILL.md` were checked ("Run a defensive" on main, "Defensive security and" on
  v2); the first line of each run's log shows the expected description.
- Query set: `evals/trigger-eval-holdout.json` from this branch at `374325b`, read with `git show`
  into a file outside the repository so it stayed available while `main` and `desc-v2` were
  checked out; the copy has the same blob hash as the committed file (`c1bd900`).
- Skill harness: the working copy of skill-creator's scripts used in
  `evals/results/trigger-2026-10.md`, with the four changes listed there (pipe drained to the end
  at process exit; stale temporary commands deleted before each run; one worker only; a trigger
  counts only when the first tool is `Skill` on the temporary command, a first `Read` counted
  apart, first tool logged per run), plus a fifth change for this measurement:
  5. every nested session is launched with `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`,
     so no MCP server of the account or of any configuration file is loaded. Both flags are
     listed by `claude --help` in 2.1.294. Committed separately in the working copy.
- `<work>/trigger-config` and `<work>/trigger-project`: the same directories as in the earlier
  measurements (credentials file recopied, see Incidents).

Evidence for the fifth change, in `<work>/trigger-config` and `<work>/trigger-project`, with
`claude -p "list every tool you have, names only"`:

- without the flags: 58 tools with the `mcp__` prefix, from four account connectors (documents 8,
  mail 30, calendar 9, file storage 11);
- with `--strict-mcp-config --mcp-config '{"mcpServers":{}}'`: no tool with the `mcp__` prefix and
  no connector named; the list holds only Claude Code's own tools;
- a fake `claude` on the path, run through the harness, recorded the arguments it received: `-p
  <query> --output-format stream-json --verbose --include-partial-messages --strict-mcp-config
  --mcp-config {"mcpServers":{}} --model claude-sonnet-5-5`;
- across the 240 runs of this measurement, no first tool call has the `mcp__` prefix.

Isolation checks before the runs, after the credentials were recopied:

- `ls ~/.claude/skills ~/.claude/plugins 2>/dev/null | grep -i audit` returns nothing; a recursive
  search of the user config folder (skills, plugins, commands) and of the test config directory
  finds no copy of the skill.
- `claude -p "list the skills available to you, names only"` with the test `CLAUDE_CONFIG_DIR`,
  run twice: no `defensive-audit-sweep` and no `audit-sweep` in the answer.

Command, one combination at a time, in this order: Sonnet and main, Sonnet and v2, Opus and main,
Opus and v2. Each run started after the previous one finished.

```bash
cd <work>/trigger-project
CLAUDE_CONFIG_DIR=<work>/trigger-config PYTHONPATH=<work>/skill-creator-work \
python3 -m scripts.run_loop \
  --eval-set <work>/holdout/trigger-eval-holdout.json \
  --skill-path <work>/repo/plugin/skills/defensive-audit-sweep \
  --model <model> \
  --num-workers 1 --runs-per-query 3 --holdout <0 for main, 0.4 for v2> --max-iterations 1 \
  --timeout 120 --report none --results-dir <work>/results-holdout/<model>-<main|v2> --verbose
```

With `--max-iterations 1` the loop evaluates once and exits before the description improvement
step, with either holdout value. Trigger threshold 0.5 (the default).

| Model (`--model`) | Description | `--holdout` | Started (results folder) | Eval time | Exit |
|---|---|---|---|---|---|
| `claude-sonnet-5-5` | main | 0 | 2026-10-09 08:38 | 201 s | 0 |
| `claude-sonnet-5-5` | v2 | 0.4 | 2026-10-09 08:44 | 194 s | 0 |
| `claude-opus-5-5` | main | 0 | 2026-10-09 08:47 | 230 s | 0 |
| `claude-opus-5-5` | v2 | 0.4 | 2026-10-09 08:51 | 244 s | 0 |

## Incidents

- **Expired credentials in the test config directory.** The first attempt at the evidence for the
  fifth change failed on both sessions with "Failed to authenticate: OAuth session expired and
  could not be refreshed": the main session had refreshed its token, which rotates the refresh
  token and invalidates the copy, and the failed nested session then emptied its own credentials
  file. Nothing ran. The credentials file was copied again from the user config folder, as when
  the environment was built, and the isolation checks were repeated before any measurement.
- **Holdout value changed for the v2 rows.** The plan was `--holdout 0` for all four
  combinations. During the first run (Sonnet and main) the owner asked for `--holdout 0.4` on
  v2; the running combination was not stopped, and the two v2 combinations ran with 0.4. Figures
  are unaffected (see Results), but the main and v2 rows do not share that parameter.
- **Reruns:** none. Each combination ran once, to completion.
- **Timeouts (120 s):** 0 in each of the four combinations.
- **Errors:** none. No harness warning, no failed query, no stale temporary command found at any
  start, and none left after any run.
- **Other account skills in the nested sessions.** As in the earlier measurements, the account's
  skills are synced into the test config directory at session start; the same 17 were present:
  the app's own (browser, computer use, research, document formats, skill-creator) and 3
  specific to the account; their names are not listed here. With the
  fifth change their connectors are no longer loaded; a skill that needs a connector (for example
  `docs`) can be called but has no tool to act with.
- **No denied tool attempted.** Unlike the earlier measurements, no run started with `Bash`.
- **Model not confirmed from transcripts.** As before, the harness stops each nested session at
  its first tool call, before the turn is written to the session transcript; the model is the one
  passed with `--model`.
