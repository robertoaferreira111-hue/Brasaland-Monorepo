"""Exercise real API paths so capture writes genuine rows to Supabase.

Origin label: automated local HTTP via FastAPI TestClient (not human UI clicks).
Does not use SQL INSERT or synthetic seed rows.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

# Allow `uv run python scripts/...` from services/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

from app.errors import StorageError
from app.main import app


def main() -> None:
    operations: list[str] = []
    with TestClient(app) as client:
        # Technical: failed login (catalogue staff_login_failed)
        r = client.post(
            "/auth/login",
            json={"email": "gate-a-fail@brasaland.com", "password": "wrong-pass"},
        )
        operations.append(f"login_fail status={r.status_code}")

        # Technical: validation 422
        r = client.post("/auth/login", json={})
        operations.append(f"login_validation status={r.status_code}")

        # Technical: protected routes without auth
        r = client.get("/suppliers")
        operations.append(f"suppliers_unauth status={r.status_code}")
        r = client.get("/suppliers/1")
        operations.append(f"supplier_get_unauth status={r.status_code}")
        r = client.post(
            "/suppliers",
            json={
                "name": "x",
                "country": "Colombia",
                "currency": "COP",
                "categories": ["carne"],
                "rate_per_unit": 1,
                "status": "active",
                "contact_email": "a@b.co",
            },
        )
        operations.append(f"supplier_create_unauth status={r.status_code}")

        # Technical: invalid bearer
        r = client.get(
            "/suppliers",
            headers={"Authorization": "Bearer not-a-jwt"},
        )
        operations.append(f"suppliers_bad_token status={r.status_code}")

        # Register + login for business ops
        email = f"telemetry-{uuid.uuid4().hex[:8]}@brasaland.com"
        password = "demo-password"
        r = client.post(
            "/users",
            json={
                "email": email,
                "password": password,
                "name": "Telemetry Operator",
            },
        )
        operations.append(f"register status={r.status_code}")
        r = client.post(
            "/auth/login",
            json={"email": email, "password": password},
        )
        operations.append(f"login_ok status={r.status_code}")
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Business: supplier_created (two distinct creates)
        created_ids: list[int] = []
        for label, country, currency, category, rate in (
            ("Carnes del Valle", "Colombia", "COP", "carne", 18.5),
            ("Florida Greens LLC", "USA", "USD", "verduras_y_hortalizas", 4.25),
        ):
            r = client.post(
                "/suppliers",
                headers=headers,
                json={
                    "name": f"{label} {uuid.uuid4().hex[:6]}",
                    "country": country,
                    "currency": currency,
                    "categories": [category],
                    "rate_per_unit": rate,
                    "status": "active",
                    "contact_email": f"contact-{uuid.uuid4().hex[:6]}@example.com",
                },
            )
            operations.append(f"supplier_create:{label} status={r.status_code}")
            if r.status_code == 201:
                created_ids.append(r.json()["id"])

        # Business: rate + status change on first supplier
        if created_ids:
            sid = created_ids[0]
            r = client.patch(
                f"/suppliers/{sid}/rate",
                headers=headers,
                json={"rate_per_unit": 19.75},
            )
            operations.append(f"rate_change status={r.status_code}")
            r = client.patch(
                f"/suppliers/{sid}/status",
                headers=headers,
                json={"status": "suspended"},
            )
            operations.append(f"status_change status={r.status_code}")

        # Authenticated validation reject (422) — no invented event type
        r = client.post(
            "/suppliers",
            headers=headers,
            json={
                "name": "Bad Currency Co",
                "country": "Colombia",
                "currency": "USD",
                "categories": ["carne"],
                "rate_per_unit": 1,
                "status": "active",
                "contact_email": "bad@example.com",
            },
        )
        operations.append(f"supplier_validation status={r.status_code}")

        # Technical: storage_unavailable via temporary dependency failure
        import app.routers.suppliers as suppliers_mod

        original = suppliers_mod.get_table

        def broken_table():
            raise StorageError("Storage unavailable")
            yield  # pragma: no cover

        suppliers_mod.get_table = broken_table  # type: ignore[assignment]
        try:
            r = client.get("/suppliers", headers=headers)
            operations.append(f"storage_unavailable status={r.status_code}")
        finally:
            suppliers_mod.get_table = original

    print("OPERATIONS")
    for line in operations:
        print(line)


if __name__ == "__main__":
    main()
