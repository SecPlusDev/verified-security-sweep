# Round v1.2.3: targeted rerun, graded

This file records the grading of round v1.2.3 of the skill at plugin version 1.2.3 (`main` at
`5087d28`). The round is a targeted rerun: 8 runs, all with the skill, on evals 1 and 5 only, on
`claude-sonnet-5-5` (eval 1 x3, eval 5 x3) and `claude-opus-5-5` (eval 1 x1, eval 5 x1). One
orchestrator session ran each model, and each has its own manifest. The grading covers the
assertions of `evals/evals.json` for evals 1 and 5, a blind finding-quality score for both evals,
and the criteria B1 to B5 of round v1.2.2, with B5 measured against the v1.2.2 runs without the
skill. Only the measurements are reported, with no interpretation beyond the criteria.

Path prefixes in this file and in `round-v1.2.3/`:
- `<opus-round>` is the Opus round directory of v1.2.3 and `<sonnet-round>` the Sonnet one.
- `<grading>` is the grading working directory.
- Paths in the repository are given relative to its root.

## Procedure

The grading session ran on `claude-opus-5-5` and applied the procedure of round v1.2.2. Every
sub-agent ran on `claude-opus-5-5` in a fresh context and received only what its step lists
below. The grader did not run the skill and did not start any application, server, database or
container.

0. **Preparation.**
   - Read `docs/BUILD.md` sections 3 and 5, `evals/evals.json` and both round manifests.
   - Located the 8 runs to grade, each with its `outputs/`:
     - Sonnet v1.2.3: `<sonnet-round>/runs/eval1-with_skill-{1,2,3}/outputs/` and
       `<sonnet-round>/runs/eval5-with_skill-{1,2,3}/outputs/`;
     - Opus v1.2.3: `<opus-round>/runs/eval1-with_skill-1/outputs/` and
       `<opus-round>/runs/eval5-with_skill-1/outputs/`.
   - Every run received the skill path and read `SKILL.md` (both manifests, "SKILL.md read"), so
     no run is invalid.
   - Checked the reference code, read-only:
     - `<opus-round>/base/nodegoat` at `9e832da`, clean;
     - `<opus-round>/base/healthchecks-defects` at `7a07141`, clean.
   - Created branch `evals-round-v1.2.3` from `main`.
1. **Assertions.** Two sub-agents ran in parallel, one per eval, with 4 runs each. Each received:
   - the eval's prompt and assertion text from `evals.json`;
   - the Grading paragraph of `docs/BUILD.md` section 5;
   - the `outputs/` paths and working copies of its runs;
   - the path of the reference code.

   The rules were those of v1.2.2:
   - PASS or FAIL only.
   - A required section that is missing fails, even if its content appears elsewhere.
   - Every line cited by a confirmed finding is opened in the reference code. A line that does not
     exist or does not hold the cited code fails the cited-lines assertion (2 for eval 1, 3 for
     eval 5).
   - Every grade carries its evidence as `path:line`.
   - Every entry in a refused or unconfirmed section needs one of the three allowed dispositions.

   One rule was given to the graders in writing that was an orchestrator adjustment in v1.2.2: a
   cited line holds the cited code only if that physical line contains it. A line of a multi-line
   statement whose cited element is on another line does not hold it (see "Strict readings").
   The graders also listed every cited line that does not exist or does not hold the cited code,
   in confirmed and unconfirmed findings, with its kind.
2. **Finding quality, blind.** This step covered the 8 runs.
   1. **Blinding and extraction.**
      - Letters were assigned to runs with `random.shuffle` in `python3`, per eval.
      - Each run's dated report, its `coverage-matrix.md` where present and its final reply were
        copied under the run's letter. Run paths, run names and model names were redacted in the
        copies.
      - The mapping was moved out of the grading directory until step 3.
      - One fresh sub-agent per eval read the copies and wrote a neutral list per letter:
        - the claim in one sentence, with none of the skill's vocabulary and none of its format;
        - the cited `file:line`;
        - the status: "confirmed" or "unconfirmed".
   2. **Grading.**
      - One fresh sub-agent per eval received the reference code, the ground truth and the lists.
        It did not receive the mapping, the extraction notes or the reports.
        - Eval 5: `evals/ground-truth/healthchecks-api-planted.md`.
        - Eval 1: `evals/ground-truth/nodegoat-access-control.md`, including its closing
          correction.
      - For each claim it recorded:
        - REAL, NOT REAL or UNDECIDED, with a reason;
        - whether the claim is in the zone;
        - for REAL claims, whether the location line holds the defect, and the matching P-n,
          GT-n or ADJ-n entry, or "outside GT".
      - The stop rule was more than 2 UNDECIDED in one eval. Both evals had 0.
3. **Metrics and criteria.**
   - The mappings were opened only after step 2.
   - B1 to B5 were computed over the 8 runs. The v1.2.2 figures in the combined table are taken
     from `round-v1.2.2.md` and `round-v1.2.2/`.
   - Where a rule was ambiguous, the stricter reading was applied and the ambiguity is recorded.
4. **This file and the artifacts.**

## Assertions

`n/m` counts runs that pass. The totals count assertion grades. Per-run grades and evidence are in
`round-v1.2.3/assertions-eval<n>.json`. No orchestrator adjustment was applied in this round.
`R` is the run's dated report under `outputs/docs-audits/`.

### Eval 1 (`nodegoat-access-control-sweep`)

| Assertion | Opus with skill | Sonnet with skill |
|---|---|---|
| 1 Report, template sections | 1/1 | 3/3 |
| 2 Exact file:line, chain of three, cited lines hold the code | 0/1 | 1/3 |
| 3 VERIFIED REAL with existing test and run status | 1/1 | 3/3 |
| 4 Unconfirmed candidates with disposition | 1/1 | 0/3 |
| 5 Registry row, `--check` exits 0 | 1/1 | 3/3 |
| 6 No re-report of AC-1, AC-2 | 1/1 | 3/3 |
| 7 Hygiene | 1/1 | 3/3 |
| Total | **6/7 (86%)** | **16/21 (76%)** |

The FAIL grades:
- **Assertion 2.**
  - Opus run 1:
    - the location `app/routes/allocations.js:18` (`R:56`) holds `} = req.params;`, and the
      cited `userId` is on line 17;
    - chain lines `app/data/allocations-dao.js:82` (`R:61`), which holds
      `userId: parsedUserId`, not `{ userId: parseInt(userId) }`;
    - `app/data/allocations-dao.js:97` (`R:62`), which holds `userName` only;
    - `app/routes/session.js:27` (`R:98`), which is inside `isAdminUserMiddleware`, while the
      `isLoggedIn` check cited is on line 37.
  - Sonnet run 1: chain lines `app/routes/allocations.js:18` (`R:42`) and
    `app/data/allocations-dao.js:58` (`R:44`), which holds `parseInt(userId)` and no query.
  - Sonnet run 2: chain line `app/routes/allocations.js:18` (`R:34`).
  - Sonnet run 3 passes. It cites the destructuring as `app/routes/allocations.js:16`-`18`
    (`R:36`) in the chain, and its location is `app/routes/allocations.js:23` (`R:32`).
- **Assertion 4, Sonnet runs 1 to 3.** Entries in the refused section carry no allowed
  disposition:
  - run 1: `R:73`;
  - run 2: `R:59`, `R:63`, `R:65`;
  - run 3: `R:72`, `R:75`. `R:60` also calls AC-2 closed without citing the earlier report.

### Eval 5 (`healthchecks-api-planted-defects`)

| Assertion | Opus with skill | Sonnet with skill |
|---|---|---|
| 1 Bootstrap: categories, registry, report | 1/1 | 3/3 |
| 2 Report, API zone slug, template sections | 1/1 | 3/3 |
| 3 Exact file:line, chain of three, cited lines hold the code | 0/1 | 1/3 |
| 4 VERIFIED REAL with existing test and run status | 1/1 | 3/3 |
| 5 Unconfirmed candidates with disposition | 1/1 | 0/3 |
| 6 Registry row, `--check` exits 0 | 1/1 | 3/3 |
| 7 Hygiene | 1/1 | 3/3 |
| Total | **6/7 (86%)** | **16/21 (76%)** |

The FAIL grades:
- **Assertion 3.**
  - Opus run 1: chain lines `hc/api/models.py:475` (`R:97`), cited for `ping_url` and
    `update_url`, which holds `ping_url` only; `hc/api/models.py:474` (`R:118`), cited for six
    fields, which holds `uuid` only.
  - Sonnet run 2: chain line `templates/docs/api.md:51` (`R:38`), cited as the docs list that
    excludes delete for read-only keys. The line is the sentence on creating keys; the list is at
    lines 56 to 62.
  - Sonnet run 3: chain line `hc/api/views.py:482` (`R:53`), cited for the
    `check.project_id != request.project.id` comparison, which is on line 483.
- **Assertion 5, Sonnet runs 1 to 3.** One entry each in the refused section carries a reason but
  no allowed disposition:
  - run 1: `R:116-119`, "checked, no defect";
  - run 2: `R:89-91`, "refused, by design" with no lens;
  - run 3: `R:75`, "performance only, outside this zone's scope".

### Totals over evals 1 and 5

| Model | With skill |
|---|---|
| `claude-opus-5-5` | 12/14 (86%) |
| `claude-sonnet-5-5` | 32/42 (76%) |

### Cited lines that do not exist or do not hold the cited code

All 8 runs are listed. The graders opened 113 cited lines in eval 1 and 180 in eval 5. No cited
line that does not exist was found in any run. Kind "other" is a line cited outside the location
and the chain, for example in the fix approach or in a candidate's text.

| Run | Finding (status, kind) | Report line | Cited | Problem |
|---|---|---|---|---|
| opus/eval1-with_skill-1 | AC-3 (confirmed, location) | `R:56` | `app/routes/allocations.js:18` | does not hold the cited code (`userId` is on :17) |
| opus/eval1-with_skill-1 | AC-3 (confirmed, chain) | `R:61` | `app/data/allocations-dao.js:82` | does not hold the cited code (`userId: parsedUserId`; `parseInt` is on :58) |
| opus/eval1-with_skill-1 | AC-3 (confirmed, chain) | `R:62` | `app/data/allocations-dao.js:97` | does not hold the cited code (`firstName`, `lastName` are on :98-99) |
| opus/eval1-with_skill-1 | AC-4 (confirmed, chain) | `R:98` | `app/routes/session.js:27` | does not hold the cited code (`isAdminUserMiddleware`; the `isLoggedIn` check is on :37) |
| opus/eval1-with_skill-1 | AC-3 (confirmed, other) | `R:73-74` | `app/routes/profile.js:16`, `app/routes/contributions.js:15`, `app/routes/memos.js:23` | do not hold the cited code (`} = req.session;`; `userId` is on the line before) |
| opus/eval1-with_skill-1 | profile update candidate (unconfirmed, other) | `R:131` | `app/data/profile-dao.js:45` | does not hold the cited code (`const user = {};`, no `$set`) |
| opus/eval1-with_skill-1 | profile update candidate (unconfirmed, other) | `R:132` | `app/routes/profile.js:80` | does not hold the cited code (`userId` is on :79) |
| sonnet/eval1-with_skill-1 | AC-3 (confirmed, chain) | `R:42` | `app/routes/allocations.js:18` | does not hold the cited code (`userId` is on :17) |
| sonnet/eval1-with_skill-1 | AC-3 (confirmed, chain) | `R:44` | `app/data/allocations-dao.js:58` | does not hold the cited code (no query; the criterion is on :82) |
| sonnet/eval1-with_skill-1 | AC-3 (confirmed, other) | `R:51` | `app/routes/profile.js:15`, `app/routes/contributions.js:14` | do not hold the cited code (`req.session` is on the next line) |
| sonnet/eval1-with_skill-1 | profile/contributions candidate (unconfirmed, other) | `R:74` | `app/routes/profile.js:15`, `:79`, `app/routes/contributions.js:14` | do not hold the cited code (`req.session` is on the next line) |
| sonnet/eval1-with_skill-2 | AC-3 (confirmed, chain) | `R:34` | `app/routes/allocations.js:18` | does not hold the cited code (`userId` is on :17) |
| sonnet/eval1-with_skill-2 | AC-3 (confirmed, other) | `R:45` | `app/views/allocations.html:15` | does not hold the cited code (`{{userId}}` there is the URL parameter, not the session id) |
| sonnet/eval1-with_skill-2 | profile/contributions/dashboard candidate (unconfirmed, other) | `R:64` | `app/routes/profile.js:16`, `app/routes/contributions.js:15` | do not hold the cited code (`userId` is on the line before) |
| sonnet/eval1-with_skill-3 | AC-3 (confirmed, other) | `R:45` | `app/routes/profile.js:16`, `app/routes/contributions.js:15` | do not hold the cited code (`userId` is on the line before) |
| sonnet/eval1-with_skill-3 | AC-4 (unconfirmed, other) | `R:62` | `app/data/memos-dao.js:18` | does not hold the cited code (`const memos = {`; `memo`, `timestamp` are on :19-20) |
| sonnet/eval1-with_skill-3 | profile/contributions candidate (unconfirmed, other) | `R:73` | `app/routes/profile.js:16`, `:80`, `app/routes/contributions.js:15`, `:44` | do not hold the cited code (`userId` is on the line before) |
| opus/eval5-with_skill-1 | F2 (confirmed, chain) | `R:97` | `hc/api/models.py:475` | does not hold the cited code (`update_url` is on :479-480) |
| opus/eval5-with_skill-1 | F3 (confirmed, chain) | `R:118` | `hc/api/models.py:474` | does not hold the cited code (`uuid` only; the other fields are on :475-483) |
| opus/eval5-with_skill-1 | R4 (unconfirmed, chain) | `R:149` | `hc/accounts/models.py:592` | does not hold the cited code (`hmac.digest`; `compare_digest` is on :593) |
| sonnet/eval5-with_skill-2 | A1 (confirmed, chain) | `R:38` | `templates/docs/api.md:51` | does not hold the cited code (the list is at :56-62) |
| sonnet/eval5-with_skill-3 | F2 (confirmed, chain) | `R:53` | `hc/api/views.py:482` | does not hold the cited code (`get_object_or_404`; the comparison is on :483) |

Sonnet eval1-with_skill-3 also cites `app/routes/contributions.js:177` and
`app/routes/research.js:211` in its registry diff, not in the report. These were not graded.

## Finding quality

Definitions, as in v1.2.2:
- **Confirmed:** the claims the report asserts as defects.
- **Precision:** REAL / confirmed.
- **Recall on GT:** ground-truth entries found by a confirmed REAL claim. The denominator is 2 for
  eval 1 (GT-1, GT-2) and 3 for eval 5 (P-1, P-2, P-3).
- **Exact lines:** confirmed REAL claims whose location line holds the defect.
- **Unconfirmed (REAL):** all unconfirmed claims, with the number graded REAL in brackets.

Blind grading verdicts: eval 1, 66 claims (35 REAL, 31 NOT REAL, 0 UNDECIDED); eval 5, 43 claims
(12 REAL, 31 NOT REAL, 0 UNDECIDED).

| Run | Letter | Confirmed | REAL | NOT REAL | Precision | Recall on GT (confirmed) | GT found only unconfirmed | Exact lines | Unconfirmed (REAL) | Confirmed REAL outside GT |
|---|---|---|---|---|---|---|---|---|---|---|
| opus/eval1-with_skill-1 | B | 2 | 2 | 0 | 1.00 | 2/2 (GT-1, GT-2) | none | 2/2 | 15 (7) | none |
| sonnet/eval1-with_skill-1 | C | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 15 (8) | none |
| sonnet/eval1-with_skill-2 | A | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 17 (8) | none |
| sonnet/eval1-with_skill-3 | D | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 14 (7) | none |
| opus/eval5-with_skill-1 | A | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 15 (0) | none |
| sonnet/eval5-with_skill-1 | C | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 4 (1) | none |
| sonnet/eval5-with_skill-2 | B | 2 | 2 | 0 | 1.00 | 2/3 (P-1, P-2) | none | 2/2 | 9 (0) | none |
| sonnet/eval5-with_skill-3 | D | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 4 (0) | none |

Location details:
- The blind grader found the location line of every confirmed REAL claim on its defect. For the
  eval 1 claims at `app/routes/allocations.js:18` (B-1) and `:23` (A-1, C-1, D-1), it graded the
  location against the defect (the route takes the id from the path), not against the cited
  token, which is the assertion grader's check.
- In eval 1, GT-2 (session fixation) is confirmed in B and handed off without a verdict in A, C
  and D (A-15, C-15, D-13), where it is graded REAL as an unconfirmed claim.
- No confirmed claim in eval 1 re-reports AC-1 or AC-2. Four unconfirmed claims describe the AC-2
  redirect (A-3, B-5, C-8, D-3); they are graded NOT REAL, since the ground truth closes AC-2 as
  informational.
- In eval 5, letter B has no claim matching P-3, confirmed or unconfirmed.

## Criteria

The criteria are those of v1.2.2, computed over the 8 runs of v1.2.3. This round has no eval 4
run, so B1 rests on assertion 7 alone.

| Criterion | Result |
|---|---|
| B1 Nothing outside `docs/audits` and test folders changes | **PASS** |
| B2 Zero confirmed findings graded NOT REAL | **PASS** |
| B3 Zero cited lines that do not exist; zero location lines of confirmed findings that do not hold the cited code | **FAIL** |
| B4 Eval 5: `docs/audits` created (categories, registry, report) and `sweep_status --check` exits 0, in all 4 runs | **PASS** |
| B5 Eval 5, per model: mean recall on P-1..P-3 (confirmed) with skill in v1.2.3 >= without skill in v1.2.2 | **FAIL** (Opus PASS, Sonnet FAIL) |

**B1, PASS.**
- Assertion 7 passes in all 8 runs. `outputs/git-status.txt` and `outputs/changed-files.txt`
  list only `docs/audits/` and test files. `__pycache__` and `.venv` are gitignored.
- `outputs/head.txt` is the base commit in every run, and `outputs/staged.diff` is empty.

**B2, PASS.**
- The 8 runs have 16 confirmed claims, all REAL (`quality-per-run.json`).

**B3, FAIL.**
- **First clause.** No cited line that does not exist was found, by the assertion graders or by
  `check_citations.py` on the final reports (next section).
- **Second clause.** opus/eval1-with_skill-1 has a location line of a confirmed finding that does
  not hold the cited code: `app/routes/allocations.js:18` (`R:56`), cited as "where `userId` is
  taken from `req.params`". The line holds `} = req.params;`, and `userId` is on line 17. This
  entry rests on the physical-line rule (see "Strict readings"). Under a reading that accepts a
  line of the same statement, no run fails B3.
- **Recorded, not counted by B3's text:** the chain and "other" lines in the table above, in
  confirmed and unconfirmed findings.

**B4, PASS.**
- Assertion 1 passes in all 4 eval 5 runs. `outputs/docs-audits/` holds `categories.md`,
  `sweep-registry.md` and a dated report.
- `outputs/sweep-status-check.txt` ends with `exit code: 0` in all 4. The assertion grader re-ran
  the check on each copy and got exit 0.

**B5, FAIL.** Recall on P-1..P-3 from confirmed REAL claims, against the v1.2.2 runs without the
skill:

| Model | With skill, v1.2.3 | Mean | Without skill, v1.2.2 (runs 1, 2) | Mean | Result |
|---|---|---|---|---|---|
| `claude-opus-5-5` | 3/3 (run 1) | 1.00 | 3/3, 3/3 | 1.00 | PASS |
| `claude-sonnet-5-5` | 3/3, 2/3, 3/3 (runs 1, 2, 3) | 0.89 | 3/3, 3/3 | 1.00 | FAIL |

- P-3 is missing from sonnet/eval5-with_skill-2 (letter B).
- No planted defect was found only as an unconfirmed claim in any eval 5 run.

### Combined table

Clean runs / total runs, per criterion and model. A run is clean on a criterion when nothing in
that run fails it:
- B1: assertion 7 passes, and for eval 4 the staged diff equals the patch with no commit.
- B2: no confirmed claim graded NOT REAL. Counted on evals 1 and 5.
- B3: no cited line that does not exist and no location line of a confirmed finding that does not
  hold the cited code. Counted on evals 1 and 5.
- B4: eval 5 runs with categories, registry and report, and `--check` exit 0.
- B5: eval 5 runs with recall 3/3 on P-1..P-3 (the without-skill mean is 1.00 on both models).

v1.2.2 counts the 16 runs with the skill of that round (per model: eval 1 x3, eval 4 x2,
eval 5 x3); v1.2.3 counts the 8 runs of this round.

| Criterion | Model | v1.2.2 | v1.2.3 | Combined |
|---|---|---|---|---|
| B1 | `claude-opus-5-5` | 8/8 | 2/2 | 10/10 |
| B1 | `claude-sonnet-5-5` | 8/8 | 6/6 | 14/14 |
| B2 | `claude-opus-5-5` | 6/6 | 2/2 | 8/8 |
| B2 | `claude-sonnet-5-5` | 6/6 | 6/6 | 12/12 |
| B3 | `claude-opus-5-5` | 6/6 | 1/2 | 7/8 |
| B3 | `claude-sonnet-5-5` | 4/6 | 6/6 | 10/12 |
| B4 | `claude-opus-5-5` | 3/3 | 1/1 | 4/4 |
| B4 | `claude-sonnet-5-5` | 3/3 | 3/3 | 6/6 |
| B5 | `claude-opus-5-5` | 3/3 | 1/1 | 4/4 |
| B5 | `claude-sonnet-5-5` | 2/3 | 2/3 | 4/6 |

## check_citations.py

The runs' own calls are read from the run transcripts: Bash calls that execute
`scripts/check_citations.py` on the run's new report, and their results. Details per run are in
`round-v1.2.3/check-citations-runs.json`.

- **8 of 8 runs ran `check_citations.py` themselves** on their new report, 1 to 3 times each.
- **First call:**
  - 4 runs reported 0 not OK: opus/eval1-1 (40 citations), opus/eval5-1 (69), sonnet/eval1-1
    (31), sonnet/eval5-2 (25).
  - 4 runs reported citations not OK, all `OUT OF RANGE` (a line past the end of the file):
    - sonnet/eval1-2: 1 of 23, exit 1;
    - sonnet/eval1-3: 10 of 30, exit 1;
    - sonnet/eval5-1: 3 of 50;
    - sonnet/eval5-3: 2 of 34, exit 1.
- **Last call:** all 4 of those runs reached 0 not OK, or exit 0 with the output discarded
  (sonnet/eval5-1).
- **Orchestrator call after each run** (`outputs/check-citations.txt`): every new report gives
  0 not OK, exit 0, and the other new files of eval 5 give "no file:line citations found",
  exit 0.
- The script checks that each cited line exists. It does not check that the line holds the cited
  code, so the entries in the cited-lines table above are not reported by it.

## Strict readings and ambiguities

- **Physical-line rule, given to the graders.** In v1.2.2 this reading was an orchestrator
  adjustment on one run (Sonnet eval 1 run 1, location `allocations.js:17`). In v1.2.3 it was a
  written rule for every cited line, location and chain. It decides:
  - eval 1 assertion 2 for Opus run 1 (`allocations.js:18` as location) and Sonnet runs 1 and 2
    (the same line in the chain);
  - eval 5 assertion 3 for Opus run 1 (`models.py:474`, `:475` cited for several fields);
  - B3 for Opus eval 1 run 1.

  Under a reading that accepts a line of the same statement:
  - eval 1, Sonnet run 2 would pass assertion 2. Sonnet run 1 would still fail on
    `allocations-dao.js:58`, and Opus run 1 on `allocations-dao.js:82`, `:97` and `session.js:27`.
  - eval 5, Opus run 1 would pass assertion 3. Sonnet runs 2 and 3 fail on lines that do not hold
    the cited code under either reading.
  - B3 would pass.

  In v1.2.2 the graders had no such rule for chain lines, so the cited-lines grades of the two
  rounds were not made under the same written rule.
- **Eval 1 grader's calls.**
  - A line that opens an object literal or defines a function was accepted when the claim
    describes the construct as a whole. It was flagged only when a token quoted by the claim sits
    on another line: `memos-dao.js:18` (Sonnet run 3) and `profile-dao.js:45` (Opus run 1).
  - In assertion 4, an entry that names a lens without the word "refused" was accepted as refused
    with that lens. An entry with neither a lens, nor "needs deeper review", nor "closed earlier"
    with the report cited was failed.
  - Assertion 2 covers the location and the evidence chain. Lines in the fix approach, the context
    or the candidates are listed but do not decide it.
- **Eval 5 grader's calls.**
  - In assertion 5, "checked, no defect", "by design" and "performance only, outside scope" are
    not allowed dispositions. A lenient reading would pass Sonnet run 1 at least.
  - A loop or condition header cited for "the filter", and `def compare_api_key` cited for its
    comparison, were accepted as holding the cited construct.
- **Blind grader's calls.**
  - Eval 1: AC-2 claims are NOT REAL per the ground truth. Memos without an owner and the public
    `/tutorial` are NOT REAL as "examined and not included". Cookie claims A-17 and C-16 are REAL
    against ADJ-3 for `secure` and `maxAge`, with the `httpOnly` part false per the correction.
    ADJ-n entries are out of the zone.
  - Eval 5: claims on the key lookup in `hc/accounts/models.py` count in the zone. Ping, callback,
    metrics and Prometheus endpoints count out of the zone.
- **Extraction status.** Calls on borderline confirmed or unconfirmed status are recorded in
  `extraction-notes-eval<n>.json`. Among them:
  - Session fixation is confirmed in eval 1 letter B and handed off without a verdict in A, C and
    D.
  - C-3 in eval 5 stays confirmed although its verified severity was lowered from High to Medium.
- **B1 scope.** No eval 4 run in this round, so B1 is assertion 7 over the 8 runs.
- **B3 scope.** As in v1.2.2, the second clause names location lines only.
- **B5 baseline.** The baseline is the v1.2.2 runs without the skill (Opus 1.00, Sonnet 1.00). No
  run without the skill was made in v1.2.3.
- **Combined table, B5.** A run is counted clean at recall 3/3, since both baseline means are 1.00.

## Incidents from the manifests

From the Sonnet manifest:
1. A first orchestrator command failed with a zsh parse error before running anything. It was
   rewritten as `evidence.sh`. No run was affected.
2. After each wave: no process with its working directory under the runs, no Xvfb or runserver,
   containers identical to the recorded list, and no Monitor, background call or `/tmp/` path in
   any run's tool inputs. No process, container or task was stopped.
3. No run used docker or started a server. The eval 1 runs had no `node_modules` or MongoDB, so
   their reproduction tests use stubs. Run 1 left a `describe`/`it` shim and stubs in its `.tmp`
   directory.
4. The eval 5 runs used the base `.venv` copied with `cp -a`. eval5-with_skill-3 ran its test with
   `DB_NAME` set to a SQLite path in its `.tmp` directory. Each run has one `__pycache__` file in
   `changed-files-not-copied.txt`.
5. An old, gitignored `__pycache__` under the skill's `scripts/` in the repository was left
   untouched.
6. Final reports reached the orchestrator as agent messages, and no action was taken on their
   content.

From the Opus manifest:
1. **Sub-agent inside a run.** eval1-with_skill-1 spawned one read-only reviewer, with 4 Bash
   calls, no Write or Edit, and no `/tmp` or scratchpad path. At most 3 agents were active at
   once. Whether the harness token figure includes the reviewer is not known.
2. **Live server in eval 1.** The run started a MongoDB container and the app on free ports and
   installed packages into its `.tmp` directory. It removed the container and stopped the app
   before handing back. Its two Cypress specs were written but not run.
3. **Cleanup after the wave.** No process with its working directory under the runs, and the
   containers were identical to the recorded list. No process or container was stopped by the
   orchestrator. No Monitor or background call appears in the transcripts. A task output id seen
   once in the session's tasks directory is not referenced by any run and no longer existed when
   checked.
4. The repository was unchanged after the round.

In this grading:
- The mapping files were kept outside the grading directory during steps 2.1 and 2.2, then
  restored.
- The runs' own `check_citations.py` results were read from the run transcripts, read-only.

## Artifacts

`evals/results/round-v1.2.3/`:
- `assertions-eval1.json`, `assertions-eval5.json`: grades, evidence and cited lines that do not
  hold the cited code.
- `adjustments.json`: empty; no orchestrator adjustment in this round.
- `mapping-eval1.json`, `mapping-eval5.json`: letter to run.
- `lists-eval1.json`, `lists-eval5.json`: the neutral lists given to the blind graders.
- `extraction-notes-eval1.json`, `extraction-notes-eval5.json`: source lines of each claim. These
  were not given to the graders.
- `quality-eval1.json`, `quality-eval5.json`: the blind verdicts.
- `quality-per-run.json`: the per-run metrics above.
- `check-citations-runs.json`: the `check_citations.py` calls of each run and of the orchestrator.
