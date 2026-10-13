"""Reproduction tests from docs/audits/2026-10-09-api-key-scope.md.

Each "attack" test fails on the code as audited and passes once the defect is
fixed. Each "legit" test passes on the code as audited and must keep passing
after the fix.
"""

from __future__ import annotations

from datetime import timedelta as td

from hc.accounts.models import Project
from hc.api.models import Check
from hc.test import BaseTestCase


class ApiKeyScopeAuditTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # Hashed keys, as issued by the current settings UI
        self.rw_key = self.project.set_api_key()
        self.ro_key = self.project.set_api_key_readonly()
        self.project.save()

        self.check = Check.objects.create(
            project=self.project, name="Alice 1", timeout=td(seconds=3600)
        )

        # A second project owned by Alice. Bob is a member of self.project only,
        # so neither self.project's keys nor Bob should see this project's checks.
        self.private = Project.objects.create(
            owner=self.alice, name="Alice Private", badge_key="alice-private"
        )
        self.private_check = Check.objects.create(
            project=self.private, name="Private 1", timeout=td(seconds=3600)
        )

    # F1: read-only key can delete a check

    def test_attack_readonly_key_cannot_delete_check(self) -> None:
        url = f"/api/v3/checks/{self.check.code}"
        r = self.client.delete(url, HTTP_X_API_KEY=self.ro_key)
        self.assertEqual(r.status_code, 401)
        self.assertTrue(Check.objects.filter(id=self.check.id).exists())

    def test_legit_write_key_can_delete_check(self) -> None:
        url = f"/api/v3/checks/{self.check.code}"
        r = self.client.delete(url, HTTP_X_API_KEY=self.rw_key)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Check.objects.filter(id=self.check.id).exists())

    # F2: list endpoint returns checks of every project with the same owner

    def test_attack_list_checks_is_scoped_to_key_project(self) -> None:
        for key in (self.rw_key, self.ro_key):
            r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=key)
            self.assertEqual(r.status_code, 200)
            names = {c["name"] for c in r.json()["checks"]}
            self.assertNotIn("Private 1", names)

    def test_legit_list_checks_returns_own_project_checks(self) -> None:
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=self.rw_key)
        names = {c["name"] for c in r.json()["checks"]}
        self.assertIn("Alice 1", names)

    # F3: lookup by unique_key returns the write-level view to a read-only key

    def test_attack_unique_key_lookup_hides_secrets_from_readonly_key(self) -> None:
        url = f"/api/v3/checks/{self.check.unique_key}"
        r = self.client.get(url, HTTP_X_API_KEY=self.ro_key)
        self.assertEqual(r.status_code, 200)
        doc = r.json()
        self.assertNotIn("uuid", doc)
        self.assertNotIn("ping_url", doc)
        self.assertNotIn("update_url", doc)

    def test_attack_readonly_chain_to_delete(self) -> None:
        # read-only key -> unique_key from list -> uuid from F3 -> delete via F1
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=self.ro_key)
        unique_key = r.json()["checks"][0]["unique_key"]
        r = self.client.get(
            f"/api/v3/checks/{unique_key}", HTTP_X_API_KEY=self.ro_key
        )
        uuid = r.json().get("uuid")
        if uuid:
            self.client.delete(f"/api/v3/checks/{uuid}", HTTP_X_API_KEY=self.ro_key)
        self.assertTrue(Check.objects.filter(id=self.check.id).exists())

    def test_legit_unique_key_lookup_with_write_key_returns_full_view(self) -> None:
        url = f"/api/v3/checks/{self.check.unique_key}"
        r = self.client.get(url, HTTP_X_API_KEY=self.rw_key)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["uuid"], str(self.check.code))
