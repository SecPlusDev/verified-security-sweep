# Defensive audit sweep: api-key-scope, 2026-10-09

## Context

Scope: the API-key protected management API under `hc/api`, question "which key can read or
change which checks". Files: `hc/api/decorators.py`, `hc/api/urls.py`, `hc/api/views.py` (the
API-key views), and the key lookup it depends on, `ProjectManager.for_api_key` and
`Project.compare_api_key` in `hc/accounts/models.py`; `Check.to_dict` in `hc/api/models.py` for
what each key level is shown.

Trigger: owner request, pre-release check before the Friday release.

Branch `main`, single commit `7a07141` ("Import service source for the release review"), clean
working tree, no diff against main. `fresh_code.py` listed no file changed in the last three
days, so there was no fresh-code zone to prefer. First sweep in this repository: `docs/audits/`
was bootstrapped in this run (`categories.md`, `sweep-registry.md`, `coverage-matrix.md`). No
previous reports, no `docs/specs/`. The rules file is `CONTRIBUTING.md`; it states no security
baseline beyond "add a test", so the baseline controls were taken from the code itself (listed in
`categories.md`).

Key model, as audited: each project has a read-write key (`api_key`, issued as `hcw_...`) and a
read-only key (`api_key_readonly`, issued as `hcr_...`); both are stored as `<8 chars>.<HMAC>`, and
legacy 32-character plain-text keys are still accepted. `authorize` accepts only the read-write
key (`hc/api/decorators.py:59`); `authorize_read` accepts either and sets `request.readonly`
(`hc/api/decorators.py:82`). A key is scoped to one project, not to the owner's account.

## Delegation

No reviewer was delegated. The zone is a single small one (three files of about 1,200 lines plus
two model methods), so the reading was done directly, as the skill allows for a single small
zone. Consequence for the reader: the reading is not independent of the verification. The
reproduction tests below are the independent check; each confirmed finding has a test that
fails on the current code.

## Verification

| Finding | Zone | Verdict | Claimed | Verified | Reservations | Proof |
|---|---|---|---|---|---|---|
| F1 read-only key can delete a check | api-key-scope | VERIFIED REAL | High | High | needs the check uuid; a read-only key obtains it through F3 | `test_attack_readonly_key_cannot_delete_check`, ran, fails as expected (200 != 401, check deleted); `test_attack_readonly_chain_to_delete`, ran, fails as expected |
| F2 list endpoint returns checks of every project of the same owner | api-key-scope | VERIFIED REAL | High | High | only projects with the same owner; another owner's projects stay hidden | `test_attack_list_checks_is_scoped_to_key_project`, ran, fails as expected ('Private 1' found) |
| F3 lookup by unique_key gives a read-only key the read-write view | api-key-scope | VERIFIED REAL | Medium | Medium | own project only; impact is the ping URL and uuid, which escalate to F1 | `test_attack_unique_key_lookup_hides_secrets_from_readonly_key`, ran, fails as expected (uuid, ping_url, update_url present) |
| R1 CORS `*` on key-authenticated endpoints | api-key-scope | FALSE POSITIVE | Medium | - | lens: existing mitigation | no ambient credential |
| R2 key accepted from the JSON body | api-key-scope | FALSE POSITIVE | Low | - | lens: claim correctness | `hc/api/decorators.py:51` |
| R3 plain-text lookup matches a stored hash | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/api/decorators.py:56` |
| R4 8-character prefix lookup returns a wrong project | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/accounts/models.py:412` |
| R5 read-only flag derived from the `hcr_` prefix | api-key-scope | FALSE POSITIVE | Medium | - | lens: exploitability, fails safe | `hc/api/decorators.py:88` |
| R6 flips by uuid fetch any project's check | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/api/views.py:650` |
| R7 lookup by unique_key crosses projects | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/api/views.py:493` |
| R8 create/update assigns another project's channels | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/api/views.py:330` |
| R9 update, pause, resume cross projects | api-key-scope | FALSE POSITIVE | High | - | lens: claim correctness | `hc/api/views.py:502` |
| R10 no rate limit on wrong API keys | api-key-scope | FALSE POSITIVE | Medium | - | lens: exploitability | `hc/accounts/models.py:550` |
| R11 404 vs 403 reveals a uuid exists in another project | api-key-scope | FALSE POSITIVE | Low | - | lens: exploitability | `hc/api/views.py:482` |

Calibration: 3 of 14 candidates confirmed, no severity lowered, 3 confirmed verdicts carry a
reservation (all narrow the scope, none changes the class).

## Confirmed defects

### F1. Read-only API key can delete checks (High)

- Location: `hc/api/views.py:520` (the decorator on `delete_check`).
- Class: key privilege (read-only key performs a write).
- Evidence chain:
  1. `delete_check` is decorated with `@authorize_read` (`hc/api/views.py:520`) and calls
     `check.rename_and_delete()` (`hc/api/views.py:528`).
  2. `authorize_read` accepts the read-only key (`hc/api/decorators.py:82`) and only records
     `request.readonly`; `delete_check` never reads that flag.
  3. Every other mutating view uses `@authorize`, which rejects read-only keys
     (`hc/api/decorators.py:59`): `update_check` (`hc/api/views.py:499`), `pause`
     (`hc/api/views.py:546`), `resume` (`hc/api/views.py:573`), `create_check`
     (`hc/api/views.py:438`). The routing (`hc/api/urls.py:50`, dispatch in `single` at
     `hc/api/views.py:539`) sends `DELETE checks/<uuid>` straight to it.
- Scenario: a read-only key is handed out for a status dashboard or embedded in the read-only
  dashboard URL (`Project.dashboard_url`). Whoever holds it calls `GET /api/v3/checks/` to get
  each `unique_key`, `GET /api/v3/checks/<unique_key>` to get the uuid (F3), then
  `DELETE /api/v3/checks/<uuid>`, and deletes every check of the project; monitoring stops
  silently.
- Fix approach: decorate `delete_check` with `@authorize`, like `update_check` two views above.
- Reproduction: `hc/api/tests/test_audit_api_key_scope.py`
  - `test_attack_readonly_key_cannot_delete_check`: expects 401 and the check still present;
    on the current code it gets 200 and the check is gone. Ran, fails as expected.
  - `test_attack_readonly_chain_to_delete`: read-only key alone, list, unique_key lookup,
    delete. Ran, fails as expected (check deleted).
  - `test_legit_write_key_can_delete_check`: read-write key deletes. Ran, passes.

### F2. `GET /api/vN/checks/` lists checks from every project of the key's owner (High)

- Location: `hc/api/views.py:415`.
- Class: project isolation.
- Evidence chain:
  1. `get_checks` builds its queryset with `Check.objects.filter(project__owner_id=request.project.owner_id)`
     (`hc/api/views.py:415`): every check of every project owned by the same user.
  2. The key identifies one project (`hc/api/decorators.py:86`); every other view scopes to
     `request.project` (`hc/api/views.py:475`, `hc/api/views.py:483`, and
     `hc/api/views.py:695` for badges via `request.project.check_set`).
  3. No later filter narrows to the project. With a read-write key, `to_dict` includes each
     foreign check's `ping_url` and `update_url` (`hc/api/models.py:475`).
- Scenario: Alice owns "Production" and "Private". Bob is a team member of "Production" only and
  has its read-write key (or a CI job holds it). `GET /api/v3/checks/` with that key returns the
  checks of "Private" too, including their ping URLs, which Bob can then ping to make failing
  jobs look healthy. With a read-only key the foreign checks' names, schedules, tags, keyword
  filters and status leak.
- Fix approach: `Check.objects.filter(project=request.project)`, the same scoping as `channels`
  (`hc/api/views.py:475`).
- Reproduction: `test_attack_list_checks_is_scoped_to_key_project` (both key levels), ran,
  fails as expected ('Private 1' returned). `test_legit_list_checks_returns_own_project_checks`,
  ran, passes. The existing `test_it_shows_only_users_checks` in
  `hc/api/tests/test_list_checks.py` only covers another owner's project, which is why it passes.

### F3. Lookup by unique_key returns the read-write view to a read-only key (Medium)

- Location: `hc/api/views.py:495`.
- Class: secrets in responses / key privilege.
- Evidence chain:
  1. `get_check_by_unique_key` returns `check.to_dict(v=request.v)` (`hc/api/views.py:495`);
     `readonly` defaults to `False` (`hc/api/models.py:439`).
  2. With `readonly=False`, `to_dict` adds `uuid`, `ping_url`, `update_url`, `pause_url`,
     `resume_url` and `channels` (`hc/api/models.py:474`).
  3. The view is `@authorize_read` (`hc/api/views.py:491`), so read-only keys reach it; the
     sibling `get_check` passes `readonly=request.readonly` (`hc/api/views.py:486`), and so does
     `get_checks` (`hc/api/views.py:433`). The existing `test_readonly_key_works` in
     `hc/api/tests/test_get_check.py` only tests the uuid route.
- Scenario: a read-only key holder lists checks (gets `unique_key`, which read-only listings are
  meant to expose instead of the uuid), then looks each one up by `unique_key` and receives the
  ping URL. Sending success pings to it masks real failures; the uuid enables F1.
- Fix approach: `check.to_dict(readonly=request.readonly, v=request.v)`, as in `get_check`.
- Reproduction: `test_attack_unique_key_lookup_hides_secrets_from_readonly_key`, ran, fails as
  expected (`uuid`, `ping_url`, `update_url` in the response).
  `test_legit_unique_key_lookup_with_write_key_returns_full_view`, ran, passes.

Run command: `.venv/bin/python manage.py test hc.api.tests.test_audit_api_key_scope` gives
7 tests, 4 failures (the four attack tests), 3 passes (the legitimate paths).

## Refused or unconfirmed candidates

- R1, CORS `Access-Control-Allow-Origin: *` on API views (`hc/api/decorators.py:112`): refused,
  lens existing mitigation. Authentication is the `X-Api-Key` header or a body field, never a
  cookie, so a foreign origin has no ambient credential to ride.
- R2, `authorize` takes the key from the JSON body (`hc/api/decorators.py:51`): refused, lens
  claim correctness. Only on POST, same 32-character check and same lookup as the header; it is
  the documented legacy way to pass the key.
- R3, the plain-text branch of `for_api_key` (`hc/accounts/models.py:426`) could match a stored
  hash: refused, lens claim correctness. Stored hashes are 72 characters (8 + "." + 64 hex,
  `hc/accounts/models.py:556`) and the decorators reject any key whose length is not 32
  (`hc/api/decorators.py:56`).
- R4, the hashed lookup filters by an 8-character prefix (`hc/accounts/models.py:411`) and could
  pick a wrong project: refused, lens claim correctness. Each candidate is confirmed by
  `compare_api_key` (`hc/accounts/models.py:412`), an HMAC of the full key compared with
  `hmac.compare_digest` (`hc/accounts/models.py:592`).
- R5, `request.readonly` is derived from the `hcr_` prefix (`hc/api/decorators.py:88`): refused,
  lens exploitability. The prefix only routes to the read-only hash branch, which compares
  against `api_key_readonly` (`hc/accounts/models.py:583`); a legacy read-write plain key that
  happened to start with `hcr_` would be treated as read-only, which fails safe.
- R6, `flips_by_uuid` fetches the check by uuid without a project filter (`hc/api/views.py:676`):
  refused, lens claim correctness. `flips()` returns 403 when the project differs
  (`hc/api/views.py:650`).
- R7, `get_check_by_unique_key` and `flips_by_unique_key` could cross projects: refused, lens
  claim correctness. Both iterate `request.project.check_set` (`hc/api/views.py:493`,
  `hc/api/views.py:684`). The defect in that view is F3, not scoping.
- R8, `create_check`/`update_check` could attach another project's channels: refused, lens claim
  correctness. Channels are resolved only among `Channel.objects.filter(project=check.project)`
  (`hc/api/views.py:323`, `hc/api/views.py:330`); `_lookup` is scoped to `request.project`
  (`hc/api/views.py:300`).
- R9, `update_check`, `pause`, `resume`, `pings`, `ping_body` could act on another project's
  check: refused, lens claim correctness. Each compares `check.project_id` with
  `request.project.id` before acting (`hc/api/views.py:502`, `hc/api/views.py:549`,
  `hc/api/views.py:576`, `hc/api/views.py:598`, `hc/api/views.py:628`).
- R10, no rate limit on wrong API keys: refused, lens exploitability. Issued keys carry
  `token_urlsafe(21)`, 28 random characters (`hc/accounts/models.py:550`); guessing is not
  feasible. Legacy plain keys are out of the operator's control here (see hand-off).
- R11, `get_object_or_404` before the project check returns 404 vs 403, revealing that a uuid
  exists in some project (`hc/api/views.py:482`): refused, lens exploitability. Check uuids are
  random UUID4; an attacker who already has a uuid gains nothing from learning it exists.

## Coverage

Read in full: `hc/api/decorators.py`, `hc/api/urls.py`, `hc/api/views.py` (all API-key views;
the unauthenticated views were read only to place them out of zone),
`ProjectManager.for_api_key`, `Project._make_api_key`, `set_api_key`, `set_api_key_readonly`,
`compare_api_key` in `hc/accounts/models.py`, `Check.to_dict` and `Check.unique_key` in
`hc/api/models.py`. Existing tests read: `test_get_check.py`, `test_delete_check.py`,
`test_list_checks.py`, fixtures in `hc/test.py`.

Checked, no defect: `channels` and `pings`/`ping_body` require the read-write key (stricter than
reads elsewhere, by design); `badges` scoped to `request.project`; `authorize` rejects non-object
JSON bodies.

Key-to-endpoint matrix as audited (R = read-only key accepted, W = read-write key accepted):
list checks R/W (F2: owner-wide), get check R/W, get by unique_key R/W (F3), create W, update W,
delete R/W (F1), pause W, resume W, pings W, ping body W, flips R/W, channels W, badges R/W.

Not in scope: `ping`, `ping_by_slug`, `notification_status`, `bounces`, `metrics`, `status`,
`badge`, `check_badge` (authenticated by other secrets or not at all), `hc/integrations/prometheus`,
the web UI in `hc/front`, session auth and team roles in `hc/accounts`.

Lenses applied to every candidate: exploitability, claim correctness, existing mitigation.
Probes: the Django probes from the skill were adapted (no DRF here); the useful one was "every
`get_object_or_404(Check, ...)` followed by a project comparison", which every view satisfies.

## Hand-off

Proposals, not changes. The sweep wrote only `docs/audits/` and
`hc/api/tests/test_audit_api_key_scope.py`; nothing was committed.

1. Fix F1, F2 and F3 before the release, in one change through the normal process, with
   `hc/api/tests/test_audit_api_key_scope.py` shipped alongside (its attack tests turn green):
   - `hc/api/views.py:520`: `@authorize_read` to `@authorize`.
   - `hc/api/views.py:415`: filter by `project=request.project`.
   - `hc/api/views.py:495`: pass `readonly=request.readonly`.
2. Guard test to adopt: a table-driven test over every route in `api_urls` that asserts (a) a
   read-only key gets 401 on every non-GET method, (b) a key of project A never sees or changes
   a check of project B with the same owner, (c) no response to a read-only key contains `uuid`
   or `ping_url`. All three defects here are of classes that only a sentence protected.
3. Proposed sweeps of other zones (no verdict, not counted here), recorded in
   `docs/audits/sweep-registry.md`: `metrics` compares `X-Metrics-Key` with `!=`
   (`hc/api/views.py:860`); unauthenticated callbacks and slug auto-provisioning
   (`hc/api/views.py:262`); `hc/integrations/prometheus/views.py:50`.
4. Owner decision pending: whether legacy 32-character plain-text API keys should still be
   accepted (`hc/accounts/models.py:422`), or rotated to hashed keys before the release.
5. First run: propose a one-line pointer in `CONTRIBUTING.md` (or a rules file) to
   `docs/audits/`, so the next release starts from the registry and this report.
