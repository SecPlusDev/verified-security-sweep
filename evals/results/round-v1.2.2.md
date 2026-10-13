# Round v1.2.2: two models, graded

This file records the grading of round v1.2.2 of the skill at plugin version 1.2.2 (`main` at
`099cf6b`). The runs were made on `claude-opus-5-5` and `claude-sonnet-5-5`, one orchestrator
session per model, and each round has its own manifest (incidents below). The grading covers the
assertions of `evals/evals.json` for evals 1, 4 and 5; a blind finding-quality score for evals 5
and 1; and the criteria B1 to B5, which were fixed before the round. Only the measurements are
reported, with no interpretation beyond the criteria.

Path prefixes in this file and in `round-v1.2.2/`:
- `<opus-round>` is the Opus round directory and `<sonnet-round>` the Sonnet one.
- `<opus-workspace>` is the Opus evaluation workspace of 2026-10-09 and `<sonnet-archive>` the
  archived Sonnet evaluation of 2026-10-09.

## Procedure

The grading session ran on `claude-opus-5-5`. Every sub-agent ran on `claude-opus-5-5` in a fresh
context and received only what its step lists below. The grader did not run the skill and did not
start any application, server, database or container.

0. **Preparation.**
   - Read `docs/BUILD.md` sections 3 and 5, `evals/evals.json` and both round manifests.
   - Located the 24 runs to grade:
     - Opus v1.2.2:
       - `eval5-with_skill-1..3` and `eval5-without_skill-1..2`;
       - `eval1-with_skill-1..3-r2` (the reruns; the originals without `-r2` are not graded, see
         incidents);
       - `eval4-with_skill-1..2`.
     - Sonnet v1.2.2: `eval5-with_skill-1..3`, `eval5-without_skill-1..2`,
       `eval1-with_skill-1..3`, `eval4-with_skill-1..2`.
     - Baselines of 2026-10-09 for evals 1 and 4 without the skill:
       - Opus in `<opus-workspace>/iteration-1/eval-<n>-<name>/without_skill/`;
       - Sonnet in `<sonnet-archive>/eval<n>/without_skill/`.
   - Checked the reference code, read-only:
     - `<opus-round>/base/nodegoat` at `9e832da`, clean;
     - `<opus-round>/base/healthchecks-defects` at `7a07141`, clean.
   - Created branch `evals-round-v1.2.2` from `main`.
1. **Assertions.** Three sub-agents, one per eval, ran in parallel: eval 1 had 8 runs, eval 4 had
   6 and eval 5 had 10. Each received:
   - the eval's assertion text from `evals.json`;
   - the grading rules of `docs/BUILD.md` section 5;
   - the `outputs/` paths of its runs;
   - the path of the reference code.

   The rules were:
   - PASS or FAIL only.
   - A required section that is missing fails, even if its content appears elsewhere.
   - Every line cited by a confirmed finding is opened in the reference code. A line that does not
     exist or does not hold the cited code fails the cited-lines assertion.
   - Every grade carries its evidence as `path:line`.
   - For eval 4, the staged state was compared with the patch itself, not by counting files. The
     grader built the expected cached diff by applying
     `evals/fixtures/patches/nodegoat/verify-fix.patch` with `git apply --index` on a clone at
     `9e832da`, then compared each run's staged diff with `cmp`.
   - The guard test of Opus `eval4-with_skill-1` was read at the path recorded in the Opus
     manifest.

   For evals 1 and 5, the graders also listed every cited line that does not exist or does not
   hold the cited code, whether the finding was confirmed or unconfirmed.
2. **Finding quality, blind.** This step covered eval 5 (10 runs) and eval 1 (the 6 runs with the
   skill).
   1. **Blinding and extraction.**
      - Letters were assigned to runs with `random.shuffle` in `python3`.
      - Each run's written record and final reply were copied under its letter. Run paths and
        model names were redacted in the copies.
      - The mapping was moved out of the grading directory until step 3.
      - One fresh sub-agent per eval read the copies and wrote a neutral list per letter:
        - the claim in one sentence, with none of the skill's vocabulary and none of its format;
        - the cited `file:line`;
        - the status: "confirmed" or "unconfirmed".
   2. **Grading.**
      - One fresh sub-agent per eval received the reference code, the ground truth and the lists.
        It did not receive the mapping or the reports.
        - Eval 5: `evals/ground-truth/healthchecks-api-planted.md`.
        - Eval 1: `evals/ground-truth/nodegoat-access-control.md`, including its closing
          correction.
      - For each claim it recorded:
        - REAL, NOT REAL or UNDECIDED, with a reason;
        - whether the claim is in the zone;
        - for REAL claims, whether the location line holds the defect, and the matching P-n or
          GT-n entry, or "outside GT".
      - The stop rule was more than 2 UNDECIDED in one eval. Both evals had 0.
3. **Metrics and criteria.**
   - The mappings were opened only after step 2.
   - B1 to B5 were computed over the 16 runs made with the skill in v1.2.2 (eval 1 x3, eval 4 x2,
     eval 5 x3, on both models).
   - Where a rule was ambiguous, the stricter reading was applied and the ambiguity is recorded.
4. **This file and the artifacts.**

## Assertions

`n/m` counts runs that pass. The totals count assertion grades. Per-run grades and evidence are in
`round-v1.2.2/assertions-eval<n>.json`. One orchestrator adjustment applies, listed under
"Strict readings".

### Eval 1 (`nodegoat-access-control-sweep`)

| Assertion | Opus with skill | Opus without | Sonnet with skill | Sonnet without |
|---|---|---|---|---|
| 1 Report, template sections | 3/3 | 0/1 | 3/3 | 0/1 |
| 2 Exact file:line, chain of three, cited lines hold the code | 3/3 | 0/1 | 2/3 | 0/1 |
| 3 VERIFIED REAL with existing test and run status | 3/3 | 0/1 | 3/3 | 0/1 |
| 4 Unconfirmed candidates with disposition | 3/3 | 0/1 | 0/3 | 0/1 |
| 5 Registry row, `--check` exits 0 | 3/3 | 1/1 | 3/3 | 0/1 |
| 6 No re-report of AC-1, AC-2 | 3/3 | 1/1 | 3/3 | 1/1 |
| 7 Hygiene | 3/3 | 1/1 | 3/3 | 1/1 |
| Total | **21/21 (100%)** | **3/7 (43%)** | **17/21 (81%)** | **2/7 (29%)** |

The FAIL grades in runs with the skill:
- **Sonnet runs 1 to 3, assertion 4.** Entries in the refused section carry no allowed disposition:
  - run 1: `R:65-70`, "examined, no finding";
  - run 2: `R:76-79`;
  - run 3: `R:84-89`, including a "refused" entry that names no lens.
- **Sonnet run 1, assertion 2 (adjusted).** The location `app/routes/allocations.js:17` (`R:32`)
  does not hold `req.params`, which is on line 18.

### Eval 4 (`nodegoat-verify-fix`)

| Assertion | Opus with skill | Opus without | Sonnet with skill | Sonnet without |
|---|---|---|---|---|
| Format, verdict BROKEN, sections in order | 0/2 | 0/1 | 1/2 | 0/1 |
| 8a Broken legitimate path named | 2/2 | 1/1 | 2/2 | 0/1 |
| 8b Guard with both `it(...)` halves | 2/2 | 1/1 | 0/2 | 1/1 |
| Staged fix equals the patch, no commit | 2/2 | 1/1 | 2/2 | 1/1 |
| Total | **6/8 (75%)** | **3/4 (75%)** | **5/8 (62%)** | **2/4 (50%)** |

The FAIL grades in runs with the skill:
- **Format.** Opus runs 1 and 2 and Sonnet run 2 put the over-restriction part before the
  unverified callers. The order is set by `references/verify-fix.md:103-111`. Evidence:
  `outputs/response.md:3`, `:18` (Opus 1); `:3`, `:27` (Opus 2); `:3`, `:17` (Sonnet 2).
- **8b.** Both Sonnet runs wrote the two halves of the guard with node:test `test()` or
  `t.test()`, not `it(...)`. Evidence: Sonnet 1 `outputs/response.md:42-54`; Sonnet 2
  `<sonnet-round>/runs/eval4-with_skill-2.tmp/guard.test.js:12`, `:17`.

All six staged diffs are byte-identical to the expected diff (`cmp`). The unstaged diffs are
empty and HEAD is `9e832da` in all six.

### Eval 5 (`healthchecks-api-planted-defects`)

| Assertion | Opus with skill | Opus without | Sonnet with skill | Sonnet without |
|---|---|---|---|---|
| 1 Bootstrap: categories, registry, report | 3/3 | 0/2 | 3/3 | 0/2 |
| 2 Report, API zone slug, template sections | 3/3 | 0/2 | 3/3 | 0/2 |
| 3 Exact file:line, chain of three, cited lines hold the code | 2/3 | 0/2 | 0/3 | 0/2 |
| 4 VERIFIED REAL with existing test and run status | 2/3 | 0/2 | 3/3 | 0/2 |
| 5 Unconfirmed candidates with disposition | 0/3 | 0/2 | 0/3 | 0/2 |
| 6 Registry row, `--check` exits 0 | 3/3 | 0/2 | 3/3 | 0/2 |
| 7 Hygiene | 3/3 | 0/2 | 3/3 | 0/2 |
| Total | **16/21 (76%)** | **0/14 (0%)** | **15/21 (71%)** | **0/14 (0%)** |

The FAIL grades:
- **Assertion 5, all six runs with the skill.** Entries carry a reason but no allowed
  disposition, for example "by design", "OK", "decision pending" or "over-rated". Evidence:
  - Opus 1 `R:176-188`; Opus 2 `R:139-148`; Opus 3 `R:98-139`;
  - Sonnet 1 `R:107-108`; Sonnet 2 `R:75-80`; Sonnet 3 `R:69-74`.
- **Opus run 2, assertions 3 and 4.** L1 is marked VERIFIED REAL (Low) at `R:41`, but it has no
  evidence chain and no reproduction test.
- **Sonnet runs, assertion 3.**
  - Run 1: the F2 chain has no data-flow element (`R:77-78`).
  - Run 2: the AUD-1 chain cites `hc/api/decorators.py:62`, a blank line (`R:35`).
  - Run 3: the F1 chain cites `hc/api/decorators.py:57`, which holds
    `return error("missing api key", 401)` (`R:34`).
- **Runs without the skill.** No `docs/audits/` was written. The record went to `docs/security/`
  or `docs/security-audits/`, which also fails assertion 7. No `file:line` is cited.
  `sweep_status.py --check` exits 2.

### Totals over evals 1, 4 and 5

| Model | With skill | Without skill |
|---|---|---|
| `claude-opus-5-5` | 43/50 (86%) | 6/25 (24%) |
| `claude-sonnet-5-5` | 37/50 (74%) | 4/25 (16%) |

The runs without the skill for evals 1 and 4 are the 2026-10-09 baselines, n=1 each. They are
graded here with the assertion text of `evals.json` at `099cf6b`.

### Cited lines that do not exist or do not hold the cited code

All runs of evals 1 and 5 are listed. The graders opened 264 cited lines in eval 1 and 207 in
eval 5. The 2026-10-09 baselines are included.

| Run | Finding (status, kind) | Report line | Cited | Problem |
|---|---|---|---|---|
| sonnet/eval1-with_skill-1 | AC-3 (confirmed, location) | `R:32` | `app/routes/allocations.js:17` | does not hold the cited code (`req.params` is on :18); orchestrator adjustment |
| sonnet/eval1-with_skill-2 | AC-4 (unconfirmed, chain) | `R:26` | `app/routes/session.js:106-114` | does not hold the cited code (comment block; the middleware is at :25-34) |
| sonnet/eval1-with_skill-2 | AC-4 (unconfirmed, chain) | `R:67` | `session.js:106-114` | does not hold the cited code |
| sonnet/eval1-with_skill-2 | AC-6 (unconfirmed, location) | `R:28` | `app/routes/session.js:109` | does not hold the cited code (comment line) |
| sonnet/eval1-with_skill-2 | read-and-clean candidate (unconfirmed, chain) | `R:78` | `profile-dao.js:168-189` | does not exist (file has 113 lines) |
| sonnet/eval1-with_skill-2 | read-and-clean candidate (unconfirmed, chain) | `R:79` | `session.js:337-345` | does not exist (file has 277 lines) |
| sonnet/eval1-with_skill-2 | hand-off item (unconfirmed, other) | `R:105` | `app/routes/session.js:197` | does not hold the cited code |
| sonnet/eval5-with_skill-2 | AUD-1 (confirmed, chain) | `R:35` | `hc/api/decorators.py:62` | does not hold the cited code (blank line) |
| sonnet/eval5-with_skill-3 | F1 (confirmed, chain) | `R:34` | `hc/api/decorators.py:57` | does not hold the cited code |

No other run has an entry. `R` is the run's dated report under `outputs/docs-audits/`.

## Finding quality

Definitions:
- **Confirmed:** the claims the report asserts as defects.
- **Precision:** REAL / confirmed.
- **Recall on GT:** ground-truth entries found by a confirmed REAL claim. The denominator is 2 for
  eval 1 (GT-1, GT-2) and 3 for eval 5 (P-1, P-2, P-3).
- **Exact lines:** confirmed REAL claims whose location line holds the defect.
- **Unconfirmed (REAL):** all unconfirmed claims, with the number graded REAL in brackets.

Blind grading verdicts: eval 1, 93 claims (55 REAL, 38 NOT REAL, 0 UNDECIDED); eval 5, 125 claims
(40 REAL, 85 NOT REAL, 0 UNDECIDED).

| Run | Letter | Confirmed | REAL | NOT REAL | Precision | Recall on GT (confirmed) | GT found only unconfirmed | Exact lines | Unconfirmed (REAL) | Confirmed REAL outside GT |
|---|---|---|---|---|---|---|---|---|---|---|
| opus/eval1-with_skill-1-r2 | D | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 15 (8) | none |
| opus/eval1-with_skill-2-r2 | B | 2 | 2 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 2/2 | 21 (12) | B-2 (ADJ-1, in zone) |
| opus/eval1-with_skill-3-r2 | A | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 11 (7) | none |
| sonnet/eval1-with_skill-1 | C | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 13 (7) | none |
| sonnet/eval1-with_skill-2 | E | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 14 (8) | none |
| sonnet/eval1-with_skill-3 | F | 1 | 1 | 0 | 1.00 | 1/2 (GT-1) | GT-2 | 1/1 | 12 (6) | none |
| opus/eval5-with_skill-1 | B | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 11 (0) | none |
| opus/eval5-with_skill-2 | G | 4 | 4 | 0 | 1.00 | 3/3 | none | 4/4 | 9 (0) | G-4 (metrics key compare, out of zone) |
| opus/eval5-with_skill-3 | J | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 13 (2) | none |
| opus/eval5-without_skill-1 | I | 4 | 4 | 0 | 1.00 | 3/3 | none | 0/4 | 7 (0) | I-6 (metrics key compare, out of zone) |
| opus/eval5-without_skill-2 | C | 3 | 3 | 0 | 1.00 | 3/3 | none | 0/3 | 14 (2) | none |
| sonnet/eval5-with_skill-1 | A | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 10 (3) | none |
| sonnet/eval5-with_skill-2 | D | 2 | 2 | 0 | 1.00 | 2/3 (P-1, P-2) | none | 2/2 | 5 (0) | none |
| sonnet/eval5-with_skill-3 | H | 3 | 3 | 0 | 1.00 | 3/3 | none | 3/3 | 9 (0) | none |
| sonnet/eval5-without_skill-1 | E | 4 | 4 | 0 | 1.00 | 3/3 | none | 0/4 | 5 (1) | E-7 (metrics key compare, out of zone) |
| sonnet/eval5-without_skill-2 | F | 3 | 3 | 0 | 1.00 | 3/3 | none | 0/3 | 10 (0) | none |

Location details:
- The eval 5 runs without the skill give no line for any confirmed claim (`location: null` in
  `lists-eval5.json`), so they have 0 exact lines.
- No confirmed claim in eval 1 re-reports AC-1 or AC-2. Three unconfirmed claims match AC-2:
  B-11, C-8 and D-9.

## Criteria (fixed before the round)

The criteria are computed over the 16 runs with the skill in v1.2.2.

| Criterion | Result |
|---|---|
| B1 Nothing outside `docs/audits` and test folders changes; eval 4 staged equals the patch, no commit | **PASS** |
| B2 Zero confirmed findings graded NOT REAL | **PASS** |
| B3 Zero cited lines that do not exist; zero location lines of confirmed findings that do not hold the cited code | **FAIL** |
| B4 Eval 5: `docs/audits` created (categories, registry, report) and `sweep_status --check` exits 0, in all 6 runs | **PASS** |
| B5 Eval 5, per model: mean recall on P-1..P-3 (confirmed) with skill >= without skill | **FAIL** (Opus PASS, Sonnet FAIL) |

**B1, PASS.**
- Assertion 7 passes in all 12 eval 1 and eval 5 runs with the skill.
  - Eval 1: `outputs/git-status.txt` lists only `docs/audits/` and test files.
  - Eval 5: likewise; `__pycache__` and `.venv` are gitignored.
- In the 4 eval 4 runs with the skill:
  - `outputs/staged.diff` is byte-identical to the expected diff;
  - `outputs/unstaged.diff` is empty;
  - `outputs/head.txt` is `9e832da61b323e1e234bbc69501bf5e175b009b6`;
  - `outputs/git-status.txt` lists only the two staged files of the patch.

**B2, PASS.**
- The 12 eval 1 and eval 5 runs with the skill have 25 confirmed claims, all REAL
  (`quality-per-run.json`).
- Eval 4 produces no finding list, so B2 is computed on evals 1 and 5 only.

**B3, FAIL.** The failing runs:
- **sonnet/eval1-with_skill-2 has two cited lines that do not exist:**
  - `profile-dao.js:168-189` (`R:78`);
  - `session.js:337-345` (`R:79`).

  Both are in the chain of an unconfirmed candidate.
- **sonnet/eval1-with_skill-1 has a location line of a confirmed finding that does not hold the
  cited code:** `app/routes/allocations.js:17` (`R:32`). This entry rests on the orchestrator's
  strict-reading adjustment. With the grader's reading, B3 still fails on the first run alone.
- **Recorded, not counted by B3's text:**
  - two lines of confirmed findings that do not hold the cited code but are chain lines, not
    location lines: sonnet/eval5-with_skill-2 `R:35` and sonnet/eval5-with_skill-3 `R:34`;
  - the four other entries of sonnet/eval1-with_skill-2 in the table above.
- The blind grader's location check finds every confirmed REAL claim of the 12 runs on its defect
  line.

**B4, PASS.**
- Assertion 1 passes in all 6 eval 5 runs with the skill. `outputs/docs-audits/` holds
  `categories.md`, `sweep-registry.md` and a dated report.
- `outputs/sweep-status-check.txt` ends with `exit code: 0` in all 6. The assertion grader re-ran
  the check on each copy and got exit 0.

**B5, FAIL.** Recall on P-1..P-3 from confirmed REAL claims:

| Model | With skill (runs 1, 2, 3) | Mean | Without skill (runs 1, 2) | Mean | Result |
|---|---|---|---|---|---|
| `claude-opus-5-5` | 3/3, 3/3, 3/3 | 1.00 | 3/3, 3/3 | 1.00 | PASS |
| `claude-sonnet-5-5` | 3/3, 2/3, 3/3 | 0.89 | 3/3, 3/3 | 1.00 | FAIL |

- P-3 is missing from sonnet/eval5-with_skill-2 (letter D). That run's list has no claim matching
  P-3, confirmed or unconfirmed.
- No planted defect was found only as an unconfirmed claim in any eval 5 run, with or without the
  skill.

## Strict readings and ambiguities

- **Orchestrator adjustment, eval 1, sonnet/eval1-with_skill-1, assertion 2: PASS to FAIL.**
  - The grader accepted the location `app/routes/allocations.js:17` because it is part of a
    destructuring that spans lines 16 to 18. Line 17 holds only `userId`, and the cited
    `req.params` is on line 18. The stricter reading was applied.
  - The chain range `:11-:14` contains the commented session line (14) and was kept.
  - Recorded in `round-v1.2.2/adjustments.json`; the grader file is unchanged.
- **Eval 1 graders' calls.**
  - "Not a range" was applied to the location, not to ranges inside the evidence chain, following
    the text "cites an exact file:line location, not a range".
  - Every entry listed in a refused or unconfirmed section counts as an examined candidate that
    needs one of the three dispositions.
- **Eval 4 graders' calls.**
  - "then unverified callers, over-restriction, ..." was read as an order.
  - `it(...)` was read literally, so `test()` and `t.test()` do not satisfy it.
  - The over-restriction part must name the e2e spec by path. The Sonnet baseline names it by its
    test title only, which fails 8a.
- **Eval 5 graders' calls.**
  - A VERIFIED REAL finding counts as confirmed for assertions 3 and 4 even when the report keeps
    it out of its headline count (Opus run 2, L1).
  - "over-rated" is not an allowed disposition.
  - In Sonnet runs 1 and 3, the reproduction test is named by test name, and the test file is
    named once in the report. This was accepted for assertion 4.
- **Extraction status.** Calls on borderline confirmed or unconfirmed status are recorded in
  `extraction-notes-eval<n>.json`.
  - The metrics-key comparison is marked confirmed in G, E and I and unconfirmed in A and J.
  - The `$where` injection is marked unconfirmed in A and D, where the report hands it off to
    another zone.
- **B2 scope.** B2 is computed on evals 1 and 5, because eval 4 runs have no finding list.
- **B3 scope.** The second clause of B3 names location lines only. Chain lines are listed but not
  counted.

## Incidents from the manifests

From the Opus manifest:
1. **Step 0 expectation.** The verify-fix fixture stages 2 files, not 1. The check was replaced by
   a byte comparison of the cached diff with the patch applied on `9e832da`, and it passed.
2. **Monitor.** `eval5-with_skill-2` started a Monitor (`sleep 590; echo tick`) and handed back
   while it was still running. Its cwd was the round directory, so the wave-1 cleanup did not see
   it. The orchestrator stopped it with TaskStop at about 10:31 UTC, before it fired. The agent was
   not woken again, and its working copy did not change after collection.
3. **Shared scratchpad and the `-r2` rerun.**
   - Sub-agents inherited the orchestrator's scratchpad.
   - In wave 2, the three eval 1 runs used that scratchpad at the same time for app copies, seeded
     data and server logs with shared names. The artifacts were moved to
     `scratchpad-artifacts-val2/`.
   - In wave 3, the eval 4 runs wrote probes and a guard test there. They were moved to
     `scratchpad-artifacts-val3/`.
   - Eval 1 was rerun as `eval1-with_skill-{1,2,3}-r2` with the new wrapper. The runs had distinct
     MongoDB containers and ports and no reference to `/tmp` or the scratchpad.
   - The eval 5 transcripts of waves 1 and 2 were checked and showed no write outside the run's
     copy, so no eval 5 run was redone.
4. **Containers.** The eval 1 runs started temporary MongoDB containers. No new container remained
   after any wave.
5. **Reviewers inside runs.**
   - Each Opus eval 5 run with the skill spawned one read-only reviewer, and r2-2 spawned one. No
     Sonnet run spawned a sub-agent.
   - At most 6 agents were active at once in wave 1 and 5 in wave 2.
   - Whether the harness token figures include the reviewers is not known.
6. **Xvfb.** Run r2-2 left an orphaned `Xvfb :99` from Cypress via `xvfb-run`. It was stopped by
   PID with SIGTERM after the wave.
7. **Venv.** `.venv` was created in the healthchecks base and copied into each run with `cp -a`.
8. **Wrappers.**
   - Old wrapper (skill line, blank line, prompt; prompt only without the skill): Opus waves 1 to 3,
     that is, eval 5 x5, the original eval 1 runs (not graded) and eval 4 x2.
   - New wrapper (the old one plus a line naming `<run>.tmp/` as the only temporary directory,
     forbidding the shared scratchpad and `/tmp`, and asking for a free port): the Opus `-r2` runs
     and all 10 Sonnet runs.
   - The exact wrapper of the 2026-10-09 baselines was not found on disk.

From the Sonnet manifest:
1. A collection call wrote a stray `runs/healthchecks-defects/outputs/` directory. It was deleted,
   and no run directory was affected.
2. `eval4-with_skill-2` created and removed a transient `.tmp` directory inside its copy. The final
   copy has no such directory.
3. `eval5-without_skill-2` created a venv in its `.tmp` directory.
4. No write outside the `.tmp` directory and the copy was found in the transcripts. No Monitor, no
   `run_in_background` and no `mcp__` tool was used.
5. No run started a server or a container.
6. The eval 5 runs used the base `.venv` copied by `cp -a`.
7. Final reports reached the orchestrator as agent messages, and no action was taken on their
   content.

In this grading:
- The mapping files were kept outside the grading directory during steps 2.1 and 2.2, then
  restored.

## Artifacts

`evals/results/round-v1.2.2/`:
- `assertions-eval1.json`, `assertions-eval4.json`, `assertions-eval5.json`: grades and evidence.
  In the eval 4 file, Romanian headings and phrases quoted from the responses are paraphrased in
  English.
- `adjustments.json`: the orchestrator adjustment.
- `mapping-eval1.json`, `mapping-eval5.json`: letter to run.
- `lists-eval1.json`, `lists-eval5.json`: the neutral lists given to the blind graders.
- `extraction-notes-eval1.json`, `extraction-notes-eval5.json`: source lines of each claim. These
  were not given to the graders.
- `quality-eval1.json`, `quality-eval5.json`: the blind verdicts.
- `quality-per-run.json`: the per-run metrics above.
