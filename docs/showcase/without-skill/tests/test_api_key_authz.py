"""API key authorization matrix for the management API (hc/api).

Written for the security review recorded in docs/security/api-key-authz-review.md.
Every test asserts the *intended* behaviour: a key may only act on checks in
its own project, and a read-only key may never change or delete anything, nor
learn a check's UUID / ping URL.

Tests named test_finding_* fail on the reviewed revision (7a07141) and pass
once the corresponding finding in the review document is fixed.
"""

from __future__ import annotations

from hc.accounts.models import Project
from hc.api.models import Channel, Check
from hc.test import BaseTestCase


class ApiKeyAuthzTestCase(BaseTestCase):
    def setUp(self) -> None:
        super().setUp()

        # Hashed keys, as created by the current UI
        self.rw_key = self.project.set_api_key()
        self.ro_key = self.project.set_api_key_readonly()
        self.project.save()

        # Legacy plain-text keys on a second project
        self.legacy = Project.objects.create(
            owner=self.charlie,
            api_key="L" * 32,
            api_key_readonly="R" * 32,
            badge_key="legacy",
        )

        # A second project owned by the same user (Alice), with its own key
        self.alice2 = Project.objects.create(
            owner=self.alice, name="Alice 2", badge_key="alice2"
        )
        self.alice2_key = self.alice2.set_api_key()
        self.alice2.save()

        self.check = Check.objects.create(project=self.project, name="mine")
        self.other = Check.objects.create(project=self.alice2, name="other")
        self.foreign = Check.objects.create(project=self.charlies_project, name="x")
        Channel.objects.create(project=self.project, kind="email", value="a@b.c")

    def call(self, method: str, path: str, key: str):  # type: ignore[no-untyped-def]
        if method == "post":
            return self.client.post(
                path, "{}", content_type="application/json", HTTP_X_API_KEY=key
            )
        return getattr(self.client, method)(path, HTTP_X_API_KEY=key)

    def url(self, check: Check, suffix: str = "") -> str:
        return f"/api/v3/checks/{check.code}{suffix}"

    # --- Key resolution -------------------------------------------------

    def test_ro_key_cannot_use_rw_only_endpoints(self) -> None:
        for method, path in [
            ("post", "/api/v3/checks/"),
            ("get", "/api/v3/channels/"),
            ("post", self.url(self.check)),
            ("post", self.url(self.check, "/pause")),
            ("post", self.url(self.check, "/resume")),
            ("get", self.url(self.check, "/pings/")),
            ("get", self.url(self.check, "/pings/1/body")),
        ]:
            for key in (self.ro_key, "R" * 32):
                r = self.call(method, path, key)
                self.assertEqual(r.status_code, 401, f"{method} {path} {key[:4]}")

    def test_ro_key_cannot_be_sent_in_body(self) -> None:
        r = self.client.post(
            "/api/v3/checks/",
            {"api_key": self.ro_key, "name": "x"},
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 401)

    def test_hashed_key_with_wrong_secret_is_rejected(self) -> None:
        forged = self.rw_key[:12] + "a" * 20
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=forged)
        self.assertEqual(r.status_code, 401)

    def test_rw_prefix_on_ro_secret_is_rejected(self) -> None:
        forged = "hcw_" + self.ro_key[4:]
        r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=forged)
        self.assertEqual(r.status_code, 401)

    def test_ro_key_gets_readonly_representation(self) -> None:
        for key in (self.ro_key,):
            r = self.client.get(self.url(self.check), HTTP_X_API_KEY=key)
            self.assertEqual(r.status_code, 200)
            self.assertNotIn("uuid", r.json())
            self.assertNotIn("ping_url", r.json())

    # --- Cross-project access --------------------------------------------

    def test_rw_key_cannot_touch_foreign_check_by_uuid(self) -> None:
        for check in (self.other, self.foreign):
            for method, suffix in [
                ("get", ""),
                ("post", ""),
                ("delete", ""),
                ("post", "/pause"),
                ("post", "/resume"),
                ("get", "/pings/"),
                ("get", "/pings/1/body"),
                ("get", "/flips/"),
            ]:
                r = self.call(method, self.url(check, suffix), self.rw_key)
                self.assertEqual(r.status_code, 403, f"{method} {suffix}")
        self.assertTrue(Check.objects.filter(code=self.other.code).exists())

    def test_create_check_cannot_attach_foreign_channel(self) -> None:
        foreign = Channel.objects.create(project=self.alice2, kind="email")
        r = self.client.post(
            "/api/v3/checks/",
            {"name": "n", "channels": str(foreign.code)},
            content_type="application/json",
            HTTP_X_API_KEY=self.rw_key,
        )
        self.assertEqual(r.status_code, 400)

    def test_finding_1_list_checks_is_scoped_to_project(self) -> None:
        # F-1: GET /checks/ filters by project owner, not by project
        for key in (self.rw_key, self.ro_key):
            r = self.client.get("/api/v3/checks/", HTTP_X_API_KEY=key)
            names = {c["name"] for c in r.json()["checks"]}
            self.assertEqual(names, {"mine"})

    # --- Read-only key privilege boundary ---------------------------------

    def test_finding_2_ro_key_cannot_delete(self) -> None:
        # F-2: DELETE /checks/<uuid> is wrapped in @authorize_read
        for key in (self.ro_key,):
            r = self.client.delete(self.url(self.check), HTTP_X_API_KEY=key)
            self.assertEqual(r.status_code, 401)
        self.assertTrue(Check.objects.filter(code=self.check.code).exists())

    def test_finding_2_legacy_ro_key_cannot_delete(self) -> None:
        check = Check.objects.create(project=self.legacy)
        r = self.client.delete(self.url(check), HTTP_X_API_KEY="R" * 32)
        self.assertEqual(r.status_code, 401)
        self.assertTrue(Check.objects.filter(code=check.code).exists())

    def test_finding_3_ro_key_unique_key_lookup_hides_uuid(self) -> None:
        # F-3: GET /checks/<unique_key> ignores request.readonly
        path = f"/api/v3/checks/{self.check.unique_key}"
        r = self.client.get(path, HTTP_X_API_KEY=self.ro_key)
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("uuid", r.json())
        self.assertNotIn("ping_url", r.json())
        self.assertNotIn("update_url", r.json())
