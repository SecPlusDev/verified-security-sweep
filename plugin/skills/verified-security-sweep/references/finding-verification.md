# Verifying a candidate finding

Contents: The three lenses; Verdict vocabulary; Reservations hide inside "real"; Reproduce, do not reason; Classes that survive verification, and classes that do not; Worked example, generic.

A reviewer, human or agent, produces a mix of real defects, misreadings, and restatements of
controls that already exist. Before acting on any of them, attack each one from three angles.
Default to refusing when uncertain; confirm when the lenses hold after reading the cited lines.

## The three lenses

| Lens | Question | Refute when |
|---|---|---|
| Exploitability | Can a concrete actor reach the sink? Name the actor: "authenticated member of org A", "anyone with the public link", "the nightly cron". | The path is unreachable, requires the highest privilege already, is dev-only, or the "attacker" is the resource owner. |
| Claim correctness | Does the code at the cited `file:line` do what the finding says? | The line does something else; the "missing" guard is a few lines up, in the route, in middleware, or in a database constraint. |
| Existing mitigation | Is there a documented control (rules file, middleware, DB CHECK or UNIQUE, allow-list, escaper) that neutralizes it? | A baseline control blocks it. Record the control next to the refused candidate so it is not rediscovered. |

Read the cited lines yourself. A paraphrase such as "no ownership check on the update" is the
reviewer's model, and the lens that fails most often is claim correctness: the check exists, in
the route file the reviewer did not open.

## Verdict vocabulary

- `VERIFIED REAL`: all three lenses hold. Write the reproduction, then the report entry.
- `FALSE POSITIVE`: the claim-correctness lens fails. Record what the code does instead.
- `OVER-RATED`: real, lower severity. Typical causes: requires an already-privileged actor,
  display-only effect, window of milliseconds between two actions of the same owner.
- `NEEDS DEEPER REVIEW`: cannot be resolved from the handler and its route. Trace the data flow
  end to end before deciding; do not report it as real to be safe.

## Reservations hide inside "real"

When several skeptical reviewers vote on a finding, the declared refusal rate can drop by an
order of magnitude between runs while the reasons keep saying "real, but the severity is lower", "real, but
the scope is narrower", "real, but it is a display defect, not a data defect". A boolean verdict
swallows all of that: in the runs that were measured, most "real" verdicts carried a reservation
in their reasoning while the refusal flag moved by tens of points between runs.

So read the reasons, not the flag. A finding confirmed with reservations is re-verified by hand
before it appears in the report with the original severity. Phrases that mark a reservation:
"but", "however", "partially", "possibly", "overstated", "severity lower", "misclassified",
"the scope is".

Also: a reviewer that died or timed out is not a reviewer that refused. A quorum rule that
treats silence as refusal drops real findings from the report along with the noise. Count only
verdicts that were actually written.

## Reproduce, do not reason

For every `VERIFIED REAL`, write a test that fails on the current code. The defect is the
mutant. This is what turns a finding into something the team can act on without re-deriving
the argument.

Run it. When it cannot run here (the test runner is not installed, the database is not
available), say so wherever the test is cited: `written, not run: <reason>`, with the expected
result of each case (the attack path fails on the current code, the legitimate path passes). The
proof of the finding is then what was observed instead, for example a live request and its
response; if nothing was observed, the finding is `NEEDS DEEPER REVIEW`, not `VERIFIED REAL`.

A hard-coded credential is verified by its shape, never by its value. Decide whether a value is
real or a placeholder through booleans, lengths or shapes computed by a script (length, character
classes, the format of a known key type, equality with the value in another file), and put the
boolean in the report. Never print the value, in the session or in a test's output, and never
write a masking expression by hand for the purpose: in the run that produced this rule, the
hand-written expression was wrong and the value was printed. Never try the credential against the
service it belongs to; its validity is a reservation in the verification table, not a test. The
reproduction test reads the value at run time and compares, so the test file holds the variable
name and the shape, not the value, and `leak_check.py` confirms that nothing delivered holds a
value of that shape.

- Concurrency: an interleaving test (two requests racing on one token, two uploads racing on one
  quota, a cancel racing a payment). A fix for a race verified only by reading has been found
  incomplete when the interleaving test was finally written.
- Documents: generate the PDF, CSV or email and inspect the output (`pdftotext -layout` for PDFs;
  look for repeated labels, binary fields rendered as yes/no, the wrong calendar day).
- Time: set the clock near midnight in the deployment timezone and check that the legal day is
  the local one, not UTC.
- Public endpoints: the generic 404 on an invalid token must be byte-identical, and the response
  time must not depend on whether the record exists (send the response before doing the work).

## Classes that survive verification, and classes that do not

Observed across many sweeps, useful as a prior when triaging a long candidate list:

Survive most often:
- Check-then-act races on public one-shot endpoints (double submit of an invitation, two resets
  with one link, a cancel racing a mark-paid).
- Counters and quotas that count artifacts instead of facts (deleting the report frees the
  quota; archiving an item escapes the cap).
- Readers written before a data rule changed (a nullable score that the reader treats as zero;
  a derived column copied by a migration that nothing re-derives).
- Side channels on public paths (response time that differs by branch; a score returned on
  failure that works as an oracle).
- Labels whose predicate does not support them ("renewed" counted as "any payment", "public"
  counted without the hiding reason).
- The recovery path nobody exercises (restore without the post-restore script resurrects every
  revoked token).

Rarely survive:
- Escaping and injection claims where the project has a central escaper or strict
  parametrization; the lens that fails is existing mitigation.
- "Missing rate limit" when a global or gateway limiter exists.
- "Hardcoded secret" that is a placeholder refused at startup.
- Anything claimed from the controller alone without the route file.

## Worked example, generic

A reviewer flags four findings on a public invitation-accept endpoint: unescaped HTML in a
generated confirmation page, a missing rate limit, a missing audit log, and a double-submit race
on the acceptance. The first fails the existing-mitigation lens (the template engine escapes every
rendered string). The second fails the same lens (a route-level limiter is mounted in the app
entry point). The third fails exploitability as a defect (accepting writes its own event row,
which is the audit). The fourth survives all three: two concurrent accepts of one invitation
create two memberships and two welcome emails. Reproduction: two parallel requests with the same
token; both return 201. Fix: a uniqueness constraint on the accepted invitation, so the second
insert fails and is mapped to 409. Lesson: one in four survived, and it was the race, not the injection.
