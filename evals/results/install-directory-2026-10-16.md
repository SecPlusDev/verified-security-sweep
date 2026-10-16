# Install from the Claude directory, 2026-10-16

The plugin as a user gets it after the listing went live on 2026-10-16: installed from the
directory into a Claude Code configuration created for the check, compared with the v1.4.0
release, then run once on the planted-defects fixture. Run by the owner on the owner's machine,
Claude Code 2.1.301, Linux, model `claude-opus-5-5`. The owner's own configuration was not
touched: `CLAUDE_CONFIG_DIR` pointed at an empty directory for every command below.

## Result: PASS, both parts

| Part | Outcome |
|---|---|
| 1. The installed copy is the release | PASS: identical tree, identical archive digest |
| 2. A natural request on the installed copy | PASS: 9 of 9 assertions of eval 5, 3 of 3 planted defects |

## Part 1: the installed copy is the release

The directory appears in Claude Code as a built-in marketplace, `anthropic-plugin-directory`
("Anthropic Directory" in `/plugin`). The listing page inside Claude Code reads "Installs exactly
commit 90a73a1, the commit the Anthropic Directory lists", version 1.4.0. The install was done
once from that page (`/plugin`, Discover, "Install for you (user scope)") and once from the
command line:

```bash
claude plugin install verified-security-sweep@anthropic-plugin-directory
```

| Check | Result |
|---|---|
| `claude plugin list` | `verified-security-sweep@anthropic-plugin-directory`, `Version: 1.4.0-90a73a192b40`, scope user, enabled |
| Where the files landed | `<config>/plugins/cache/anthropic-plugin-directory/verified-security-sweep/1.4.0-90a73a192b40/`; nothing under the account's own `~/.claude` |
| Skill loaded from the installed copy | `.../skills/verified-security-sweep/SKILL.md` under that path; the five scripts answered `--help` from `.../scripts/` with exit code 0 |
| `diff -r --brief <tag v1.4.0: plugin/> <installed copy>` | no file differs; two extra entries in the installed copy, neither from the release: `.in_use/<pid>`, Claude Code's marker that the running session uses the plugin, and `scripts/__pycache__/`, written by the `--help` runs of this check because they used `python3 -I`, which ignores `PYTHONDONTWRITEBYTECODE` (removed afterwards) |
| `package_skill.py --root <installed skill folder>` | `43b85f314afcd6efe26ac35d100762a28ca1aaa5f2ac9a2937a01a706558e77f`, 12 files, the v1.4.0 digest of `docs/BUILD.md` section 6 |
| `plugin.json` of the installed copy | `"version": "1.4.0"` |

The repository's `main` had moved on by two commits (the feedback-channel note and a Dependabot
bump of a CI action) when this ran; the installed copy is the tagged commit, not `main`, as the
listing says.

## Part 2: a natural request on the installed copy

Project copy: `healthchecks` at the defects state (`7a07141`, three planted defects, no
`docs/audits/`), clean before the run. New session started in the copy with the test
configuration, no MCP servers. Prompt: the eval 5 prompt of `evals/evals.json` with `<repo>`
replaced by `.`; the skill was not named. About 15 minutes; token use was not recorded. The
first tool call was not checked in the transcript this time.

Graded after the run against the nine assertions of eval 5 and the three fixed readings of
`docs/BUILD.md` section 5, then against `evals/ground-truth/healthchecks-api-planted.md`:

| # | Assertion | Result |
|---|---|---|
| 1 | Bootstrap: `docs/audits/` with categories, registry and a dated report | PASS |
| 2 | Report `docs/audits/2026-10-16-api-key-scope.md`, slug names the zone, template sections | PASS, all seven sections |
| 3 | Exact `file:line` and a three-part evidence chain; every cited line holds the described code | PASS: `check_citations.py` 40 citations, 0 not OK, including lines of `templates/docs/api.md` and of the project's own tests |
| 4 | VERIFIED REAL findings with a reproduction test and its run status | PASS: each row "ran, fails as expected" with the failing assertion quoted, each guard "ran, passes"; the command and its result (7 tests, 3 failures, 4 passes) written in the report |
| 5 | Every examined and unconfirmed candidate carries a disposition | PASS: R1 refused (exploitability), R2 see below, R3 refused (existing mitigation); all three in the Verification table with a verdict, none labelled "out of zone" |
| 6 | Registry row matches the report; `sweep_status.py --check` exit 0 | PASS: 1 zone, 1 dated report, 0 divergent, 0 stale |
| 7 | Tree differs only under `docs/audits/` and the test folder | PASS: `git diff --stat` empty; `git status --short` shows `docs/` and `hc/api/tests/test_review_api_key_scope.py` only |
| 8 | `findings.jsonl` complete and `findings.py check` exit 0 | PASS: 3 entries at `7a07141`, `hc/api/views.py:520`, `:415`, `:495`, each line holds its snippet |
| 9 | Recorded commands use the project's test runner, no shell | PASS: `.venv/bin/python manage.py test hc.api.tests.test_review_api_key_scope.<Class>` for reproduce and guard |

`check_report.py`: 6 verification rows (3 VERIFIED REAL), 3 refused entries, 3 hand-off
citations, 0 problems, exit 0. The hand-off cites the three in-zone lines next to their finding
ids, which is the allowed form.

Against the ground truth: recall 3 of 3, precision 1.00, severities as planted.

| Report | Ground truth | Line | Severity (report / planted) |
|---|---|---|---|
| F1, read-only key deletes checks | P-2 | `hc/api/views.py:520` | High / High |
| F2, check list scoped to the owner, not the key's project | P-1 | `hc/api/views.py:415` | High / High |
| F3, get-by-unique_key returns the read-write fields to a read-only key | P-3 | `hc/api/views.py:495` | Medium / Medium |

The test file pairs each attack class with a guard class, asserts on status codes, on the
database and on the raw response body (the UUID absent from the whole body, not only from the
JSON keys), and depends on nothing beyond the project's `BaseTestCase`. The report records the
owner decision F2 depends on (keys scoped per project, as the documentation says, or per owner)
as "decision pending", and proposes two further zones in the registry.

One reviewer subagent with a fresh context; verification, reproduction and the report by the
session itself. No permission failure; nothing outside the record and the test folder changed.

### Observation: R2 is internally inconsistent

Candidate R2 (`METRICS_KEY` compared with `!=`, `hc/api/views.py:860`) has verdict `OVER-RATED`
in the Verification table with `Claimed` Low and `Verified` Low, and its entry in the refused
section reads "refused as a finding of this zone, lens exploitability (verdict OVER-RATED, kept
as Low)". Two things do not fit. `OVER-RATED` is defined as "real, lower severity"
(`references/finding-verification.md`), so `Verified` must be below `Claimed`; here they are
equal. And the refused section's four dispositions (refused with a lens, needs deeper review,
closed earlier, out of zone) have no word for a candidate that is real at a lower severity and
not `VERIFIED REAL`; the run bridged the gap with a bracket. On the code, R2 is the same class
as R1 (a non-constant-time comparison that is not exploitable over the network), and R1 took
`FALSE POSITIVE`, lens exploitability; the same verdict fit R2. The grade is unaffected: the
candidate has a verdict and a disposition, and it is not confirmed. First occurrence; recorded
in `docs/BUILD.md` section 7 as a candidate rule for `check_report.py` and a vocabulary gap for
the next skill text version, to be settled on more data, not on one run.

## What this measures

That the directory delivers the release unchanged, that a configuration directory isolates the
install, and that a natural request on the installed copy produces the same record as the
graded rounds. It extends `install-2026-10-13.md`, which loaded the plugin through
`--plugin-dir` from a clone, to the path a user takes after the listing.
