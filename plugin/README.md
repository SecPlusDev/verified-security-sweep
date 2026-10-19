# Verified Security Sweep

This plugin runs defensive security and correctness reviews of a codebase as a repeatable sweep:
it picks one zone, delegates the reading to a fresh-context reviewer, verifies every finding on
the cited lines, reproduces each confirmed finding with a failing test, and records the run in a
registry and a findings index, so the next run re-checks earlier findings instead of starting
from zero. It does not replace an audit. It reports, reproduces and proposes; the fixes go
through your normal review process.

## When it triggers

Ask in your own words; requests like these start a sweep or a fix verification:

- "we're launching the billing module next tuesday, it's an express app with postgres under
  services/billing. can you do a proper security pass on it before we ship?"
- "I patched the double-submit race on /api/invites/accept (see git diff --cached). before
  I commit, what did this fix break?"
- "review this PR please, it touches the session middleware and the org switch endpoint"

Implementation requests, such as adding rate limiting, and reviews of changes with no security
surface, such as a CSS cleanup, are left to Claude without the plugin.

Recommended on Opus and Sonnet, where it loads reliably. With it, Opus met 86% of the evaluation
checks and Sonnet 74%; without it, 24% and 16% (the round with baselines). The current version
meets 85% on Opus and 78% on Sonnet against the full check list, which now includes the
findings index, the recheck of earlier findings and the refusal of a recorded command that is
not the test runner. Those checks measure the method: exact locations, a reproduction per
finding, a reason for every refusal, the registry. Detection did not change: on the evaluation
code the models found the same real defects with or without it, and no confirmed finding was
false in any round. Known gap: leads the reviewer raises but the sweep does not verify are
recorded with their location, but often labelled "out of zone" instead of verified; read those
entries as unverified. It is not recommended on Haiku, which rarely loads it and did not follow
it reliably when it did; per-model figures are in the repository's `evals/results/`.

## What you get

- A dated report in `docs/audits/` of the target repository: verification table, confirmed
  defects with a single-line location and a three-part evidence chain, refused candidates with
  the reason, coverage, and hand-off.
- A registry row in `docs/audits/sweep-registry.md`, so the next run starts from the record.
- A reproduction test for each confirmed finding, in the target project's test folders.
- One line per confirmed finding in `docs/audits/findings.jsonl` (location, the exact code on
  that line, the reproduction command), which a later run re-checks and can write as SARIF.

## What this plugin runs and reads

- **Reads** the source code of the target repository, its rules file, and any previous reports in
  `docs/audits/`.
- **Runs** `python3 scripts/fresh_code.py`, which calls `git rev-parse` and `git log` in the target
  repository and reads the test files under its test folders, to rank recently changed files.
- **Runs** `python3 scripts/sweep_status.py`, which reads the report filenames and the registry in
  `docs/audits/` and prints which zones are stale.
- **Runs** `python3 scripts/check_citations.py <report>`, which reads the report and the files it
  cites and prints each cited line, so a wrong `file:line` is caught before the report ships.
- **Runs** `python3 scripts/check_report.py <report>`, which reads only the report and fails it
  when a section is missing, a verification row has no verdict, a refused entry has no
  disposition, or a line inside the zone's scope is cited only in the hand-off.
- **Runs** `python3 scripts/findings.py`, which reads `docs/audits/findings.jsonl`, the index of
  confirmed findings. `check` confirms each cited line holds the quoted code at the recorded
  commit. `recheck --run` runs the reproduction commands recorded in that index, without a shell,
  from the repository root, and with `--write` appends the results to
  `docs/audits/recheck-log.jsonl`. It refuses commands that start a shell or pass inline code to
  an interpreter, and the skill lists the commands and runs them only when they invoke the
  project's test runner. `sarif` prints the open findings as SARIF. Without `--run` nothing is
  executed.
- **Runs** `python3 scripts/leak_check.py`, which collects credential-like values from the target
  repository (dotenv values, literals next to secret names, DSN passwords, key-like tokens) and
  searches the report, the index and the new test files for them. It prints sources, lengths and
  masked context, never a value, and writes nothing.
- No script opens a network connection, and all use only the Python standard library. Apart
  from the recheck log, they write no files.
- **Runs** read-only `grep` searches from `references/stack-probes.md` to find places to read.
- **Writes** only under `docs/audits/` and in the target project's test folders. Fixes, changes to
  the rules file and any other edit are written in the report as proposals, never applied. It
  does not commit and does not run mutating git commands.
- **May start the target application and its database** to reproduce a finding, under a name or
  port specific to the run, and stops only what it started, by PID or container name. Starting
  them uses the target project's own tooling, which can install that project's dependencies or
  pull its container images; the plugin bundles no installer and downloads nothing itself.
- **Sends** no data outside the Claude session it runs in, and asks for no credentials.

Everything runs with the permissions of your Claude Code session; the plugin has no sandbox of
its own. Run it on a clone or a disposable checkout rather than the working tree you deploy from.

## License

MIT. Source, evaluations and security policy: https://github.com/SecPlusDev/verified-security-sweep
