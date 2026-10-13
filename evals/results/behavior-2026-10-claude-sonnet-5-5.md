# Behavior evaluation, `claude-sonnet-5-5`, 2026-10

Evals 1 (`nodegoat-access-control-sweep`) and 4 (`nodegoat-verify-fix`) from `evals/evals.json`,
each run once with the skill and once without, on `claude-sonnet-5-5` (the model of the session
that ran and graded them). Skill: `plugin/skills/defensive-audit-sweep` at `main` 71e4f01 (plugin
1.2.0), read from the repository, not installed in the account. Evals 2 and 3 were not run.

## Results

Graded against the assertions of `evals/evals.json` as written: for eval 1, assertions 1 to 6 and
9 (hygiene, the seventh expectation); for eval 4, the format assertion, 8a, 8b and 9 (staged fix
unchanged). Evidence paths are relative to each run's directory in the evaluation workspace
(`<eval>/<with_skill|without_skill>/`); `R` is `outputs/docs-audits/2026-10-09-access-control.md`,
the report the run wrote.

| Assertion | Eval | With skill | Without skill | Evidence |
|---|---|---|---|---|
| 1 Report and template sections | 1 | PASS | FAIL | with: `R:3`, `:15`, `:40`, `:47`, `:71`, `:93` hold the six sections. without: no Delegation section (headings `R:3`, `:12`, `:31`, `:38`, `:75`, `:91`, `:98`) |
| 2 Exact `file:line`, chain of three | 1 | PASS | FAIL | with: single line `allocations.js:16` at `R:50`, chain of three at `R:52-58`. without: ranges at `R:41-42` (`allocations.js:11-30`, `allocations-dao.js:57-100`) and `R:63` (`~63-82`) |
| 3 VERIFIED REAL with an existing reproduction test | 1 | PASS | FAIL | with: `R:43` VERIFIED REAL, test `test/security/allocations-access-test.js` exists (`outputs/git-status.txt:3`). without: no VERIFIED REAL, the verdicts at `R:34-35` read "REAL (by code reading)" with proof "none yet" |
| 4 Refused candidates with the failing lens | 1 | FAIL | FAIL | with: lens named at `R:72` (claim correctness), `:79` and `:81` (exploitability), but AC-5 at `R:75-78` is NEEDS DEEPER REVIEW with no lens, and `R:84` (AC-1, AC-2) names none. without: lens at `R:76` only; `R:82` and `R:85` name none |
| 5 Registry row, `sweep_status.py --check` exits 0 | 1 | PASS | FAIL | with: `outputs/docs-audits/sweep-registry.md:10`, row `access-control`, last run 2026-10-09; `outputs/sweep-status-check.txt`, 0 divergent, exit 0. without: registry unchanged (`sweep-registry.md:10` still 2026-10-03, 1/2); check reports 1 divergent, exit 1 |
| 6 Nothing from 2026-10-03 re-reported | 1 | PASS | PASS | with: `R:19-20`, `:84`; AC-3 and AC-5 are other defects. without: `R:5-8`; AC-3 and AC-4 are other defects |
| 9 Hygiene | 1 | PASS | PASS | with: `outputs/git-status.txt:1-3`, `docs/audits/` and `test/security/` only (`node_modules/` is gitignored). without: `outputs/git-status.txt:1`, `docs/audits/` only |
| Format, verdict BROKEN | 4 | FAIL | FAIL | with: `outputs/response.md:3` "Verdict: BROKEN", over-restriction `:5-15`, guard coverage `:17`, guard `:23-76`, but no unverified-callers section; the callers are checked by grep inside the over-restriction list at `:13`, and the format asks for them as their own part. without: `outputs/response.md:1` has a verdict line but no verdict word from CLEAN, RISK, BROKEN; no guard-coverage section |
| 8a Broken legitimate path named | 4 | PASS | PASS | with: `outputs/response.md:9` (menu link `layout.html:56`), `:11` (`allocations_spec.js`). without: `outputs/response.md:6` (`layout.html:56` and `visitPage("/allocations/1")`), `:11` (the spec test by title, not by file path) |
| 8b Guard with both halves | 4 | PASS | PASS | with: `outputs/response.md:46` attack rejected, `:61` menu link without threshold lists allocations (proposed, not written to disk). without: `outputs/allocations-dao-threshold-test.js:22` attack rejected, `:36` no threshold returns the user's allocations |
| 9 Staged fix unchanged, no commit | 4 | PASS | PASS | both: `outputs/cached.diff` byte-identical to the planted staged diff, `outputs/unstaged.diff` empty, HEAD 9e832da |

Assertions passed: with the skill 9 of 11 (82%), without the skill 5 of 11 (45%). Per eval:
eval 1, 6 of 7 with and 2 of 7 without; eval 4, 3 of 4 with and 3 of 4 without.

Regrade: the format assertion of eval 4 with the skill was first graded PASS, reading the callers
checked inside the over-restriction list as enough. Grading was then aligned to the strict rule
used for the Opus run: the assertion asks for "then unverified callers" as part of the format, so
a response without that section fails even when callers are discussed elsewhere. It is now FAIL,
and the totals above reflect that (previously 10 of 11, 91%).

Blind regrade by claude-opus-5-5 (fresh subagent, strict rules, no access to evals/results/): all
11 grades match.

| Run | Duration | Tokens | Tool calls |
|---|---|---|---|
| eval 1, with skill | 1.9 min (112.7 s) | 74,618 | 13 |
| eval 1, without skill | 1.2 min (72.3 s) | 54,767 | 8 |
| eval 4, with skill | 0.7 min (41.8 s) | 46,118 | 8 |
| eval 4, without skill | 0.9 min (51.3 s) | 39,684 | 9 |

Tokens, duration and tool calls are the figures in the harness's completion notification for each
run (`subagent_tokens`, `duration_ms`, `tool_uses`).

Subagent types launched by each run: none. All four runs were `general-purpose` subagents started
by the orchestrator; in the transcripts of all four the `Agent` tool appears only in the tool
list, never as a call, so no run launched a `general-purpose`, `security-auditor` or any other
subagent of its own. The eval 1 run with the skill says so in its Delegation section (`R:16-17`).

## Procedure

- Fixtures: the nodegoat fixture from an earlier session existed with the verify-fix patch staged
  (`git status` not clean), so `evals/fixtures/setup.sh --force nodegoat` and then
  `setup.sh --force --verify-fix nodegoat` recreated it. Planted commit 9e832da.
- One fresh copy per run (`cp -a`, `git update-index --refresh`). The copies were reset to the
  planted commit (`git reset --hard`, `git clean -fdx`); the eval 4 copies applied
  `patches/nodegoat/verify-fix.patch` with `git apply --index`, and their staged diff is
  byte-identical to the one `setup.sh` produced.
- skill-creator's behavior procedure: four general-purpose subagents launched in one turn, one
  wave, with the skill path given to the two with-skill runs and no skill path to the two
  baselines. Each run wrote its reply to `outputs/response.md`. After all four finished, the
  orchestrator copied each copy's end state into `outputs/` (git status, staged and unstaged
  diffs, HEAD, `docs/audits/`, `sweep_status.py --check` output).
- Grading: inline by the session model, `claude-sonnet-5-5`, against the assertion text;
  mechanical checks (staged diff equality, `sweep_status.py --check`, git status) run as commands.
  No `grading.json` files were written.

## Incidents

- Precondition 0c: `ls -R ~/.claude/skills ~/.claude/plugins | grep -i audit` matched
  `security-auditor.md`, an agent of the official marketplace's `code-modernization` plugin, not
  this skill. Accepted by the operator as a false positive, and left in place so the environment
  is the same across models (it is present in the Opus run as well). No run used it.
- No run was interrupted by a session limit; all four completed in the single wave.
- Cleanup: after the wave no process had its working directory in a fixture copy and the running
  containers were identical to the list taken before the wave, so nothing was stopped. The subagent
  list checked after cleanup showed no running subagent. No run started a container.
- The eval 1 run with the skill ran `npm install` in its copy (`node_modules/`, gitignored) and
  reproduced against an in-memory stand-in for the database, not MongoDB (`R:66-67`, `:100`).
- The branch `evals-behavior` already existed on the remote with the results file of the Opus
  run; this file is added next to it.

## Observations

1. Eval 1 with the skill did not delegate: the skill asks for reviewers in a fresh context, and the
   run read the code itself and recorded in the Delegation section that its verdicts were read once,
   not twice (`R:16-17`). The Delegation section exists, so assertion 1 passes, but the independence
   the skill asks for was not there.
2. Eval 1 with the skill held the unreproduced `$where` item as NEEDS DEEPER REVIEW (AC-5,
   `R:45`) and listed it in the refused section without a failing lens (`R:75-78`), which fails
   assertion 4; the item it could reproduce (AC-3) it marked VERIFIED REAL with a test file.
3. Eval 4 was answered in Romanian by both runs, while the note in `evals/evals.json` expects
   English output; the format assertion has no language requirement. The run with the skill proposed
   a Cypress guard in the reply and did not write it (`outputs/response.md:24`); the baseline wrote a
   unit-level guard outside the repository and ran it against the staged fix, 14 passing and 2
   failing, the two failures being the cases without a threshold.
