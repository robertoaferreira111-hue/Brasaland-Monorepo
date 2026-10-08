"""Load the Brasaland supplier spreadsheet into TinyDB without duplicating rows."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from app.database import open_db, persist_supplier, suppliers_table
from app.errors import StorageError
from app.models import Supplier

SUPPLIERS_SEED = [
    {
        "name": "Carnes del Valle S.A.S.",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 28500.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@carnesdelvalle.co",
        "notes": "Primary beef and pork supplier for Medellín. Delivery Tuesday and Friday.",
    },
    {
        "name": "Frigorífico Antioqueño",
        "country": "Colombia",
        "categories": ["carne"],
        "rate_per_unit": 27900.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@frigorificoa.co",
        "notes": "Secondary supplier. Used when Carnes del Valle is out of stock.",
    },
    {
        "name": "Verduras La Cosecha",
        "country": "Colombia",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 3200.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "lacosecha@gmail.com",
        "notes": "Medellín wholesale market. Daily delivery before 7am.",
    },
    {
        "name": "Condimentos El Sabor",
        "country": "Colombia",
        "categories": ["salsas_y_condimentos"],
        "rate_per_unit": 12400.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "info@elsabor.co",
    },
    {
        "name": "Distribuidora RefriCol",
        "country": "Colombia",
        "categories": ["bebidas", "lacteos"],
        "rate_per_unit": 4100.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "refricol.pedidos@gmail.com",
    },
    {
        "name": "Empaques y Más",
        "country": "Colombia",
        "categories": ["packaging"],
        "rate_per_unit": 890.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "ventas@empaquesymas.co",
        "notes": "Supplies boxes, bags, and napkins for all Colombia locations.",
    },
    {
        "name": "Limpiahogar Profesional",
        "country": "Colombia",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 7600.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "limpiahogar@promail.co",
        "notes": "Suspended for delivery non-compliance. Under review by Lucía.",
    },
    {
        "name": "CarboCo",
        "country": "Colombia",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 45000.0,
        "currency": "COP",
        "status": "active",
        "contact_email": "pedidos@carboco.co",
        "notes": "Only approved charcoal supplier for the grills. Annual contract.",
    },
    {
        "name": "Miami Meat Distributors LLC",
        "country": "USA",
        "categories": ["carne"],
        "rate_per_unit": 6.80,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@miamimeat.com",
        "notes": "Primary meat supplier for Florida locations.",
    },
    {
        "name": "Sunshine Produce FL",
        "country": "USA",
        "categories": ["verduras_y_hortalizas"],
        "rate_per_unit": 2.15,
        "currency": "USD",
        "status": "active",
        "contact_email": "sales@sunshineproduce.com",
    },
    {
        "name": "Latin Flavors Inc.",
        "country": "USA",
        "categories": ["salsas_y_condimentos", "bebidas"],
        "rate_per_unit": 4.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@latinflavors.com",
        "notes": "Imports Colombian sauces for the Florida market.",
    },
    {
        "name": "PackRight USA",
        "country": "USA",
        "categories": ["packaging"],
        "rate_per_unit": 0.35,
        "currency": "USD",
        "status": "active",
        "contact_email": "info@packright.us",
    },
    {
        "name": "CleanPro Florida",
        "country": "USA",
        "categories": ["productos_limpieza"],
        "rate_per_unit": 12.90,
        "currency": "USD",
        "status": "active",
        "contact_email": "orders@cleanproflorida.com",
    },
    {
        "name": "GrillFuel Supply Co.",
        "country": "USA",
        "categories": ["carbon_y_combustible"],
        "rate_per_unit": 38.50,
        "currency": "USD",
        "status": "active",
        "contact_email": "supply@grillfuel.com",
        "notes": "Charcoal supplier for Florida. Price subject to quarterly review.",
    },
    {
        "name": "Bebidas Andinas",
        "country": "Colombia",
        "categories": ["bebidas"],
        "rate_per_unit": 3800.0,
        "currency": "COP",
        "status": "suspended",
        "contact_email": "ventas@bebidasandinas.co",
        "notes": "Suspended. Price above market after last renegotiation.",
    },
]


@dataclass(frozen=True)
class SeedResult:
    inserted: int
    total: int


def seed_suppliers(db_path: Path | None = None) -> SeedResult:
    """Insert context seed rows that are not already stored under the same name."""
    db = open_db(db_path)
    table = suppliers_table(db)
    inserted = 0
    try:
        stored_names: set[str] = set()
        for row in table.all():
            name = row.get("name")
            if isinstance(name, str) and name:
                stored_names.add(name)

        pending: list[dict] = []
        for record in SUPPLIERS_SEED:
            if record["name"] in stored_names:
                continue
            Supplier.from_client(record)
            pending.append(record)
            stored_names.add(record["name"])

        for record in pending:
            try:
                persist_supplier(table, record)
            except StorageError as exc:
                raise ValueError(
                    "could not write the supplier database after inserting "
                    f"{inserted} of {len(pending)} pending row(s). "
                    "Fix storage and re-run seed; existing names are skipped."
                ) from exc
            inserted += 1
        return SeedResult(inserted=inserted, total=len(table))
    except StorageError:
        raise
    except ValidationError as exc:
        raise ValueError(
            f"Seed data failed validation after inserting {inserted} row(s)."
        ) from exc
    except OSError as exc:
        raise StorageError("Storage unavailable") from exc
    finally:
        db.close()


def main(argv: list[str] | None = None) -> int:
    _ = argv  # CLI currently takes no arguments; reserved for compatibility.
    try:
        result = seed_suppliers()
    except StorageError:
        print(
            "Seed failed: could not read or write the supplier database. "
            "Check file permissions and try again.",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:
        print(f"Seed failed: {exc}", file=sys.stderr)
        return 1
    except Exception:
        print(
            "Seed failed due to an unexpected error. Check the database path and try again.",
            file=sys.stderr,
        )
        return 1

    print(
        f"Seed complete. Inserted {result.inserted} supplier(s). "
        f"{result.total} supplier(s) stored."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

