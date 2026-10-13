# Behavior evaluation, `claude-opus-5-5`, 2026-10

Evals 1 (`nodegoat-access-control-sweep`) and 4 (`nodegoat-verify-fix`) from `evals/evals.json`,
each run once with the skill and once without, on `claude-opus-5-5` (the model of the session that
ran and graded them). Skill: `plugin/skills/defensive-audit-sweep` at `main` 71e4f01 (plugin
1.2.0), read from the repository, not installed in the account. Evals 2 and 3 were not run.

## Results

Graded against the assertions of `evals/evals.json` as written: for eval 1, assertions 1 to 6 and
9 (hygiene, the seventh expectation); for eval 4, the format assertion, 8a, 8b and 9 (staged fix
unchanged). Evidence paths are relative to each run's directory in the evaluation workspace
(`iteration-1/<eval>/<with_skill|without_skill>/`); `R` is
`outputs/docs-audits/2026-10-09-access-control.md`, the report the run wrote.

| Assertion | Eval | With skill | Without skill | Evidence |
|---|---|---|---|---|
| 1 Report and template sections | 1 | PASS | FAIL | with: `R:3`, `:24`, `:65`, `:84`, `:173`, `:209` hold the six sections. without: no Delegation section (headings `R:3`, `:14`, `:21`, `:40`, `:49`, `:124`, `:143`, `:148`); refused section titled "Verified and refused, or unconfirmed" (`R:124`) |
| 2 Exact `file:line`, chain of three | 1 | PASS | FAIL | with: `R:87`, `:107`, `:125`, `:146` single lines, chains at `R:90-97`, `:110-115`, `:127-134`, `:148-153`. without: ranges at `R:52` (`allocations.js:16-23`) and `R:71` (`allocations-dao.js:77-79`), no line at `R:116`, one-sentence chain at `R:73-74` |
| 3 VERIFIED REAL with an existing reproduction test | 1 | PASS | FAIL | with: `R:69-72`; tests named at `R:103`, `:121`, `:141`, `:159` exist (`outputs/git-status.txt:4-5`). without: five VERIFIED REAL at `R:43-47`, none names a test, `outputs/git-status.txt:1-3` has no test file |
| 4 Refused candidates with the failing lens | 1 | FAIL | FAIL | with: lens named at `R:180`, `:184`, `:186`, but `R:189` (HttpOnly) names none in the section; its lens is only in the Verification table (`R:77`). without: reasons, no lens, `R:126-141` |
| 5 Registry row, `sweep_status.py --check` exits 0 | 1 | PASS | PASS | both: `outputs/docs-audits/sweep-registry.md:10`, row `access-control`, last run 2026-10-09; `outputs/sweep-status-check.txt`, 0 divergent, exit 0 |
| 6 Nothing from 2026-10-03 re-reported | 1 | PASS | PASS | with: `R:18-22`; AC-3 to AC-6 are other defects. without: `R:36-37`, `:140-141`; AC-7 (`R:115`) is a test gap on the AC-1 guard, not AC-1 |
| 9 Hygiene | 1 | PASS | PASS | with: `outputs/git-status.txt:1-5`, `docs/audits/` and `test/e2e/integration/` only. without: `outputs/git-status.txt:1-3`, `docs/audits/` only |
| Format, verdict BROKEN | 4 | PASS | FAIL | with: `outputs/response.md:3` "Verdict: BROKEN.", callers `:36-43`, over-restriction `:51`, guard coverage `:55`, guard `:59`. without: `outputs/response.md:3` "Verdict: nu-l comite așa", no verdict word, no unverified-callers or guard-coverage section |
| 8a Broken legitimate path named | 4 | PASS | PASS | with: `outputs/response.md:10`, `:29-32`, `:53`. without: `outputs/response.md:20`, `:30` |
| 8b Guard with both halves | 4 | PASS | PASS | with: `outputs/response.md:84`, `:94` attack, `:102` no threshold. without: `outputs/repo-files/test/unit/allocations_threshold_guard_test.js:67` attack, `:78` no threshold |
| 9 Staged fix unchanged, no commit | 4 | PASS | PASS | both: `outputs/cached.diff` byte-identical to the planted staged diff, `outputs/unstaged.diff` empty, HEAD 9e832da |

Assertions passed: with the skill 10 of 11 (91%), without the skill 6 of 11 (55%). Per eval:
eval 1, 6 of 7 with and 3 of 7 without; eval 4, 4 of 4 with and 3 of 4 without. skill-creator's
`aggregate_benchmark.py` averages the two per-eval rates instead and reports 93% and 59%.

| Run | Duration | Tokens | Tool calls |
|---|---|---|---|
| eval 1, with skill | 5.1 min (303.6 s) | 103,940 | 28 |
| eval 1, without skill | 3.3 min (197.0 s) | 78,877 | 21 |
| eval 4, with skill | 1.9 min (113.8 s) | 62,360 | 13 |
| eval 4, without skill | 2.0 min (118.2 s) | 53,160 | 16 |

Tokens, duration and tool calls are the figures in the harness's completion notification for each
run. The eval 1 run with the skill delegated to two reviewers (`R:24-39`); the notification does
not say whether their tokens are included.

## Procedure

- Fixtures: `evals/fixtures/setup.sh nodegoat`, then `setup.sh --verify-fix nodegoat`, both on a
  new clone (no fixture existed before). Planted commit 9e832da.
- One fresh copy per run (`cp -a`, `git update-index --refresh`). `--verify-fix` stages the patch
  in the fixture itself, so the eval 1 copies were reset to the planted commit
  (`git reset --hard`, `git clean -fdx`) and the eval 4 copies applied
  `patches/nodegoat/verify-fix.patch` with `git apply --index`; their staged diff is
  byte-identical to the one `setup.sh` produced.
- skill-creator's behavior procedure: four general-purpose subagents launched in one turn, one
  wave, with the skill path given to the two with-skill runs and no skill path to the two
  baselines. Each run wrote its reply to `outputs/response.md`. After all four finished, the
  orchestrator copied each copy's end state into `outputs/` (git status, staged and unstaged
  diffs, HEAD, `docs/audits/`, new and changed files, `sweep_status.py --check` output).
- Grading: inline by the session model, `claude-opus-5-5`, against the assertion text, with
  `grading.json` per run in skill-creator's schema; mechanical checks (staged diff equality,
  `sweep_status.py --check`, git status) run as commands.

## Incidents

- Precondition 0c: `ls -R ~/.claude/skills ~/.claude/plugins | grep -i audit` matched
  `security-auditor.md`, an agent of the official marketplace's `code-modernization` plugin, not
  this skill. Accepted by the operator as a false positive before the wave.
- No run was interrupted by a session limit; all four completed in the single wave.
- Cleanup: after the wave no process had its working directory in a fixture copy and no container
  had appeared (running containers identical to the list taken before the wave), so nothing was
  stopped. The eval 1 runs report starting and removing their own MongoDB containers
  (with skill: `acsweep-20261009-mongo`, app on port 4399). The subagent list checked after
  cleanup showed no running subagent.
- The eval 1 baseline reports that `scripts/sweep_status.py`, which the planted registry names,
  does not exist in the fixture (it ships with the skill), and updated the registry row by hand.
- `aggregate_benchmark.py` labels the benchmark "3 runs each per configuration"; each
  configuration ran once.

## Observations

1. Eval 4 with the skill answered in Romanian, the language of the prompt, with Romanian section
   headings except "Over-restriction" (`outputs/response.md:51`). The note in `evals/evals.json`
   expects the output in English; the format assertion does not require a language, so it was
   graded PASS.
2. Eval 1 with the skill put the lens for each refused candidate in the Verification table
   (`R:74-78`) and repeated it in the refused section for three of the four refused candidates;
   the HttpOnly item (`R:189`) lost it in the refused section, which fails assertion 4. The same
   section also lists entries that are not candidates of this run (AC-1 bypass "none found",
   `R:190`; AC-2, `R:192`).
3. Both eval 1 runs reproduced their findings live over HTTP against a local MongoDB container,
   but neither executed a test: the run with the skill wrote two Cypress specs and states they were
   not run because Cypress is not installed (`R:168-171`); the baseline wrote no test file. The
   eval 4 baseline wrote and ran a unit-level guard (`node --test` with a shim) and placed it in
   the fixture as an untracked file, which the staged-state assertion allows.
