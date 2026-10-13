# Trigger evaluation of v1.3.1 (`verified-security-sweep`), alone and next to another collection, 2026-10

Trigger loop of the skill at plugin version 1.3.1 on two sets of 20 queries (10 should_trigger=true, 10 near misses),
`evals/trigger-eval.json` (tuning) and `evals/trigger-eval-holdout-2.json`, three runs per query, one worker, for
`claude-sonnet-5-5` and `claude-opus-5-5`, in two parts: part 1 without any other collection installed; part 2 with
`addyosmani/agent-skills` installed next to the skill (criterion B7 of `docs/BUILD.md`). Both parts use the same
sets, models, harness and parameters. The description was not changed. Haiku was not measured.

## Results

A run counts as a trigger only when the first tool call of the nested session is `Skill` on the temporary command
(comparable with `docs/BUILD.md` section 5). Precision and recall are per run: 30 positive runs and 30 negative runs
per row. A query fails when its trigger rate is on the wrong side of 0.5. Counting a first `Read` of the temporary
command file as well ("Skill or Read") gives the same figures in every row.

Interpretation (the only one in this file): on Opus the collection loads for its own query and wins none of the
positive runs of this skill; on Sonnet the collection did not load even for its own query, so there the result shows
that this skill does not lose, not that it beat an active competitor.

### Part 1: without another collection

| Model | Set | Precision | Recall | Queries passed | Missed queries | False positives | Skill or Read | Timeouts |
|---|---|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` | tuning | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-sonnet-5-5` | holdout-2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-opus-5-5` | tuning | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-opus-5-5` | holdout-2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |

### Part 2: with `agent-skills` installed next to the skill

Load check first (three nested sessions per model, without the temporary command, prompt "harden the webhook endpoint
that fetches user-supplied URLs server-side"; loaded means a first call of `Skill` on one of the collection's skills):

| # | Model | First tool call | Skill named | Seconds | Loaded |
|---|---|---|---|---|---|
| 1 | `claude-sonnet-5-5` | `Grep` | pattern "webhook" | 6.5 | no |
| 1 | `claude-opus-5-5` | `Skill` | `agent-skills:security-and-hardening` | 9.3 | yes |
| 2 | `claude-sonnet-5-5` | `Grep` | pattern "webhook" | 2.9 | no |
| 2 | `claude-opus-5-5` | `Skill` | `agent-skills:security-and-hardening` | 4.9 | yes |
| 3 | `claude-sonnet-5-5` | `Grep` | pattern "webhook" | 7.8 | no |
| 3 | `claude-opus-5-5` | `Skill` | `agent-skills:security-and-hardening` | 3.6 | yes |

Loaded in 0 of 3 on `claude-sonnet-5-5` and in 3 of 3 on `claude-opus-5-5`. The installation is valid under the rule
of `docs/BUILD.md` section 5 at `1ff4b7d` (at least one model loads the collection).

| Model | Set | Precision | Recall | Queries passed | Missed queries | False positives | Skill or Read | Timeouts |
|---|---|---|---|---|---|---|---|---|
| `claude-sonnet-5-5` | tuning | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-sonnet-5-5` | holdout-2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-opus-5-5` | tuning | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |
| `claude-opus-5-5` | holdout-2 | 1.00 (30/30) | 1.00 (30/30) | 20/20 | none | none (0/30 runs) | 30/30 positive runs | 0 |

### Criterion B7

Queries that ask for continuity or for verifying a fix: 3, 6 and 8 of `evals/trigger-eval.json` and 1, 2, 5 and 6 of
`evals/trigger-eval-holdout-2.json` (positions in the file). Cell: runs won by this skill (x/3). PASS when the
model wins at least 2 of 3; the last row is PASS when all 7 pass.

| Set | # | Query | Sonnet | Opus |
|---|---|---|---|---|
| tuning | 3 | I patched the double-submit race on /api/invites/accept (see git diff --cached).... | 3/3 PASS | 3/3 PASS |
| tuning | 6 | ce a stricat fix-ul ... (Romanian, cut at the first non-ASCII character) | 3/3 PASS | 3/3 PASS |
| tuning | 8 | we keep re-finding the same issues every quarter and nobody remembers what was a... | 3/3 PASS | 3/3 PASS |
| holdout-2 | 1 | we fixed a couple of things after last month's security review, can you check wh... | 3/3 PASS | 3/3 PASS |
| holdout-2 | 2 | can you re-run the reproduction tests from the last security review and tell me... | 3/3 PASS | 3/3 PASS |
| holdout-2 | 5 | I staged a fix for the IDOR on /api/projects/:id. does it break anything legit?... | 3/3 PASS | 3/3 PASS |
| holdout-2 | 6 | we keep re-finding the same issues every quarter. set up a proper review record... | 3/3 PASS | 3/3 PASS |
| all 7 | | | PASS | PASS |

Every query of both sets has the same x/3 with and without the collection, for both models (80 query rows compared).

## What the nested session did instead

First tool call of every run that did not trigger. The positive runs that did not trigger: none in any row of either
part. The negative runs (30 per row) are listed by the name of the first call; for `Skill` and `Agent` the skill or
subagent it names, and the opening words of the queries where it happened.

**Part 1, without the collection.**

- `claude-sonnet-5-5`, tuning: `Glob` 5; `Read` 5; `Bash` 4; `Grep` 3; `Skill anthropic-skills:docx` 3; `Skill code-review` 3; `ToolSearch` 3; `no tool` 3; `Agent (no subagent type)` 1.
  - `Agent (no subagent type)`: "run npm audit and semgrep on the repo and su" (1).
  - `Skill anthropic-skills:docx`: "write a pentest report template in docx we c" (3).
  - `Skill code-review`: "review this PR, it's the new dark mode toggl" (3).
- `claude-sonnet-5-5`, holdout-2: `Glob` 17; `Read` 4; `Grep` 3; `no tool` 3; `Agent (general-purpose)` 2; `Bash` 1.
  - `Agent (general-purpose)`: "run npm audit and summarize which dependenci" (2).
- `claude-opus-5-5`, tuning: `Glob` 11; `Grep` 3; `Read` 3; `Skill anthropic-skills:docx` 3; `Skill code-review` 3; `ToolSearch` 3; `no tool` 3; `Agent (general-purpose)` 1.
  - `Agent (general-purpose)`: "run npm audit and semgrep on the repo and su" (1).
  - `Skill anthropic-skills:docx`: "write a pentest report template in docx we c" (3).
  - `Skill code-review`: "review this PR, it's the new dark mode toggl" (3).
- `claude-opus-5-5`, holdout-2: `Glob` 20; `Read` 3; `no tool` 3; `Agent (general-purpose)` 2; `Grep` 1; `Skill code-review` 1.
  - `Agent (general-purpose)`: "run npm audit and summarize which dependenci" (2).
  - `Skill code-review`: "review this PR, it renames some CSS classes" (1).

**Part 2, with the collection.**

- `claude-sonnet-5-5`, tuning: `Glob` 9; `ToolSearch` 4; `Bash` 3; `Grep` 3; `Read` 3; `Skill anthropic-skills:docx` 3; `no tool` 3; `Skill code-review` 2.
  - `Skill anthropic-skills:docx`: "write a pentest report template in docx we c" (3).
  - `Skill code-review`: "review this PR, it's the new dark mode toggl" (2).
- `claude-sonnet-5-5`, holdout-2: `Glob` 19; `Bash` 3; `Read` 3; `no tool` 3; `Grep` 1; `Skill agent-skills:code-review-and-quality` 1.
  - `Skill agent-skills:code-review-and-quality`: "review this PR, it renames some CSS classes" (1).
- `claude-opus-5-5`, tuning: `Glob` 11; `Grep` 3; `Read` 3; `Skill anthropic-skills:docx` 3; `Skill code-review` 3; `ToolSearch` 3; `no tool` 3; `Agent (general-purpose)` 1.
  - `Agent (general-purpose)`: "run npm audit and semgrep on the repo and su" (1).
  - `Skill anthropic-skills:docx`: "write a pentest report template in docx we c" (3).
  - `Skill code-review`: "review this PR, it's the new dark mode toggl" (3).
- `claude-opus-5-5`, holdout-2: `Glob` 20; `Read` 3; `no tool` 3; `Skill agent-skills:performance-optimization` 2; `Skill agent-skills:ci-cd-and-automation` 1; `Skill code-review` 1.
  - `Skill agent-skills:ci-cd-and-automation`: "set up CodeQL in our GitHub Actions workflow" (1).
  - `Skill agent-skills:performance-optimization`: "the login page is slow, can you profile the" (2).
  - `Skill code-review`: "review this PR, it renames some CSS classes" (1).

Skills or subagents of the collection named as the first call of a run, over the 240 runs of part 2: agent-skills:ci-cd-and-automation 1 (`claude-opus-5-5`, holdout-2); agent-skills:performance-optimization 2 (`claude-opus-5-5`, holdout-2); agent-skills:code-review-and-quality 1 (`claude-sonnet-5-5`, holdout-2). All were negative runs.
No run began with `agent-skills:security-and-hardening`, `agent-skills:using-agent-skills` or the `security-auditor` subagent in the loop.

Where the `Skill` or `Agent` first calls of the negative runs differ between part 1 and part 2 (positions in the set file):

- `claude-sonnet-5-5`, tuning #14 "review this PR, it's the new dark mode toggle and some tailw...": without `Skill code-review` 3; with `Skill code-review` 2.
- `claude-sonnet-5-5`, tuning #15 "run npm audit and semgrep on the repo and summarize what's c...": without `Agent (no subagent type)` 1; with none.
- `claude-sonnet-5-5`, holdout-2 #11 "run npm audit and summarize which dependencies have critical...": without `Agent (general-purpose)` 2; with none.
- `claude-sonnet-5-5`, holdout-2 #16 "review this PR, it renames some CSS classes and updates the...": without none; with `Skill agent-skills:code-review-and-quality` 1.
- `claude-opus-5-5`, holdout-2 #11 "run npm audit and summarize which dependencies have critical...": without `Agent (general-purpose)` 2; with none.
- `claude-opus-5-5`, holdout-2 #15 "set up CodeQL in our GitHub Actions workflow": without none; with `Skill agent-skills:ci-cd-and-automation` 1.
- `claude-opus-5-5`, holdout-2 #18 "the login page is slow, can you profile the auth controller...": without none; with `Skill agent-skills:performance-optimization` 2.

## Procedure

Environment, all in one working folder outside this repository (written below as `<work>`):

- Claude Code 2.1.296, Python 3.13.12, Linux. Runs on 2026-10-12.
- This repository, `main`:
  - part 1 at `347c859` (`347c859707899bc2c45b4d7ea189ca95ce2a50aa`), plugin `"version": "1.3.1"`;
  - part 2 at `1ff4b7d` (`1ff4b7dcca937d9b7343ae5ed26392dde2a4230f`).
  - `git diff 347c859 HEAD --stat -- plugin/` at `1ff4b7d` is empty: `plugin/` is identical in both parts. The only
    change between the two commits is `docs/BUILD.md` (5 insertions, 2 deletions), see Incidents, item 4.
- Skill under test: `plugin/skills/verified-security-sweep`. The first line of the description in the log of every
  combination: "Verified security and correctness review of a codebase as a repeatable, recorded sweep: pick a ...".
- Query set `evals/trigger-eval.json`: blob `4a9fa8c761a83596b99d9f650776f441523c4cea`, same at both commits; read with `git show` into `<work>/sets/tuning.json`, whose blob hash is the same.
- Query set `evals/trigger-eval-holdout-2.json`: blob `dff1b373fc6acbe302b3ede5a849efa864781071`, same at both commits; read with `git show` into `<work>/sets/holdout-2.json`, whose blob hash is the same.
- Skill harness: the working copy of skill-creator's scripts of `evals/results/trigger-2026-10-holdout.md`, with the
  same five changes (including `--strict-mcp-config --mcp-config '{"mcpServers":{}}'` on every nested session).
  It logs, for every run, the first tool call and its input (the first 300 characters), which names the skill for
  `Skill` and the subagent for `Agent`; `run_details` with `first_input` is written to `results.json`.
- `<work>/trigger-config` and `<work>/trigger-project`: the same directories as in the earlier measurements.

Isolation checks before part 1:

- A recursive name search of `~/.claude/skills`, `~/.claude/plugins` and `~/.claude/commands` for "sweep" or "audit"
  returns `security-auditor.md` (known) and four names under `~/.claude/plugins` that are not skills (Incidents, item 1).
  A content search for `verified-security-sweep`, `defensive-audit-sweep` and `audit-sweep` in the same folders returns
  no file. The same name search in `trigger-config` finds only the project folder name.
- `claude -p "list the skills available to you, names only"` with `CLAUDE_CONFIG_DIR` on `trigger-config`, run twice:
  the same 31 skills both times, none named `verified-security-sweep` or `audit-sweep`.
- No tool with the `mcp__` prefix in the orchestrating session; in the 480 runs of the two parts no first tool call has
  that prefix.

Part 2 setup, from `evals/fixtures/README.md`:

- Collection `addyosmani/agent-skills`, commit `1401c8b8030e023baeebb31781a6653fe8e93026` (checked with `git rev-parse`
  before the install, before the loop and after the removal), cloned detached in `<work>/coinstall`. It ships 25 skills
  and 4 subagents.
- Local marketplace `coinstall-test` (`<work>/coinstall/.claude-plugin/marketplace.json`), installed as
  `agent-skills@coinstall-test` (version 0.6.12, scope user, enabled) with `CLAUDE_CONFIG_DIR` on `trigger-config` only.
  `ls -R ~/.claude/plugins | grep -i agent-skills` returned nothing before the install, after the install and after the
  removal. A snapshot of size and time of every file under `~/.claude/plugins` and `~/.claude/skills` taken before the
  install was identical after it (see Incidents, item 5 for the end).
- Load check: one nested `claude -p` per model and run, in `trigger-project`, without the temporary command, the same
  command line as the harness; the first tool call is read from the stream (`loadcheck.py`, raw streams kept).

Command, one combination at a time, in this order in each part: Sonnet and tuning, Sonnet and holdout-2, Opus and tuning,
Opus and holdout-2. Each run started after the previous one finished; part 2 started after part 1.

```bash
cd <work>/trigger-project
CLAUDE_CONFIG_DIR=<work>/trigger-config PYTHONPATH=<work>/skill-creator-work \
python3 -m scripts.run_loop \
  --eval-set <work>/sets/<tuning|holdout-2>.json \
  --skill-path <work>/repo/plugin/skills/verified-security-sweep \
  --model <model> \
  --num-workers 1 --runs-per-query 3 --holdout 0 --max-iterations 1 \
  --timeout 120 --report none --results-dir <work>/results-v1.3.1/[coinstall/]<model>-<set> --verbose
```

With `--max-iterations 1` the loop evaluates once and exits before the description improvement step. Trigger threshold
0.5 (the default). Cleanup after part 2: `claude plugin uninstall agent-skills@coinstall-test` and
`claude plugin marketplace remove coinstall-test`, then `claude plugin list` reports no plugins in `trigger-config`.

| Part | Model (`--model`) | Set | Started (local time) | Eval time | Exit |
|---|---|---|---|---|---|
| 1 | `claude-sonnet-5-5` | tuning | 2026-10-12 15:29:31 | 432.5 s | 0 |
| 1 | `claude-sonnet-5-5` | holdout-2 | 2026-10-12 15:38:54 | 242.9 s | 0 |
| 1 | `claude-opus-5-5` | tuning | 2026-10-12 15:43:02 | 296.8 s | 0 |
| 1 | `claude-opus-5-5` | holdout-2 | 2026-10-12 15:48:03 | 252.1 s | 0 |
| 2 | `claude-sonnet-5-5` | tuning | 2026-10-12 16:03:16 | 259.3 s | 0 |
| 2 | `claude-sonnet-5-5` | holdout-2 | 2026-10-12 16:07:40 | 229.7 s | 0 |
| 2 | `claude-opus-5-5` | tuning | 2026-10-12 16:11:33 | 291.2 s | 0 |
| 2 | `claude-opus-5-5` | holdout-2 | 2026-10-12 16:16:30 | 252.0 s | 0 |

## Incidents

1. **Name matches under `~/.claude/plugins`.** The name search of the isolation check returned, besides the known
   `security-auditor.md`, four names inside `~/.claude/plugins`: `marketplaces/claude-code-plugins/scripts/sweep.ts`,
   `marketplaces/claude-code-plugins/.github/workflows/sweep.yml`,
   `marketplaces/claude-code-plugins/mods/telemetry/tests/fixtures/plugins/sweeping.ts` and `.last_inuse_sweep`.
   The folder `marketplaces/claude-code-plugins` was created on 2026-10-12, the morning of the run, so it did not exist at
   the earlier measurements. The content search for the three skill names returns 0 files, and `~/.claude/skills` holds
   only `synced`. The run was stopped and reported before part 1; the owner accepted the matches as name-only false
   positives and instructed that `~/.claude/plugins` not be touched. It was not.
2. **Credentials.** The copy in `trigger-config` was refreshed from `~/.claude/.credentials.json` before part 1 and
   before every later combination. The owner ran `/login` in the orchestrating session between the first and the second
   combination of part 1; the source was then newer than the copy (15:38 against 15:35), the copy was made again and a
   nested `claude -p "reply with the single word ok"` answered "ok" before the next combination. The count of lines
   matching `authenticate|OAuth|expired|Warning|error` in the log of each of the 8 combinations is 0, 0, 0, 0, 0, 0, 0, 0.
3. **Eval time of Sonnet, tuning, part 1:** 432.5 s, against 242.9 s, 296.8 s, 252.1 s in the other three combinations of part 1 and 259.3 s for the same combination in part 2. No timeout, error or warning in that log.
4. **Load-check rule changed before part 2 (pull request #21).** At `347c859` the rule in `docs/BUILD.md` section 5 was one
   nested session per model, and the collection counted as loaded only if the first tool call was `Skill` on one of its
   skills, otherwise the loop did not start. In that first block Sonnet's first call was `Grep` (6.5 s) and Opus's was
   `Skill` on `agent-skills:security-and-hardening` (9.3 s); under that rule the loop did not start and the owner was
   told. Pull request #21 (`1ff4b7d`, "B7 load check validates the installation, reports routing per model") changed the
   rule to three sessions per model, with the installation valid when at least one model loads the collection and the
   per-model result reported as loaded in x of 3, not thresholded. Sessions 2 and 3 of each model, and part 2, were run
   after the change. The two first sessions are rows 1 of the load-check table above.
5. **Account sync during part 2.** After the cleanup, the hash of a file snapshot of `~/.claude/plugins` and
   `~/.claude/skills` differed from the one taken before the install. Files newer than the snapshot: three, all under
   `~/.claude/skills/synced/<id>/` (`manifest.json`, `.last-complete-round` and the folder), modified at 16:13:12, during the
   third combination of part 2 (Opus, tuning). No file under `~/.claude/plugins` is newer than the snapshot, and the number
   of files under both folders is the same (2864) before and after. The commands that touched plugins ran with
   `CLAUDE_CONFIG_DIR` on `trigger-config`; whether the sync was triggered by anything in the round is not known.
6. **Reruns:** none. **Timeouts (120 s):** 0 in the 8 combinations. **Errors:** none; no harness warning and no failed query. No stale temporary command found at any
   start or end.
7. **Other skills in the nested sessions.** The skill list of the isolation check has 31 entries (14 without a prefix, 17
   with the prefix `anthropic-skills:`). The only ones called first, on negative queries, are named in the section above.
   With the fifth harness change their connectors are not loaded.
8. **Load-check reader.** The first-tool reader of the load check is not part of the harness; it starts the same command
   line, reads the same stream events and stops at the first tool call.
9. **Model not confirmed from transcripts.** As before, the harness stops each nested session at its first tool call,
   before the turn is written to the session transcript; the model is the one passed with `--model`.

