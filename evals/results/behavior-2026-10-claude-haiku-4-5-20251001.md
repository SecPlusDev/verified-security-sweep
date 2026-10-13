# Behavior evaluation, `claude-haiku-4-5-20251001`, 2026-10

Evals 1 (`nodegoat-access-control-sweep`) and 4 (`nodegoat-verify-fix`) from `evals/evals.json`,
each run once with the skill and once without, on `claude-haiku-4-5-20251001` (the model of the
session that ran them; every message in the session transcript and in the five subagent
transcripts carries that model). Skill: `plugin/skills/defensive-audit-sweep` as in `main` 71e4f01
(plugin 1.2.0; `plugin/` has no diff between 71e4f01 and the branch the runs read it from), read
from the repository, not installed in the account. Evals 2 and 3 were not run.

## Results

Graded against the assertions of `evals/evals.json` as written: for eval 1, assertions 1 to 6 and
9 (hygiene, the seventh expectation); for eval 4, the format assertion, 8a, 8b and 9 (staged fix
unchanged). Strict reading: a required section that is absent fails, a range in place of an exact
`file:line` fails, assertion 5 requires `sweep_status.py --check` run on the copied
`docs/audits` with exit 0, and every grade is PASS or FAIL. Evidence paths are relative to
`outputs/<eval>-<with-skill|no-skill>/` in the evaluation directory; `R` is the report the run
wrote (`docs-audits/2026-10-09-access-control.md` with the skill,
`docs-audits/2026-10-09-access-control-follow-up.md` without), and `F` is the run's fixture copy
under `evals/fixtures/nodegoat-<eval>-<with-skill|no-skill>/`.

| Assertion | Eval | With skill | Without skill | Evidence |
|---|---|---|---|---|
| 1 Report and template sections | 1 | PASS INVALID | PASS | with: `R:3`, `:11`, `:17`, `:25`, `:134`, `:138` hold the six sections. without: `R:3`, `:6`, `:9`, `:16`, `:55`, `:32`; slug `access-control-follow-up` names the zone (the skill's `sweep_status.py` matches it to `access-control`) |
| 2 Exact `file:line`, chain of three | 1 | FAIL INVALID | FAIL | with: ranges at `R:35` (`allocations.js:11-31`, `allocations-dao.js:57-110`), `R:66-67` (`memos.js:11-33`, `memos-dao.js:15-35`), `R:99` (`index.js:66-69`). without: range at `R:19` (`allocations.js:16-18`) |
| 3 VERIFIED REAL with an existing reproduction test | 1 | FAIL INVALID | PASS | with: three VERIFIED REAL at `R:21-23`; the tests named at `R:58-60`, `:90-92`, `:120-122` are existing specs the report itself says do not detect the defect, and no test was written (`F`: `git status` shows only the report). without: AC-3 VERIFIED REAL at `R:13`; `R:25` names `allocations_access_control_spec.js`, which exists (`test/e2e/integration/allocations_access_control_spec.js:23` reproduces AC-3), although the same line calls the guard "missing" |
| 4 Refused candidates with the failing lens | 1 | PASS INVALID | FAIL | with: section at `R:134`, "None." (`R:136`), so no refused candidate lacks a lens. without: AC-4 refused at `R:56` with a reason and no lens |
| 5 Registry row, `sweep_status.py --check` exits 0 | 1 | FAIL INVALID | FAIL | both: `docs-audits/sweep-registry.md:10` unchanged, row `access-control` still declares 2026-10-03; `sweep_status.py --check --audits docs-audits` reports "registry text differs from reports", 1 divergent, exit 1 |
| 6 Nothing from 2026-10-03 re-reported | 1 | FAIL INVALID | FAIL | with: AC-1, closed in the 2026-10-03 report, reappears in Confirmed defects (`R:27-32`, also `R:20`); marked CONFIRMED FIXED, it is still re-reported. without: AC-1 reappears in Confirmed defects (`R:27-30`, also `R:12`), marked VERIFIED FIXED |
| 9 Hygiene | 1 | PASS INVALID | PASS | with: `F` HEAD 9e832da, `git status` shows only `?? docs/audits/2026-10-09-access-control.md`. without: `F` HEAD 9e832da, only `?? docs/audits/2026-10-09-access-control-follow-up.md` and `?? test/e2e/integration/allocations_access_control_spec.js` |
| Format, verdict BROKEN | 4 | FAIL | FAIL | with: `verify-fix-output.txt:4` "Verdict: BROKEN", but a preamble follows (`:6-11`), over-restriction (`:16`) comes before unverified callers (`:30`), and there is no proposed-guard section: `:48-63` proposes a rewrite of the fix instead; `summary.txt` opens with a preamble (`:1-25`). without: no verdict word from CLEAN, RISK, BROKEN; `summary.txt:122` gives the verdict as "the fix is safe and correct" (in Romanian), `:134` "SAFE TO COMMIT"; no unverified-callers or guard-coverage section |
| 8a Broken legitimate path named | 4 | FAIL | FAIL | with: `/allocations/1` without a threshold at `verify-fix-output.txt:25`, `:38`, but neither `app/views/layout.html` nor `allocations_spec.js` appears in any output file. without: `GET /allocations/123` without a threshold at `verify-fix-output.txt:72`, then judged harmless to UI users (`:75`, `summary.txt:65-71`); neither file is named |
| 8b Guard with both halves | 4 | PASS | FAIL | with: `guard-test.js:49` injection rejected, `:81` no threshold still returns allocations. without: every legitimate-path `it(...)` sets a threshold (`guard-test.js:113-204`), and `:60-75` treats an empty threshold as an attack |
| 9 Staged fix unchanged, no commit | 4 | PASS | PASS | both: `F` HEAD 9e832da; the staged tree (97355ab) equals HEAD with `patches/nodegoat/verify-fix.patch` applied; no unstaged or untracked change |

Eval 1 with the skill is INVALID as a with-skill measurement: the `Skill` call failed, `SKILL.md`
was read only in part (lines 1 to 199 of 230), and the report was written by a subagent that never
had the skill. Its grades stay in the table (3 of 7) but are left out of every with-skill figure.

Assertions passed, reported separately: eval 4, 2 of 4 (50%) with the skill and 1 of 4 (25%)
without; eval 1, without the skill, 3 of 7 (43%).

On Haiku the skill was not reliably applied even when its path was given; it is not recommended on
this model.

| Run | Duration | Tokens | Tool calls |
|---|---|---|---|
| eval 1, with skill | 4.4 min (264.3 s) | 50,689 | 28 |
| eval 1, with skill, its reviewer subagent | 2.1 min (128.8 s) | 48,351 | 25 |
| eval 1, without skill | 3.8 min (227.8 s) | 47,912 | 30 |
| eval 4, with skill | 6.0 min (362.8 s) | 48,190 | 27 |
| eval 4, without skill | 4.5 min (272.9 s) | 46,111 | 26 |

Tokens, duration and tool calls are the figures in the harness's completion notification for each
run (`subagent_tokens`, `duration_ms`, `tool_uses`). The notification for the eval 1 run with the
skill does not say whether its reviewer's figures are included.

Subagent types launched by each run, from the transcripts:

| Run | Subagents launched | Skill path given | `SKILL.md` read |
|---|---|---|---|
| eval 1, with skill | one `general-purpose` ("Run security audit following defensive-audit-sweep methodology") | yes | partly: lines 1 to 199 of 230 by the run; the reviewer that wrote the report was given a paraphrased brief, no skill path, and did not read it |
| eval 1, without skill | none | no | no |
| eval 4, with skill | none | yes | yes, whole file, then `references/verify-fix.md` |
| eval 4, without skill | none | no | no |

No run launched a `security-auditor` or any other subagent type.

## Procedure

- Fixtures: `evals/fixtures/setup.sh --force nodegoat`, copied twice with `cp -a` to
  `nodegoat-eval1-with-skill` and `nodegoat-eval1-no-skill`, then
  `setup.sh --force --verify-fix nodegoat`, copied twice to the two eval 4 copies. Planted commit
  9e832da. The copies live under `evals/fixtures/` in the repository (gitignored).
- Four `general-purpose` subagents launched by the orchestrator in one turn, one wave, with the
  skill path given to the two with-skill runs and an instruction not to use the skill given to the
  two baselines. Each run copied its own results into `outputs/<eval>-<with-skill|no-skill>/`
  (reports and tests for eval 1; `verify-fix-output.txt`, `guard-test.js` and `summary.txt` for
  eval 4). skill-creator's workspace layout (`iteration-N/<eval>/<with_skill|without_skill>/`) was
  not used.
- Grading: by `claude-opus-5-5`, in a separate session, from `outputs/` and the fixture copies,
  without reading the earlier grading; mechanical checks (`sweep_status.py --check` on the copied
  `docs-audits`, staged tree against the planted patch, `git status`) run as commands.

## Grading

The runs were made by `claude-haiku-4-5-20251001`; the grading in this file is by
`claude-opus-5-5`. The Haiku session graded its own runs first (`behavior-2026-10-haiku-4-5.md`);
that grading was replaced because it left out one assertion, used a PARTIAL grade, and did not
apply the strict reading used for the Opus and Sonnet runs.

## Incidents

- Precondition 0c: `ls -R ~/.claude/skills ~/.claude/plugins | grep -i audit` matched
  `security-auditor.md`, an agent of the official marketplace's `code-modernization` plugin, not
  this skill. A known false positive, the same as in the Opus and Sonnet runs, left in place. No
  run used it.
- The eval 1 run with the skill called the `Skill` tool for `defensive-audit-sweep`, which failed
  ("Unknown skill": the skill is not installed), then read `SKILL.md` from the path and delegated
  the audit to one `general-purpose` subagent without passing the skill on.
- The runs did not use skill-creator's workspace structure, and wrote no `response.md`, git status
  or diff captures; the end state was read from `outputs/` and from the fixture copies, which were
  still in place.
- No run issued a Docker command; the toolchain check in the orchestrator ran `docker ps` only.

## Observations

1. Neither eval 1 run updated the registry: both left `sweep-registry.md:10` at 2026-10-03, so
   `sweep_status.py --check` fails on both copies with the same divergence.
2. The eval 1 report with the skill was written by a subagent that never saw the skill; its
   refused-candidates section is empty and its verified findings name existing specs that, by the
   report's own text, do not reproduce them. The baseline wrote the one new reproduction test of
   the two runs.
3. Eval 4 with the skill reached BROKEN for the right reason (the threshold made mandatory) and
   proposed a two-sided guard, but missed the callers that hit the broken path (the menu link and
   the e2e spec) and proposed rewriting the fix, which `references/verify-fix.md` says not to do.
   The baseline judged the fix safe to commit.
