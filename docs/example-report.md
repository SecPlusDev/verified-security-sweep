# Verified security sweep: access-control, 2026-10-04

Example report produced by the skill during its evaluation, on the NodeGoat fixture (an Express
and MongoDB application, see `evals/fixtures/README.md`) with a planted previous report. People
and deployment details are generalized; file paths and line numbers are the fixture's.

## Context
Scope: the access-control zone, extended from the previous run (which read only the route
wiring, the middleware and `/benefits`) to every authenticated handler and its data-access
module: `app/routes/index.js`, `session.js`, `allocations.js`, `profile.js`, `contributions.js`,
`memos.js`, the matching `app/data/*-dao.js`, plus `server.js` for the session configuration.
Question asked: which routes are reachable by whom, whether the middleware gates them, and
whether a regular user can read or change another user's data.

Trigger: owner request; the registry row said "the other routes rely on the middleware being
wired by hand", and the previous run had skipped every handler except `/benefits`. Since then
the only change in the zone is the AC-1 fix (`isAdmin` wired on `/benefits`).

## Delegation
One reviewer (one zone), in a fresh context, read-only, with the skill's brief. Pre-read: the
README, the contributing guide, `docs/audits/categories.md`, `docs/audits/sweep-registry.md`
and the previous report, cited as closing AC-1 (fixed, guarded by a spec) and refusing AC-2
(informational). The reviewer returned two findings and nine examined-and-refused candidates;
the table shows the four refusals whose reasoning carries a lesson, the other five were duplicates
of AC-1 and AC-2 and are listed in the refused section by id only.
Every cited line was re-read directly and both findings were reproduced against a running
instance (app on a private port, database in a container named for this run, both stopped at
the end).

## Verification

| Finding | Zone | Verdict | Claimed | Verified | Reservations | Proof |
|---|---|---|---|---|---|---|
| AC-3 `/allocations/:userId` returns any user's allocations to any signed-in user | access-control | VERIFIED REAL | High | High | read-only; exposes full name and portfolio split, not credentials | `allocations_access_guard_spec.js`: 2 attack tests fail on current code, legitimate test passes; all 3 pass with the id taken from the session |
| AC-4 login does not regenerate the session id | access-control | OVER-RATED | Medium | Low | needs a way to plant the cookie; the reviewer's "no HttpOnly" claim is wrong (observed on `Set-Cookie`) | `session_fixation_guard_spec.js`: attack test fails, passes with `req.session.regenerate` |
| R-a `/benefits` admin gate bypass (AC-1 recheck) | access-control | FALSE POSITIVE | - | - | lens: claim correctness; both routes carry `isAdmin`, re-read from the database per request | existing guard spec passes |
| R-b self-promotion to admin | access-control | FALSE POSITIVE | - | - | lens: claim correctness; signup builds a fixed document, profile update sets named fields only | `app/data/user-dao.js:20` |
| R-d `/` has no middleware | access-control | FALSE POSITIVE | - | - | lens: existing mitigation; the handler checks the session itself | `app/routes/session.js:259` |
| R-h no CSRF protection | access-control | NEEDS DEEPER REVIEW | - | - | outside this run's question; proposed as its own zone | `server.js:104` |

AC-1 and AC-2 from the previous report were not re-reported. AC-1 rechecked: OK.

## Confirmed defects

### AC-3: object-level access control missing on `/allocations/:userId` (High)
- Location: `app/routes/allocations.js:18`
- Class: insecure direct object reference.
- Evidence chain:
  1. `app/routes/allocations.js:16-18` takes `userId` from `req.params`; line 23 passes it to
     the data layer, which queries `{userId: parseInt(userId)}` and attaches that user's name.
  2. Source: the URL segment of `GET /allocations/<id>`; ids are sequential integers.
  3. Mitigation absent: the route has `isLoggedIn` only (`app/routes/index.js:59`), which
     checks that a session exists, not whose data is asked for.
- Scenario: a signed-in employee opens their own allocations from the menu, changes the id in
  the URL, and reads a colleague's and the administrator's portfolio split.
- Fix approach: take `userId` from `req.session`, as `profile.js` and `contributions.js` do.
- Reproduction and guard: `test/e2e/integration/allocations_access_guard_spec.js`, both halves.
- Hand-off note: the existing `allocations_spec.js` browses another user's id and encodes the
  defect; the fix change must switch it to the signed-in user's own id.

## Low

### AC-4: session id not regenerated at login (Low, OVER-RATED from Medium)
- Location: `app/routes/session.js:116`
- Fix approach: wrap the login assignment in `req.session.regenerate`, as signup already does.
- Reproduction and guard: `test/e2e/integration/session_fixation_guard_spec.js`, both halves.

## Refused or unconfirmed candidates
- R-a, AC-1 bypass: refused, lens claim correctness (see table).
- R-b, self-promotion to admin: refused, lens claim correctness.
- R-d, `/` without middleware: refused, lens existing mitigation.
- R-h, no CSRF protection: decision pending; proposed as its own zone in the registry.
- R-c, R-e, R-f, R-g, R-i: duplicates of AC-1 or AC-2 under other names; refused with the
  previous report's reasoning, no new evidence.

## Coverage
Read and re-read at verification: the route index, the session, allocations, profile,
contributions and memos handlers, their data-access modules, `server.js`, the rendered views
and the existing specs for the zone. Skipped: handlers with no access-control logic.
Lenses applied: exploitability, claim correctness, existing mitigation.

## Hand-off
- Open AC-3 and AC-4 as separate changes, each with its reproduction spec.
- Run the proposed `csrf` and `input-handling` zones next; the `threshold` parameter on the same
  route reaches a `$where` clause and is not closed by the AC-3 fix.
