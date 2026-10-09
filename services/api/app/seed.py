"""Load the Brasaland supplier spreadsheet into TinyDB without duplicating rows."""

from dataclasses import dataclass
from pathlib import Path

from app.database import open_db, persist_supplier, suppliers_table, users_table
from app.models import Supplier
from app.users import create_user, get_user_by_email

# Dev/demo account for password-reset flows. Override in production.
SEED_USER_EMAIL = "lucia@brasaland.com"
SEED_USER_PASSWORD = "ChangeMe123!"

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
    try:
        stored_names = {row["name"] for row in table.all()}
        pending: list[dict] = []
        for record in SUPPLIERS_SEED:
            if record["name"] in stored_names:
                continue
            Supplier.from_client(record)
            pending.append(record)
            stored_names.add(record["name"])
        for record in pending:
            persist_supplier(table, record)
        return SeedResult(inserted=len(pending), total=len(table))
    finally:
        db.close()


@dataclass(frozen=True)
class UserSeedResult:
    inserted: bool
    email: str


def seed_users(db_path: Path | None = None) -> UserSeedResult:
    """Insert the demo user once (idempotent by email)."""
    db = open_db(db_path)
    table = users_table(db)
    try:
        if get_user_by_email(table, SEED_USER_EMAIL) is not None:
            return UserSeedResult(inserted=False, email=SEED_USER_EMAIL)
        create_user(table, email=SEED_USER_EMAIL, password=SEED_USER_PASSWORD)
        return UserSeedResult(inserted=True, email=SEED_USER_EMAIL)
    finally:
        db.close()


def main() -> None:
    result = seed_suppliers()
    users = seed_users()
    user_msg = (
        f"Inserted demo user {users.email}."
        if users.inserted
        else f"Demo user {users.email} already present."
    )
    print(
        f"Seed complete. Inserted {result.inserted} supplier(s). "
        f"{result.total} supplier(s) stored. {user_msg}"
    )


if __name__ == "__main__":
    main()
