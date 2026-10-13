# Finding quality against ground truth: NodeGoat access-control sweep, 2026-10

This file measures the quality of the findings in the eval 1 (`nodegoat-access-control-sweep`) reports that were already produced on `claude-opus-5-5` and `claude-sonnet-5-5`, with and without the skill. It checks three things: whether the findings are real, how many of the known defects they found, and which real defects they refused. No new run of the skill was made. The `claude-haiku-4-5-20251001` runs are excluded because the with-skill run was invalid (see `behavior-2026-10-claude-haiku-4-5-20251001.md`).

Reference code: the NodeGoat fixture (`evals/fixtures/nodegoat`) reset to the planted commit `9e832da`. All code checks were read-only against that commit.

## Procedure

The session ran on `claude-opus-5-5`. Every sub-agent ran on `claude-opus-5-5` and started with a clean context.

0. **Preparation.**
   - The repository was on `main` at `addf79d`, and the branch `evals-quality` was created from it.
   - The four eval 1 reports were located by path only:
     - Opus: `iteration-1/eval-1-nodegoat-access-control-sweep/<with_skill|without_skill>/outputs/docs-audits/2026-10-09-access-control.md` in the Opus workspace.
     - Sonnet: `eval1/<with_skill|without_skill>/outputs/docs-audits/2026-10-09-access-control.md` in the Sonnet session's workspace. That workspace was found through the transcripts of the Sonnet run session and of the Opus regrade session.
   - The Sonnet runs were identified from files that are not reports. With skill, `outputs/git-status.txt` lists `test/security/allocations-access-test.js`. Without skill, `outputs/docs-audits/sweep-registry.md` still has 2026-10-03 on the `access-control` row.
   - The reference copy was reset to `9e832da` and cleaned.
1. **Ground truth, before any report was read.** A fresh sub-agent received only the path of the reference copy and the zone definition. It wrote the list of access-control defects from the code and from `app/views/tutorial/`:
   - GT-1 and GT-2 open;
   - AC-1 and AC-2 marked CLOSED;
   - ADJ-1 to ADJ-9 as adjacent to the zone.

   The list is `evals/ground-truth/nodegoat-access-control.md`. It was committed as `db3aac5` and pushed to `evals-quality` before step 2.
2. **Anonymized extraction.** The four runs received the letters A to D in an order drawn with `random.shuffle` in `python3`. A second fresh sub-agent read the four reports and wrote one neutral list per run:
   - the claim in one sentence;
   - the cited `file:line`;
   - the stated status, normalized to "confirmed" (presented as a real defect) or "unconfirmed" (anything else: refused, false positive, over-rated, needs review, closed).
3. **Blind grading.** A third fresh sub-agent received the reference copy, the ground truth and the four lists. It did not receive `mapping.json` or the reports. For each finding it recorded:
   - REAL, NOT REAL or UNDECIDED in the code at `9e832da`;
   - in zone or not;
   - for REAL findings, whether the cited line is the defect line, and the matching GT entry or "outside GT";
   - whether a confirmed finding re-reports AC-1 or AC-2.

   The result had 0 UNDECIDED. It proposed two new GT entries (NEW-1 and NEW-2, below), and the grader noted that the ground truth had examined both and excluded them as by design.
4. **De-anonymization and metrics.** `mapping.json` was opened only after step 3. The metrics are defined as follows:
   - **Precision:** REAL / (REAL + NOT REAL) over the confirmed findings.
   - **Recall GT:** open GT entries (GT-1, GT-2) found by a confirmed finding, out of 2. The bracket gives the number of open GT entries found only by unconfirmed findings.
   - **Recall extended GT:** the same, over GT-1, GT-2, NEW-1 and NEW-2, out of 4.
   - **Unconfirmed REAL:** all unconfirmed findings graded REAL. The bracket gives the in-zone count and the GT entries they match.
   - **Exact line:** REAL findings (confirmed and unconfirmed) whose cited line is the defect line, out of all REAL findings of the run.
   - **Out of zone:** confirmed findings outside the zone.
   - **Re-reports:** confirmed findings that are AC-1 or AC-2.

Proposed GT entries from step 3:

- NEW-1: memos have no owner; every signed-in user reads the whole collection and writes to it (`app/data/memos-dao.js:18-21`, `app/data/memos-dao.js:28`, `app/routes/memos.js:13`).
- NEW-2: `/tutorial` is mounted without `isLoggedIn` (`app/routes/index.js:75`).

Commits on `evals-quality`: ground truth `db3aac5`; results `07baa00`.

After review, the ground truth, the finding lists and `grading.json` were translated from
Romanian into English, with no change of content; the ground truth as committed before grading
is `db3aac5`. One error in the ground truth was corrected after grading, outside the zone:
ADJ-3 claimed the session cookie is readable from JS, but the `express-session` default is
`httpOnly: true` (see the correction at the end of the ground truth). No metric changes.

Artifacts: `evals/results/quality-2026-10-nodegoat/`:
- `mapping.json`: letter to run. In this copy the local workspace prefixes of the report paths are replaced by `<opus-workspace>` and `<sonnet-workspace>`, and the mapping is otherwise unchanged.
- `findings-A.md` to `findings-D.md`;
- `grading.json`.

## Results

| model | skill | confirmed | REAL | NOT REAL | UNDECIDED | precision | recall GT | recall extended GT | unconfirmed REAL | exact line | out of zone | re-reports |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| claude-opus-5-5 | with | 4 | 4 | 0 | 0 | 4/4 (100%) | 2/2 (only unconfirmed: 0) | 2/4 (only unconfirmed: 1, NEW-1) | 9 (in zone 3: AC-1, AC-2, NEW-1) | 10/13 | 2 | 0 |
| claude-opus-5-5 | without | 5 | 5 | 0 | 0 | 5/5 (100%) | 2/2 (only unconfirmed: 0) | 2/4 (only unconfirmed: 2, NEW-1, NEW-2) | 7 (in zone 4: AC-1, AC-2, NEW-1, NEW-2) | 8/12 | 2 | 1 (C-6, AC-1) |
| claude-sonnet-5-5 | with | 1 | 1 | 0 | 0 | 1/1 (100%) | 1/2 (only unconfirmed: 1, GT-2) | 1/4 (only unconfirmed: 3, GT-2, NEW-1, NEW-2) | 11 (in zone 5: AC-1, AC-2, NEW-1, NEW-2, GT-2) | 3/12 | 0 | 0 |
| claude-sonnet-5-5 | without | 2 | 2 | 0 | 0 | 2/2 (100%) | 1/2 (only unconfirmed: 1, GT-2) | 1/4 (only unconfirmed: 2, GT-2, NEW-1) | 10 (in zone 4: AC-1, AC-2, NEW-1, GT-2) | 2/12 | 1 | 0 |

Letters: A = claude-sonnet-5-5 with skill, B = claude-opus-5-5 with skill, C = claude-opus-5-5 without skill, D = claude-sonnet-5-5 without skill.

Confirmed findings by run:
- A-3 (GT-1).
- B-3 (GT-1), B-4 (outside zone), B-6 (outside zone), B-7 (GT-2).
- C-2 (GT-1), C-3 (outside zone), C-4 (GT-2), C-5 (outside zone), C-6 (AC-1: the guard test covers only GET `/benefits`).
- D-5 (GT-1), D-6 (outside zone).

The claims, cited lines and grading evidence for every finding are in `grading.json` and in `findings-A.md` to `findings-D.md`.

## Findings by verdict

### Confirmed findings graded NOT REAL

None. Every confirmed finding in the four runs was graded REAL.

### Unconfirmed findings graded REAL

| Finding | Run | Claim (extracted) | Cited | In zone | Matches | Evidence at 9e832da |
|---|---|---|---|---|---|---|
| A-1 | claude-sonnet-5-5, with skill | An earlier issue concerning access to the benefits route was handled in a previous audit and is treated as closed. | `none` | yes | AC-1 | `app/routes/index.js:55-56` |
| A-2 | claude-sonnet-5-5, with skill | An earlier issue concerning the admin-gating middleware was rejected in a previous audit and not reconsidered. | `none` | yes | AC-2 | `app/routes/session.js:28,32` |
| A-4 | claude-sonnet-5-5, with skill | Every signed-in user sees all memos and memos carry no owner, suggesting missing per-user scoping on the memos page. | `app/data/memos-dao.js:448-468` | yes | NEW-1 | `app/data/memos-dao.js:18-21,28` |
| A-5 | claude-sonnet-5-5, with skill | The memo body can carry stored script that is rendered to other users. | `none` | no | outside GT | `server.js:135-142, app/views/memos.html:31, package.json:17` |
| A-6 | claude-sonnet-5-5, with skill | The threshold query value is concatenated into a server-side JavaScript filter, letting a signed-in user remove the user restriction and read all allocations. | `allocations-dao.js:396-398` | no | outside GT | `app/data/allocations-dao.js:77-79` |
| A-7 | claude-sonnet-5-5, with skill | The tutorial pages can be reached without signing in. | `none` | yes | NEW-2 | `app/routes/index.js:75` |
| A-9 | claude-sonnet-5-5, with skill | Contribution form fields are evaluated as code on the server, allowing an authenticated user to execute code. | `contributions.js:271-273` | no | outside GT | `app/routes/contributions.js:32-34` |
| A-10 | claude-sonnet-5-5, with skill | A query-supplied URL is used for a redirect without validation. | `index.js:68` | no | outside GT | `app/routes/index.js:68` |
| A-11 | claude-sonnet-5-5, with skill | The server fetches a user-supplied URL, enabling server-side requests to arbitrary targets. | `research.js:14-15` | no | outside GT | `app/routes/research.js:15-16` |
| A-12 | claude-sonnet-5-5, with skill | The session identifier is not renewed when a user logs in. | `session.js:197` | yes | GT-2 | `app/routes/session.js:116` |
| A-13 | claude-sonnet-5-5, with skill | User passwords are stored in plaintext. | `user-dao.js` | no | outside GT | `app/data/user-dao.js:25,61` |
| B-1 | claude-opus-5-5, with skill | The benefits route was previously reachable by any signed-in user; the earlier fix restricting it to admins still holds. | `app/routes/index.js:55-56` | yes | AC-1 | `app/routes/index.js:55-56` |
| B-2 | claude-opus-5-5, with skill | The admin middleware redirects to the login page instead of answering with a forbidden status. | `none` | yes | AC-2 | `app/routes/session.js:28,32` |
| B-5 | claude-opus-5-5, with skill | The same threshold value allows a server-side denial of service through an endless loop. | `none` | no | outside GT | `app/data/allocations-dao.js:78` |
| B-8 | claude-opus-5-5, with skill | All memos live in one shared collection visible to every user with no ownership. | `app/data/memos-dao.js` | yes | NEW-1 | `app/data/memos-dao.js:18-21,28` |
| B-16 | claude-opus-5-5, with skill | Contribution form fields are evaluated as code, letting any signed-in user run code in the server process. | `app/routes/contributions.js:32-34` | no | outside GT | `app/routes/contributions.js:32-34` |
| B-17 | claude-opus-5-5, with skill | The research route fetches a caller-supplied URL from the server. | `app/routes/research.js:15-16` | no | outside GT | `app/routes/research.js:15-16` |
| B-18 | claude-opus-5-5, with skill | The learn route redirects to an arbitrary supplied URL. | `app/routes/index.js:66-69` | no | outside GT | `app/routes/index.js:68` |
| B-19 | claude-opus-5-5, with skill | A regular expression in the profile handler is vulnerable to catastrophic backtracking. | `app/routes/profile.js:59` | no | outside GT | `app/routes/profile.js:59` |
| B-20 | claude-opus-5-5, with skill | Template auto-escaping is disabled, enabling stored script injection in memos and profile. | `server.js:135-142` | no | outside GT | `server.js:135-142` |
| C-1 | claude-opus-5-5, without skill | The benefits route was previously reachable by regular users; the earlier fix restricting both read and write to admins still holds. | `none` | yes | AC-1 | `app/routes/index.js:55-56` |
| C-10 | claude-opus-5-5, without skill | The tutorial pages are reachable without signing in. | `none` | yes | NEW-2 | `app/routes/index.js:75` |
| C-11 | claude-opus-5-5, without skill | Memos have no owner and every signed-in user sees every memo, which could be a cross-user exposure. | `memos-dao.js:18-21` | yes | NEW-1 | `app/data/memos-dao.js:18-21` |
| C-12 | claude-opus-5-5, without skill | The admin middleware redirects instead of answering with a forbidden status. | `none` | yes | AC-2 | `app/routes/session.js:28,32` |
| C-13 | claude-opus-5-5, without skill | The learn route performs an open redirect. | `index.js:66-69` | no | outside GT | `app/routes/index.js:68` |
| C-14 | claude-opus-5-5, without skill | The research route fetches a caller-controlled URL from the server. | `research.js:14-16` | no | outside GT | `app/routes/research.js:15-16` |
| C-15 | claude-opus-5-5, without skill | Contribution form fields are evaluated as code on the server. | `contributions.js:32-34` | no | outside GT | `app/routes/contributions.js:32-34` |
| D-1 | claude-sonnet-5-5, without skill | The benefits route was previously open to non-admin users and has since been fixed. | `none` | yes | AC-1 | `app/routes/index.js:55-56` |
| D-2 | claude-sonnet-5-5, without skill | The admin middleware redirects instead of refusing with a forbidden status. | `none` | yes | AC-2 | `app/routes/session.js:28,32` |
| D-7 | claude-sonnet-5-5, without skill | The same injection can hang the server with an endless loop. | `none` | no | outside GT | `app/data/allocations-dao.js:78` |
| D-8 | claude-sonnet-5-5, without skill | Memos form a single shared list without an author, so there is no per-user ownership. | `none` | yes | NEW-1 | `app/data/memos-dao.js:18-21,28` |
| D-11 | claude-sonnet-5-5, without skill | No POST route, including the admin benefits update, has protection against cross-site request forgery. | `none` | no | outside GT | `server.js:104-113` |
| D-12 | claude-sonnet-5-5, without skill | The session identifier is not regenerated at login, enabling fixation. | `none` | yes | GT-2 | `app/routes/session.js:116` |
| D-13 | claude-sonnet-5-5, without skill | Passwords are stored and compared in plaintext. | `user-dao.js` | no | outside GT | `app/data/user-dao.js:25,61` |
| D-14 | claude-sonnet-5-5, without skill | Contribution fields are evaluated as code on the server. | `none` | no | outside GT | `app/routes/contributions.js:32-34` |
| D-15 | claude-sonnet-5-5, without skill | The learn route performs an open redirect. | `none` | no | outside GT | `app/routes/index.js:68` |
| D-16 | claude-sonnet-5-5, without skill | The research route fetches a caller-controlled URL from the server. | `none` | no | outside GT | `app/routes/research.js:15-16` |
