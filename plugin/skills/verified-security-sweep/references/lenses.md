# Zones and lenses, with observed yield

A zone is what you point a sweep at; a lens is the question you ask inside it. The same zone
read with a different lens finds different defects. Yield is confirmed findings over verified
candidates in the run; it is the only criterion that has proved useful for deciding "worth
running again".

The numbers below come from roughly thirty sweeps on one multi-tenant SaaS over five months.
Treat them as priors, not promises. The registry of your own project replaces them after a few
runs.

## Zones by observed yield

Yield bands: **high** means most verified candidates were confirmed on the first run and the zone
stayed productive on re-runs; **medium** means a meaningful share confirmed, dropping on re-runs;
**exhausts** means a first pass confirms many and a second pass finds little, so the zone becomes
a periodic report rather than a sweep.

| Zone | What it covers | Yield | Why |
|---|---|---|---|
| **Fresh code** (shipped in the last 1 to 3 days) | whatever changed, read with transversal lenses | high, every time measured | the author's assumptions are still in the code; no guard exists yet |
| **Money** (billing, plans, quotas, invoices, accounting crons) | error paths and concurrency | high | no mechanical invariant by nature; a bug costs directly |
| **Documents** (PDF, CSV, email that leaves the system) | what is printed vs the data model | high, and high again weeks later | no guard checks what is on paper; the zone does not self-clean |
| **Concurrency** (races, idempotency, double submit, state machines without compare-and-set) | interleavings | high on re-run even after fixes | no invariant by construction; single-use tokens and state transitions regress |
| **Public surface** (no-auth endpoints, capability URLs, intake forms) | enumeration, limiting, leakage, side channels, tenant state | medium, high on re-run | the first pass fixes enumeration; later passes find timing and oracles |
| **Operator console** (super-admin, back office) | "the predicate does not support the label" | high | counts are arithmetically right and semantically wrong |
| **Time** (dates, timezones, deadlines) | UTC day vs local day | recurs until a guard exists | `toISOString().slice(0,10)` is the whole class |
| **Migrations** | idempotency, schema drift, deploy order, restore | high when asked what the guard does NOT cover | a guard that checks tables, columns and indexes misses triggers, functions, constraints, defaults |
| **User journey** (first login to first value, as a path) | the path, not the endpoints | high, then exhausts | a path sweep sees what per-endpoint sweeps cannot |
| **Frontend** (rendering, state, forms, plan-gated actions) | behavior on screen; both directions of a gate (disabled buttons tied to a plan, mutations without a write check) | high | weakest mechanical coverage; verification needs rendering, not reading |
| **Inventories that contradict** (the same set kept in two places, one tracked mechanically and one read by humans; UI claims made without asking the source) | status fields vs prose, exception lists vs what they match, detectors for the class | medium, then exhausts | changes update metadata and leave the prose; the class is wider than any detector |
| **Dead surface** (styles, routes, files nothing consumes) | things nothing consumes | exhausts after two runs | run twice, then make it a report |

## Lenses that transfer across zones

Use these inside any zone. They are the questions, phrased so a reviewer can answer them from
the code.

1. **Does the predicate support the label?** For every number or status shown to a human
   ("renewed", "public", "at risk", "compliant"), read the query. The count is usually right;
   the word above it is usually wider than the query.
2. **Facts or artifacts?** For every quota or cap, what is counted: rows that still exist, or
   events that happened? Deleting or archiving the row must not free the quota.
3. **Who else reads this?** For every data rule that changed (a nullable score, a renamed state,
   a new exclusion regime), list every reader written before the change. They were right then.
4. **Where is the lock relative to the check?** A count or EXISTS placed next to `FOR UPDATE`
   reads the snapshot from before the wait. The check belongs in the statement after the lock.
5. **Does the gate ask the same question as the transaction?** When a middleware gate says yes
   and the in-transaction re-check says no, one of them is counting differently.
6. **What does the response time say?** On a public path, does the early-return branch (revoked,
   throttled, not found) take measurably less time than the normal one?
7. **What happens on the recovery path?** Restore from backup, re-run of a migration, replay of
   a cron: does anything revoked come back to life?
8. **Which day is it?** Every date with legal or contractual meaning is the local day of the
   deployment, not the container's UTC day.
9. **Is the pair covered?** A public link lives on two paths (the SPA route and the API route).
   Scrubbing, limiting and 404 behavior must cover both.
10. **Does the UI mirror the server gate?** A button the server will refuse should not be
    rendered as enabled, and not as disabled-with-hover either; the reason belongs once per page.
11. **What is copied that should be derived?** A value computed from a rule and stored in a
    column becomes a second source of truth the moment the rule changes.
12. **What does the guard not cover?** For every mechanical invariant, write down its blind
    spots before sweeping the zone it protects. The findings are in the blind spots.

## Writing a new zone into the registry

A registry row has four hand-written fields: the zone slug, the argument (why this zone, why now),
the yield observed, and what the run explicitly did not cover. The last-run date is derived from
report filenames by `scripts/sweep_status.py`. Proposals for sweeps go in the registry, not in
conversation: three or four candidates discussed in a chat yield one run and three forgotten
ideas.

Before starting a proposed sweep, re-verify its premise in the code. A zone proposed one week can
be closed the next by unrelated fixes, and the session would be spent on debt already paid.
