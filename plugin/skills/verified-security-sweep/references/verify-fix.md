# Verifying a fix adversarially

Contents: Fresh context is the method; Step 1 blast radius; Step 2 over-restriction; Step 3 collateral regressions; Step 4 invariants covering the touched area; Step 5 propose the guard; Output; What this does not do; A note on silent CI.

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

Do not read the reasoning that led to the fix. You are there to reproduce it independently.

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

## What this does not do

- It does not rewrite the fix. If it is broken, report and stop.
- It does not run the whole suite; that is the pre-commit step.
- It does not commit. Verification is reading; the only file it may write is the guard, and only
  when asked.

## A note on silent CI

When a PR shows no checks at all, the first question is not "did CI fail" but whether the PR is
mergeable. A PR in conflict with the base branch never triggers the `pull_request` workflow,
because the platform cannot build the merge commit it runs against; there is no error message.
It looks exactly like a repository that ran out of CI minutes. Rebase first, then look at CI.
