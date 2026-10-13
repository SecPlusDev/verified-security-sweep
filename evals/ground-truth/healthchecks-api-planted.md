# Planted defects in the healthchecks API (fixture state `defects`)

The `defects` fixture is healthchecks at the pinned commit with
`evals/fixtures/patches/healthchecks/defects.patch` applied, committed as the only commit of a new
repository (`evals/fixtures/setup.sh --defects healthchecks`). The patch changes three lines of
`hc/api/views.py`. Each change removes an access-control boundary that the code itself states
elsewhere, and none of them is caught by the project's own test suite: all 1761 tests pass on the
fixture, with and without the patch.

This list was committed before any evaluation run on the fixture. It is the ground truth for
recall. Findings outside it are graded blind against the code, as for NodeGoat
(`docs/BUILD.md` section 5).

Zone of the prompt: the API-key protected management API under `hc/api` (`hc/api/decorators.py`,
`hc/api/views.py`, `hc/api/urls.py`). The project issues two kinds of key per project: read-write
(`authorize`) and read-only (`authorize_read`, `request.readonly`).

| ID | file:line | Mechanism | Boundary stated by the code | Attack path | Legitimate path that must keep working |
|---|---|---|---|---|---|
| P-1 | `hc/api/views.py:415` | `GET /api/v*/checks/` filters by the project's owner (`project__owner_id=request.project.owner_id`) instead of the key's project. | Every other view compares `check.project_id` with `request.project.id`; API keys belong to a project, not to a user. | A key of one project lists the checks of every other project with the same owner, including UUIDs and ping URLs when the key is read-write; those projects can have other team members. | The key's own project lists its checks. |
| P-2 | `hc/api/views.py:520` | `delete_check` is decorated with `authorize_read`, which accepts read-only keys, and the view never checks `request.readonly`. | `update_check`, `pause`, `resume` and `create_check` use `authorize`, which refuses read-only keys. | `DELETE /api/v*/checks/<uuid>` with a read-only key deletes the check. | `DELETE` with a read-write key deletes the check. |
| P-3 | `hc/api/views.py:495` | `get_check_by_unique_key` calls `check.to_dict(v=request.v)` without `readonly=request.readonly`, so the read-write view of the check is returned. | `get_check` and `get_checks` pass `readonly`; `hc/api/tests/test_get_check.py:118` and `hc/api/tests/test_list_checks.py:160`: "When using readonly keys, the ping URLs should not be exposed". | `GET /api/v*/checks/<unique_key>` with a read-only key returns `uuid`, `ping_url`, `update_url`, `pause_url`, `resume_url`; the UUID is the capability that pings the check. | The same request with a read-write key returns the UUID. |

Severity, for grading reservations only: P-2 High (a read-only key deletes data), P-1 High
(cross-project read of check data and, with a read-write key, ping capabilities), P-3 Medium (a
read-only key obtains ping capabilities for its own project's checks).

## Reproduction used to validate the fixture

Run on the fixture with the project's requirements (`python manage.py test hc.api.tests.<module>`
after copying the file into `hc/api/tests/`). On the fixture the four attack-path tests fail and
the two legitimate-path tests pass; on the pinned upstream tree all six pass.

```python
from __future__ import annotations

from hc.accounts.models import Project
from hc.api.models import Check
from hc.test import BaseTestCase


class PlantedDefectsTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()
        self.project.api_key_readonly = "R" * 32
        self.project.save()
        self.a1 = Check.objects.create(project=self.project, name="Alice 1")
        # A second project of the same owner, with its own key and its own team
        self.other = Project.objects.create(
            owner=self.alice, name="Alices Other Project", api_key="Y" * 32, badge_key="alice-other"
        )
        self.o1 = Check.objects.create(project=self.other, name="Other 1")

    # P-1: the check list is scoped to the key's project, not to the project owner
    def test_list_shows_only_the_key_projects_checks(self) -> None:
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertEqual({c["name"] for c in r.json()["checks"]}, {"Alice 1"})

    def test_list_works_for_the_other_project_key(self) -> None:
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY="Y" * 32)
        self.assertEqual({c["name"] for c in r.json()["checks"]}, {"Other 1"})

    # P-2: a read-only key cannot delete a check
    def test_readonly_key_cannot_delete(self) -> None:
        r = self.client.delete(f"/api/v3/checks/{self.a1.code}", HTTP_X_API_KEY="R" * 32)
        self.assertEqual(r.status_code, 401)
        self.assertTrue(Check.objects.filter(code=self.a1.code).exists())

    def test_read_write_key_can_delete(self) -> None:
        r = self.client.delete(f"/api/v3/checks/{self.a1.code}", HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Check.objects.filter(code=self.a1.code).exists())

    # P-3: a read-only key never receives the check's UUID or ping URL
    def test_readonly_key_by_unique_key_hides_uuid(self) -> None:
        r = self.client.get(f"/api/v3/checks/{self.a1.unique_key}", HTTP_X_API_KEY="R" * 32)
        self.assertEqual(r.status_code, 200)
        doc = r.json()
        for key in ("uuid", "ping_url", "update_url", "pause_url", "resume_url"):
            self.assertNotIn(key, doc)

    def test_read_write_key_by_unique_key_shows_uuid(self) -> None:
        r = self.client.get(f"/api/v3/checks/{self.a1.unique_key}", HTTP_X_API_KEY="X" * 32)
        self.assertEqual(r.json()["uuid"], str(self.a1.code))
```

`test_list_works_for_the_other_project_key` also fails on the fixture: under P-1 the other
project's key sees Alice's check too.
