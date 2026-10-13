# Review of a run on real code

For a run on a codebase the reviewer knows well and that is not part of this repository. The
filled form stays with the reviewer; only the counts and the answers to 7 and 8 are published, with
no detail of the code.

Fill it before reading anything else about the run's quality, and fix the decision rule first.

| | |
|---|---|
| Codebase (private label) | |
| Zone | |
| Model, skill version, date | |
| Duration, usage | |

1. **Confirmed findings.** For each: real / not real / unsure. Counts: ___ / ___ / ___
2. **Known misses.** Defects in the zone the reviewer already knew of that the run did not report: ___
3. **Locations.** `check_citations.py` exit code: ___; `findings.py check` exit code: ___; confirmed
   findings whose location opens on the line a fix would change: ___ of ___
4. **Dismissed candidates.** Dismissed for a sound reason: ___ of ___; real defects among them: ___
5. **Noise.** Items in the report the reviewer would delete: ___ of ___
6. **Reproduction tests.** Run in the reviewer's environment: ___ of ___; fail for the reason stated: ___
7. **Hand-over.** Would the reviewer accept this report from a colleague: as is / with edits / no
8. **Resume.** Would the next review start from this record (registry, index): yes / no, because ___
9. **Time.** The reviewer's estimate of the same review done by hand: ___
10. **One change** the reviewer would make to the skill: ___

Decision rule, fixed before the run: the run counts as useful when no confirmed finding is "not
real", question 7 is "as is" or "with edits", and noise (question 5) is at most one item in five.
