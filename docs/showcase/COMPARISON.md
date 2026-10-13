# Same audit with and without the skill

Two runs on the same code and the same prompt:
- code: the healthchecks `defects` fixture at commit `7a07141`, which has three planted
  access-control defects, P-1 to P-3 (`evals/ground-truth/healthchecks-api-planted.md:20-22`);
- prompt: eval 5 of `evals/evals.json`;
- model: `claude-opus-5-5` for both runs.

| Folder | Run | Files |
|---|---|---|
| `with-skill/` | round v1.2.3, `eval5-with_skill-1` | the report, the registry, the categories; `tests/` holds the run's reproduction tests |
| `without-skill/` | round v1.2.2, `eval5-without_skill-1` | everything the run wrote: one review document and, in `tests/`, one test file |

The files are copied unchanged. The with-skill run also wrote `docs/audits/coverage-matrix.md`,
which is not copied here.

Paths below are relative to this folder. Short names:
- `W` is `with-skill/2026-10-09-api-key-scope.md`;
- `N` is `without-skill/api-key-authz-review.md`.

## 1. Planted defects found

| Planted defect | Ground truth | With skill | Without skill |
|---|---|---|---|
| P-1: the check list is filtered by owner, not by project (`hc/api/views.py:415`) | `evals/ground-truth/healthchecks-api-planted.md:20` | F2, `W:86-88` | F-1, `N:55-60` |
| P-2: a read-only key can delete a check (`hc/api/views.py:520`) | `evals/ground-truth/healthchecks-api-planted.md:21` | F1, `W:59-61` | F-2, `N:68-70` |
| P-3: lookup by `unique_key` returns the read-write view to a read-only key (`hc/api/views.py:495`) | `evals/ground-truth/healthchecks-api-planted.md:22` | F3, `W:110-112` | F-3, `N:75-77` |

Both runs report 3 of 3 planted defects as findings. The blind grades of these runs are in
`evals/results/round-v1.2.3/quality-per-run.json` (`opus/eval5-with_skill-1`) and
`evals/results/round-v1.2.2/quality-per-run.json` (`opus/eval5-without_skill-1`).

## 2. Locations and reproduction tests

| | With skill | Without skill |
|---|---|---|
| Findings | 3 (`W:39-41`) | 3 (`N:10`) |
| Findings with a `file:line` location | 3: `hc/api/views.py:520` (`W:61`), `:415` (`W:88`), `:495` (`W:112`) | 0. Each gives the file and the function, with no line: `N:57`, `N:70`, `N:77` |
| `file:line` citations in the document | 69 | 0 |
| Findings that name a reproduction test | 3: `W:79-84`, `W:105-106`, `W:127-129` | 3: `N:66`, `N:73`, `N:85` |
| Test file | `with-skill/tests/test_audit_api_key_scope.py`, 7 tests | `without-skill/tests/test_api_key_authz.py`, 11 tests |
| Run status stated | ran: 4 attack tests fail, 3 legitimate-path tests pass (`W:131-132`) | ran: 4 finding tests fail, 7 control tests pass (`N:99-101`) |
| Command stated | `W:131` | `N:108` |

The citation counts are the output of
`python3 plugin/skills/verified-security-sweep/scripts/check_citations.py <file> --root <fixture>`,
run from the repository root with the fixture at `7a07141`:
- `W`: "69 citation(s), 0 not OK", exit 0;
- `N`: "no file:line citations found".

The test counts are the `def test_` lines in each file.

## 3. Candidates examined and not reported as defects

| | With skill | Without skill |
|---|---|---|
| Section | "Refused or unconfirmed candidates" (`W:134`) | none. "Notes (not blocking)" (`N:87`) and the "OK" rows of the endpoint matrix (`N:34-51`) |
| Entries | 11, R1 to R11 (`W:136-173`), also listed in the verification table (`W:42-52`) | 5 notes, N-1 to N-5 (`N:89-93`), and 12 matrix rows marked "OK" (`N:37-39`, `N:42-50`) |
| Reason given | a lens and a cited line for each entry (below) | a sentence for each note; the matrix rows give the decorator and the scoping |
| Also listed | "Checked, no defect", 3 items (`W:184-186`) | |

The with-skill refusals by lens:
- claim correctness: 7 entries, R2, R3, R4, R6, R7, R8, R9 (`W:139`, `W:142`, `W:146`, `W:154`,
  `W:157`, `W:160`, `W:164`);
- exploitability: 3 entries, R5, R10, R11 (`W:150`, `W:168`, `W:171`);
- existing mitigation: 1 entry, R1 (`W:136`).

## 4. Where each run wrote, registry and history

| | With skill | Without skill |
|---|---|---|
| Record written to | `docs/audits/`: the dated report, `categories.md`, `sweep-registry.md`, `coverage-matrix.md` (`W:15-16`) | `docs/security/api-key-authz-review.md` (`without-skill/tests/test_api_key_authz.py:3`) |
| Test written to | `hc/api/tests/test_audit_api_key_scope.py` (`W:202-203`) | `hc/api/tests/test_api_key_authz.py` (`N:9`) |
| Report filename carries the date | yes, `2026-10-09-api-key-scope.md` | no; the date is in the table at `N:5` |
| Registry | `with-skill/sweep-registry.md:11`: zone `api-key-scope`, last run 2026-10-09, yield 3/14 | none |
| Proposed next sweeps | 3 zones, `with-skill/sweep-registry.md:17-19` | none listed; re-run steps for the same scope at `N:105-115` |
| History | the registry's "Last run" column, read from report filenames (`with-skill/sweep-registry.md:3-5`) | a status log with 1 row (`N:117-121`) |
| Categories file | `with-skill/categories.md:31-43`, 11 categories | none |

## 5. What a reader can verify without re-running the audit

With skill:
- Open each of the 69 `file:line` citations of `W` in the fixture at `7a07141`, or run
  `check_citations.py` on `W` as in section 2.
- Run the 7 tests with the command at `W:131`. The report states 4 failures and 3 passes
  (`W:131-132`).
- Run
  `python3 plugin/skills/verified-security-sweep/scripts/sweep_status.py --check --audits docs/showcase/with-skill --registry docs/showcase/with-skill/sweep-registry.md`
  from the repository root. On this copy it prints "1 zones, 1 dated reports, 0 divergent,
  0 stale" and exits 0.
- For each of the 11 refused candidates, open the cited line and check the stated lens
  (`W:136-173`).

Without skill:
- Find the quoted code of F-1 (`N:60`) in `hc/api/views.py` by search. F-2 and F-3 name a function
  and a decorator or call (`N:70`, `N:77`), with no line.
- Run the 11 tests with the command at `N:108`. The report states 4 failures and 7 passes
  (`N:99-101`).
- The document has no `file:line` citation for `check_citations.py` to check and no registry for
  `sweep_status.py` to check.
