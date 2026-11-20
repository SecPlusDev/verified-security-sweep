# Verifying a fix adversarially

Contents: Fresh context is the method; Step 1 blast radius; Step 2 over-restriction; Step 3 collateral regressions; Step 4 invariants covering the touched area; Step 5 propose the guard; Output; Verdict calibration; When the fix needs another round; Coupled fixes; What this does not do; A note on silent CI.

Run this after a fix is written and before it is committed. The question is not "is the finding
resolved?"; the answer to that is always yes, because whoever wrote the fix is checking their own
solution. The question is **"what did this fix break?"**

## Fresh context is the method

If you wrote the fix in the current session, you carry the mental model that produced it,
including its wrong assumptions. Ask for a new session, or treat the diff as code written by
someone you do not know. Allowed inputs, nothing else:

- the diff (`git diff` or `git diff --cached`)
- the text of the original finding
- the code around the touched area
- on a second or later round, the earlier rounds' verification reports and this round's diff
  (see "When the fix needs another round")

Do not read the reasoning that led to the fix. You are there to reproduce it independently.

Reading is the baseline; running is allowed and sometimes decisive. Make a throwaway copy of
the tree outside the repository, apply the diff there, and run what the claim needs: the
suite, a long simulation, a lossy link, a busy sender. Every claim in the output says whether
it was **run** (with the command and the result) or **read**; a claim marked neither is a
guess. In the one measured case, a read-only first round's predictions held, and rounds two to
five found their most important problems only by running: an hour of lossy traffic in a copy
showed a retry cap losing frames on a stable connection that no reading would have predicted.

## Step 1: blast radius

```bash
git diff --cached --name-only
git diff --cached --stat
```

For every changed symbol (function, export, type, column, middleware), find every caller:

```bash
grep -rn "symbolName" src/ tests/
grep -rn "from.*moduleName" src/
```

Each caller is a path the fix can break. List them explicitly. An unverified caller is a new
finding that appears in two weeks. Cases to check every time:

- **middleware added**: which routes now pass through it that should not?
- **query changed**: which other call sites depend on the old shape of the result?
- **delete or cascade**: what still hangs off the removed row (files, archived documents,
  foreign keys)?
- **filter added**: which legitimate data disappears from the response?
- **lock added**: is anything with external latency (email, HTTP, PDF rendering) now inside the
  lock? Does a second lock elsewhere create a cycle?
- **token or step made single-use**: does the tolerance window still work (a previous, valid,
  unconsumed step must still be accepted)?

## Step 2: over-restriction

The most common way a fix does harm is not leaving the hole open. It is **closing the hole and
the legitimate path together**. For every gate, guard or check added, answer both:

1. Is the attack case blocked? (obvious, always checked)
2. Does the legitimate case still pass? (almost never checked)

The usual shape: a check added at the entry of a handler to stop one abusive request also stops a
legitimate request that shares the entry point, for example a plan check meant for writes that
also blocks the reads which must stay open on an expired plan.

Both claims are tested, not assumed.

## Step 3: collateral regressions

A fix that moves code around tends to drop things that were implicit:

- An audit or log entry that used to be inside the transaction is now outside it, and a comment
  still claims it is inside.
- An error key the new branch returns does not exist in the translation files.
- A migration the fix depends on is not in the regenerated schema, or its checksum is not
  registered.
- A fire-and-forget call swallows its error with an empty catch, where every sibling logs it.
- A lock key chosen per row when the invariant is per person, per email or per tenant.

## Step 4: which invariants cover the touched area

List the guard tests (`tests/guards/` or the team's equivalent) that cover the touched zone and
run only those:

```bash
ls tests/guards/
npx jest tests/guards/<relevant> --silent
```

If the diff touches a zone with no guard at all, that is the main finding of the verification,
more important than anything else found.

## Step 5: propose the guard

The verification ends with a test proposed for the guards folder that asserts two things:

```ts
describe('guard: <the invariant, in words>', () => {
  it('blocks the attack path', async () => { /* ... */ });
  it('lets the legitimate path through', async () => { /* ... */ });
});
```

Both. A guard that tests only the first half lets over-restriction through unnoticed. Name the
file after the invariant, not the bug: `org-scoping.test.ts`, not `fix-1234.test.ts`. The
invariant survives; the issue number says nothing in six months.

## Output

Short, in this order, no preamble (the author knows what they wrote):

- **Verdict:** `CLEAN` / `RISK` / `BROKEN`
- **Unverified callers:** `file:line` list, or "none"
- **Over-restriction:** the legitimate path that may be blocked, named by the code that walks
  it (`file:line` of the caller, view or spec), or "not applicable"
- **Guard coverage:** which guard tests touch the zone; if zero, say so
- **Proposed guard:** the test, written, ready to drop in

## Verdict calibration

The sweep brief calibrates severity; the verification uses the same scale, so that a list of
small items does not come back as `BROKEN`:

- `BROKEN`: at least one High or Medium problem, by the sweep's severities: a legitimate path
  closed, a new hole opened, an original reproduction edited to pass.
- `RISK`: Low items only (a stricter input rule than the code needs, a drifted statistic, a
  comment that no longer matches), each one for the owner to accept or fix.
- `CLEAN`: nothing to report. Over-restriction and unverified callers are never `CLEAN`.

Each problem carries its severity, so the author sees what must change before merge and what
can be a follow-up.

## When the fix needs another round

A `BROKEN` verdict sends the fix back to its author. The next round is a new verifier in a
fresh context again, never the one that wrote the report: a verifier that reviews the response
to its own findings checks its own reasoning. Its inputs are the ones above plus the earlier
rounds' verification reports and the diff of this round only, so it sees what was asked, what
changed in answer, and can tell a problem fixed from a problem moved. The author replies to
every item of the earlier report by its number: fixed (and where), accepted (and why), or
disputed (and the evidence). A verdict is asked per group of findings when the change spans
several (see "Coupled fixes"), so a `BROKEN` on one group does not hide a `CLEAN` on another.

Stop when a round returns `CLEAN` or `RISK`, with the Low items listed for the owner. A fix
that needs a fourth or fifth round because each round's new mechanism opens a new problem is a
fix whose design is wrong, not a fix with bugs: in the measured case the rounds ended when
several special cases were replaced by one propagation model, not when the last bug was
patched. Say so in the report when the pattern appears.

Record the rounds in the report that proposes the fix, one row each: round, verdict overall and
per group, problems by severity, guard tests proposed and adopted. The rows are what a reader
needs to trust the final verdict, and what makes a fix that took five rounds look like what it
was rather than like a fix that passed once.

## Coupled fixes

The hand-off proposes one change per finding group so that each is verifiable on its own. When
the groups share state (one cache, one rate budget, one sync path), a partial fix cannot be
verified: the half that is missing is itself a blocked path or an open hole. Then the fix is one
change, the verification runs on the combined diff, and the verdict is given per group, with
the shared state named in the report so a reader knows why the groups travel together.

## What this does not do

- It does not rewrite the fix. If it is broken, report and stop. A one-line change the verifier
  tried in its throwaway copy and ran against every guard may be proposed with the evidence;
  the author applies it, the verifier does not.
- It does not run the whole suite as a substitute for the targeted checks above; the suite is
  the pre-commit step, and a verifier that runs it in a copy still reports its own findings.
- It does not commit. The only file it may write in the repository is the guard, and only when
  asked.

## A note on silent CI

When a PR shows no checks at all, the first question is not "did CI fail" but whether the PR is
mergeable. A PR in conflict with the base branch never triggers the `pull_request` workflow,
because the platform cannot build the merge commit it runs against; there is no error message.
It looks exactly like a repository that ran out of CI minutes. Rebase first, then look at CI.
