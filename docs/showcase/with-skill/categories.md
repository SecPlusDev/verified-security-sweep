# Audit categories

Categories the sweeps verify, not patterns. A new pattern lands under an existing category.
"Covered by" names the project's own control; "Enforced mechanically?" says whether a test
guards it. When text and guard diverge, the guard is right.

| Category | Covered by in this project | Enforced mechanically? |
|---|---|---|
| API key authentication | `hc/api/decorators.py` `authorize` (read-write keys only) and `authorize_read` (read-write or read-only keys); `Project.objects.for_api_key` in `hc/accounts/models.py`; hashed `hcw_`/`hcr_` keys compared with HMAC and `hmac.compare_digest` | Partly: `hc/api/tests/test_auth.py`; read-only rejection on mutating endpoints not guarded before 2026-10-09 (see `hc/api/tests/test_audit_api_key_scope.py`) |
| Key privilege (read-only vs read-write) | each view picks `authorize` or `authorize_read`; `Check.to_dict(readonly=...)` hides uuid, ping and update URLs from read-only keys | Partly: `test_readonly_key_works` in `test_get_check.py` and `test_list_checks.py`; no table-driven guard over all endpoints |
| Project isolation (tenant = project) | every view filters by `request.project` or compares `check.project_id != request.project.id` | Partly: `test_it_shows_only_users_checks` covers another owner's project, not another project of the same owner |
| Session authentication and team roles | `hc/accounts`, `hc/front` (not yet swept) | |
| Secrets in responses | ping URLs and check uuids are write capabilities; never returned to read-only keys | No (sentence only) |
| Input validation | pydantic `Spec` with `strict=True` in `hc/api/views.py`; URL converters in `hc/api/urls.py` | Yes, per-field tests in `test_create_check.py`, `test_update_check.py` |
| SQL construction | Django ORM throughout | |
| Signed public links | badges (`hc/lib/badges.py`), bounce ids (`hc/lib/signing.py`) | |
| Unauthenticated callbacks | `notification_status`, `bounces`, ping endpoints | |
| Concurrency | `Check.rename_and_delete`, `update_fields` saves in `_update` | |
| Spec drift | API docs under `templates/docs/` vs `hc/api/views.py` | No |
