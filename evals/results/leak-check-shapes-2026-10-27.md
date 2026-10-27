# leak_check.py by shapes against by values, 2026-10-27

Why: v1.4.1 is held by the plugin directory's automatic policy check, "Uses a credential from
the user's machine", for `leak_check.py` reading the repository's dotenv values and secret
literals. The hold has no exemption for a script that reads and never sends; a waiver was asked
for on 2026-10-21 and had no answer by 2026-10-27. The plugin's check is rewritten to scan the
deliverables for credential shapes and read no file of the repository. This file measures what
that costs, on the same inputs, before the change ships.

Both checks run from the same clone (`check_citations.py` shapes shared), Python 3.13, the
value-side script at `tools/leak_values.py` after the move.

## Planted report

A repository with four credentials of different shapes (`tests/test_scripts.py`,
`LEAK_VALUES`): a 5-letter admin password in a dotenv file, a 19-character app password of four
lowercase groups in a seed, a DSN with a 9-character password as a key default, and a 40-character
mixed-case API key. One report cites each value twice: once as the skill cites a line ("the line
reads: `ADMIN_PASSWORD=...`", `password="..."`, the `os.getenv` default, `API_KEY = "..."`), once
in prose without the name ("the admin logs in with ...", "the mailer uses ... as its app
password", "the fallback DSN is ...", "the key ... is committed").

| Cited as | By values (v1.4.1) | By shapes (v1.4.2) |
|---|---|---|
| L1 `ADMIN_PASSWORD=` + 5-letter word | WARN | WARN (value after `ADMIN_PASSWORD=`) |
| L2 `password="` + app password | FAIL | FAIL (literal next to `password`) |
| L3 `os.getenv("SECRET_KEY", "` + DSN | FAIL | FAIL (literal next to `SECRET_KEY`) |
| L4 `API_KEY = "` + key | FAIL | FAIL (literal next to `API_KEY`) |
| U1 the 5-letter word in prose | WARN | not seen |
| U2 the app password in prose | FAIL | not seen |
| U3 the DSN in prose | FAIL | FAIL (DSN password) |
| U4 the key in prose | FAIL | FAIL (key-like token) |
| Total | 6 FAIL, 2 WARN; 8 of 8 | 5 FAIL, 1 WARN; 6 of 8 |

No value appears in either output (asserted in the test). The two misses are the same kind: a
password of ordinary words, written in prose, without its name. The skill text now says to
write a credential as its name and its shape, which the shape check sees; the value check is
the one that catches a session ignoring that sentence.

A test file is scanned for the key-like and DSN shapes only: the tests the sweep adds log in
with invented passwords next to their names (`client.login(password="wrong-pw")`), and a shape
check cannot tell an invented word from a real one. The value check could, and did
(`test_leak_values_never_collects_from_the_deliverables_or_test_fixtures`). A weak real
password copied into a test next to its name is therefore the third thing the shape check does
not see.

## The real record

The 13-report record of the SCOPE series (`real-code-2026-10-19.md`: 18 files under
`docs/audits/`, 241 recheck lines), scanned from the shallow clone at `63b6843`.

| Step | FAIL | WARN | What the hits were |
|---|---|---|---|
| By values, v1.4.1 (reference) | 0 | 0 | 36 values collected from 355 files |
| By shapes, first run | 533 | 331 | every 40-character commit id in `recheck-log.jsonl` (WARN, "not a git object": the shallow clone lacks the later commits); every finding id with both cases (`2026-10-19-audit-chain/AC6`, FAIL as key-like) |
| + a dated or segmented identifier is not a key; a 40-character lowercase hexadecimal run is a commit id | 1 | 0 | `sensor_case_max_armed=50` (24 characters with an `=` inside, taken as base64 padding) |
| + `=` is padding only at the end of a token | 0 | 0 | |

The three rules entered `check_citations.py` (the first two) and `leak_check.py` (the commit
id), with tests, so the masking in the citation check gains them too: a finding id in a cited
line is no longer masked as a key.

## Both checks in CI

The Python 3.9 smoke runs both on a report that copies a dotenv value as `SECRET_KEY=...` and
expects both to fail; the suite runs both on the planted report above and on the report that
names variables only, where both pass.

## Decision

Ship the shape check in the plugin as v1.4.2; keep the value check in the repository as
`tools/leak_values.py` and run it in every evaluation round next to the plugin's, so the gap
measured here keeps being measured on real records. If the directory waives the hold, the value
check can return to the plugin (`docs/BUILD.md`, Deferred).
