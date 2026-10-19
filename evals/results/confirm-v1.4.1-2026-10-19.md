# Confirmation run for v1.4.1, 2026-10-19

One run before tagging v1.4.1, whose changes are four scripts (two changed, one new, one fixed)
and three sentences of skill text: the plugin loaded with `--plugin-dir` from the clone at the
commit of pull request #12, in a configuration directory holding no other copy of the skill,
model `claude-opus-5-5`, on a clean copy of the planted-defects fixture (`7a07141`), with the
eval 5 prompt. Run by the owner on the owner's machine; graded from the scripts' output and
`git status`, as `evals/install-test.md` step 2 describes.

## Result: 8 of 9 assertions; the scripts behaved; one hygiene miss, answered in the text

| # | Assertion | Result |
|---|---|---|
| 1 | Bootstrap: `docs/audits/` with categories, registry and a dated report | PASS (and a coverage matrix) |
| 2 | Report with the zone slug and the template sections | PASS: `2026-10-19-api-key-scope.md` |
| 3 | Exact `file:line` and evidence chains; every cited line holds the code | PASS: 36 citations, 0 not OK |
| 4 | VERIFIED REAL findings with reproduction and run status | PASS: 3 of 3 |
| 5 | Every unconfirmed candidate carries a disposition | PASS: 4 refused entries, 0 problems |
| 6 | Registry row matches the report; `sweep_status.py --check` exit 0 | PASS |
| 7 | Tree differs only under `docs/audits/` and the test folders | **FAIL**: a 144 MB untracked copy of the whole project, `healthchecks-defects/`, left inside the working tree |
| 8 | `findings.jsonl` complete; `findings.py check` exit 0 | PASS: 3 entries at the planted lines (`views.py:415`, `:520`, `:495`) |
| 9 | Recorded commands use the project's test runner | PASS |

Recall against the ground truth: 3 of 3 planted defects, on their lines, with the planted
severities. `check_report.py`: 7 verification rows (3 VERIFIED REAL), 4 refused entries,
3 hand-off citations, 0 problems.

## What v1.4.1 changed, observed

- The run executed `leak_check.py` on its own at step 6 (the transcript holds the call) and
  finished with exit 0. Run again by hand from the plugin path: 7 files scanned, 136 values
  collected from 1,272 tracked files, 0 FAIL, 13 WARN. All 13 WARN were false: a 3-character
  placeholder in `docker/.env.example` matched every markdown table rule, and the 4-letter
  password of a test webhook URL matched the word in prose. Fixed the same evening in pull
  request #12 (sample dotenv files are not sources; a value needs 5 characters and a letter or
  digit); the result file above is from before that fix, the fix was re-run on the 13-report
  record of `real-code-2026-10-19.md` (36 values, 0 FAIL, 0 WARN).
- `check_citations.py` printed no masked row on this fixture (no credential-like line cited),
  and the three dotenv-aware changes did not alter its result on the 36 citations.
- `sweep_status.py` at bootstrap no longer reported a broken extraction.

## The hygiene miss

The run tried the fixes on a copy of the project to confirm that the reproductions turn green,
and put the copy inside the working tree. On 2026-10-13 the same run on the same fixture put it
outside. The skill text said nothing about where that copy goes; it now does (SKILL.md step 6:
a throwaway copy outside the repository, removed afterwards), together with the verify-fix
sentence from `real-code-2026-10-19.md`. Both sentences entered after this run and are not
confirmed by it; they are measured from the next round. The miss is not caused by any v1.4.1
change: the files that changed do not touch the fix-trial step.

## Decision

Tag v1.4.1. The changes it carries close a privacy gap seen in a real run (credential lines in
the transcript, nothing checking the deliverables), the scripts passed their own tests, CI on
three Python versions and the packaged archive, the method assertions that the changes could
affect (6, 8, the citation check) passed, and the one miss is model behavior on an untouched
step, answered by text that costs nothing if wrong. The full evaluation round (evals 1 to 7 on
Opus and Sonnet, the trigger loop unchanged since the description is unchanged) runs for v1.4.2,
which carries the external-review text and the eval with a planted hook.
