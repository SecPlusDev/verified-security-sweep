# Management API: API-key authorization review

| | |
|---|---|
| Date | 2026-10-09 |
| Revision reviewed | `7a07141` (working tree, before the Friday release) |
| Scope | `hc/api/decorators.py`, `hc/api/views.py` (API-key endpoints), `hc/api/urls.py`, `Project.objects.for_api_key` / `Project.compare_api_key` in `hc/accounts/models.py`, `Check.to_dict` in `hc/api/models.py` |
| Question | Which key can read or change which checks? |
| Executable record | `hc/api/tests/test_api_key_authz.py` |
| Result | **3 authorization bugs, all release-blocking** (F-1, F-2, F-3). The other endpoints behave as intended. |

## 1. Key model

Each project has two keys:

* **read-write key**: stored in `Project.api_key`. New keys look like `hcw_` plus 28 chars, and the DB holds `secret[:8] + "." + HMAC(SECRET_KEY, key)`. Legacy keys are 32 plain-text chars.
* **read-only key**: stored in `Project.api_key_readonly`. New keys use the `hcr_` prefix, and legacy keys are plain text.

There are two decorators:

* `@authorize` accepts **only the read-write key**. It reads the key from the `X-Api-Key` header or from `api_key` in a JSON POST body. It sets `request.readonly = False`.
* `@authorize_read` accepts **either key**, from the header only. It sets `request.readonly` when the key starts with `hcr_` or equals the plain-text read-only key.

Both decorators reject any key that isn't 32 chars long. `for_api_key` does the lookup. Hashed keys are matched on an 8-char prefix and then checked with `hmac.compare_digest`. The `hcr_`/`hcw_` prefix decides which DB column is compared, so swapping the prefix on a secret doesn't work (tested).

**Intended policy**
1. A key only ever reaches checks in **its own project**.
2. A read-only key can only read. It must never create, change, pause, resume or delete checks, and it must never see a check's UUID or ping URL, because knowing the UUID lets you send pings. Read-only responses carry `unique_key` instead.

## 2. Endpoint matrix (as found)

Paths are relative to `/api/v1|v2|v3/`. "RO" means read-only key, "RW" means read-write key.

| Endpoint | Decorator | RO allowed | Project scoping | Verdict |
|---|---|---|---|---|
| `GET checks/` | authorize_read | yes (readonly dict) | `project__owner_id` | **F-1: leaks checks from the owner's other projects** |
| `POST checks/` (create/upsert) | authorize | no | `_lookup` filters by `project`; channels filtered by `check.project` | OK |
| `GET checks/<uuid>` | authorize_read | yes (readonly dict) | `check.project_id != request.project.id` → 403 | OK |
| `POST checks/<uuid>` (update) | authorize | no | project_id → 403; channels scoped | OK |
| `DELETE checks/<uuid>` | **authorize_read** | **yes** | project_id → 403 | **F-2: RO key can delete** |
| `GET checks/<unique_key>` | authorize_read | yes | `request.project.check_set` | **F-3: RO gets full RW dict (uuid, ping_url)** |
| `POST checks/<uuid>/pause` | authorize | no | project_id → 403 | OK |
| `POST checks/<uuid>/resume` | authorize | no | project_id → 403 | OK |
| `GET checks/<uuid>/pings/` | authorize | no | project_id → 403 | OK |
| `GET checks/<uuid>/pings/<n>/body` | authorize | no | project_id → 403; ping looked up by `owner=check` | OK |
| `GET checks/<uuid>/flips/` | authorize_read | yes | project_id → 403 (in `flips()`) | OK |
| `GET checks/<unique_key>/flips/` | authorize_read | yes | `request.project.check_set` | OK |
| `GET channels/` | authorize | no | `project=request.project` | OK |
| `GET badges/` | authorize_read | yes | `request.project.check_set` | OK |
| `GET metrics/` | `X-Metrics-Key` vs `settings.METRICS_KEY` | n/a | global counters only | OK (see N-2) |
| `GET status/`, `POST notifications/<uuid>/status`, `POST bounces/` | none (not API-key endpoints) | n/a | n/a | out of scope, noted only |

## 3. Findings

### F-1 (High): `GET /checks/` returns checks from every project of the same owner

`hc/api/views.py`, `get_checks`:

```python
q = Check.objects.filter(project__owner_id=request.project.owner_id)
```

Any key for project A, including the read-only key, lists the checks of **all projects owned by A's owner**. Those projects can be shared with different teams. With a read-write key, the response also includes each foreign check's `uuid`, `ping_url`, `update_url` and `channels`. That is enough to send fake pings to checks in other projects, which can suppress or trigger alerts. Update, delete and pause still return 403 because of the per-object project check. With a read-only key, the response leaks names, tags, descriptions, schedules, status and `unique_key` of the other projects' checks.

Fix: `q = Check.objects.filter(project=request.project)`.
Test: `test_finding_1_list_checks_is_scoped_to_project`.

### F-2 (High): read-only keys can delete checks

`hc/api/views.py`, `delete_check` is decorated with `@authorize_read` and never looks at `request.readonly`. `DELETE /api/vN/checks/<uuid>` with a read-only key (`hcr_…` or a legacy plain-text one) returns 200 and the check is deleted. Read-only keys are meant to be handed to dashboards and status pages. Check UUIDs are not secret from such holders: they appear in every ping URL in crontabs and scripts, and F-3 hands them out directly.

Fix: change the decorator to `@authorize`. A missing or read-only key then gets 401, matching update, pause and resume.
Tests: `test_finding_2_ro_key_cannot_delete`, `test_finding_2_legacy_ro_key_cannot_delete`.

### F-3 (Medium; raises F-2 to "anyone with the RO key can delete everything")

`hc/api/views.py`, `get_check_by_unique_key` returns `check.to_dict(v=request.v)` and ignores `request.readonly`. A read-only key therefore gets `uuid`, `ping_url`, `update_url`, `pause_url`, `resume_url` and `channels`.

Chained attack using only a read-only key:
1. `GET /checks/` returns every `unique_key`.
2. `GET /checks/<unique_key>` returns the `uuid` of each check.
3. `DELETE /checks/<uuid>` deletes each check (F-2). Step 2 also lets the attacker send pings.

Fix: `check.to_dict(readonly=request.readonly, v=request.v)`, the same as `get_check`.
Test: `test_finding_3_ro_key_unique_key_lookup_hides_uuid`.

### Notes (not blocking)

* **N-1.** The CORS policy on all API endpoints is `Access-Control-Allow-Origin: *` with `X-Api-Key` allowed. This is by design for a key-in-header API, and there are no cookies, so no CSRF exposure. Keep the key out of query strings.
* **N-2.** `metrics` compares `X-Metrics-Key` with `!=` rather than `hmac.compare_digest`. The timing risk is low and the endpoint exposes only global counters. It's a cheap hardening.
* **N-3.** `@authorize` also accepts the key in a JSON body (`api_key`), but `@authorize_read` does not. This is intentional because GETs have no body. It's harmless but worth knowing when adding endpoints.
* **N-4.** `@authorize_read` works out `readonly` from the key string, not from which DB column matched. This is correct today because the `hcr_`/`hcw_` prefix and the plain-text comparison fully determine the column. If key formats change, return the matched role from `for_api_key` instead.
* **N-5.** The existing suite (`hc/api/tests`, 438 tests) passes on this revision and does not cover any of F-1 to F-3. There is no test for RO delete, none for an owner with two projects, and none for an RO lookup by `unique_key`.

## 4. What was done

1. Read the two decorators, all `@authorize` / `@authorize_read` views, the URL routing (v1, v2 and v3 share one URL list), key lookup and hashing in `Project`, and `Check.to_dict` (the readonly vs read-write fields).
2. Built the matrix above, checking each view for the correct decorator, a `project_id` check on per-object access, and use of `request.readonly` when serializing.
3. Wrote `hc/api/tests/test_api_key_authz.py`. Every test asserts the **intended** policy, using hashed keys, legacy plain-text keys, a second project with the same owner, and a project with a different owner. Results on `7a07141`:
   * 7 control tests **pass**: RO key gets 401 on all read-write endpoints (header and body); forged and prefix-swapped keys are rejected; RO `get_check` hides the uuid; a read-write key gets 403 on every per-UUID endpoint for checks in other projects; create cannot attach a foreign channel.
   * 4 `test_finding_*` tests **fail**, which confirms F-1, F-2 and F-3.

No application code was changed. The fixes are the three one-line changes listed above.

## 5. Re-running for the next release

```sh
.venv/bin/python manage.py test hc.api.tests.test_api_key_authz
```

* Once F-1 to F-3 are fixed, all 11 tests should pass. Keep the file as a regression guard.
* When an endpoint is added under `hc/api/urls.py`, add a row to the matrix in section 2 and a case to the test file. Check three things: the decorator is right (`authorize` for anything that changes data), there is a per-object `project_id` check, and `to_dict(readonly=request.readonly, …)` is used.
* Quick grep for the risky patterns:
  `grep -n "authorize_read" -A3 hc/api/views.py` (no data changes should follow it),
  `grep -n "owner_id\|to_dict(v=" hc/api/views.py`.

## 6. Status log

| Date | Revision | Reviewer | Outcome |
|---|---|---|---|
| 2026-10-09 | 7a07141 | Claude Code (automated review) | F-1, F-2, F-3 open; tests added, 4/11 failing as expected |
