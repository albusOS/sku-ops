"""Supply Yard company configuration — single source of truth for org, departments, and dev user."""

from pydantic import BaseModel


class SeedOrg(BaseModel):
    id: str
    name: str
    slug: str


class SeedDepartment(BaseModel):
    name: str
    code: str
    description: str = ""


class SeedUser(BaseModel):
    email: str
    password: str
    name: str
    role: str


# ── Organization ──────────────────────────────────────────────────────────────

ORG = SeedOrg(id="supply-yard", name="Supply Yard", slug="supply-yard")

# ── Departments (58 — from Hike POS product types) ───────────────────────────

DEPARTMENTS = [
    SeedDepartment(name="Adhesives", code="ADH"),
    SeedDepartment(name="Appliances", code="APP"),
    SeedDepartment(name="Automotive", code="AUT"),
    SeedDepartment(name="Bathroom Material", code="BAM"),
    SeedDepartment(name="Bathroom Supplies", code="BAS"),
    SeedDepartment(name="Building Materials", code="BLD"),
    SeedDepartment(name="Caulk", code="CAU"),
    SeedDepartment(name="Cleaning", code="CLN"),
    SeedDepartment(name="Concrete", code="CON"),
    SeedDepartment(name="Door Repair", code="DRP"),
    SeedDepartment(name="Doors", code="DOR"),
    SeedDepartment(name="Drywall Mud", code="DRM"),
    SeedDepartment(name="Drywall Supplies", code="DRS"),
    SeedDepartment(name="Electrical", code="ELE"),
    SeedDepartment(name="Electrical - Cords", code="ELC"),
    SeedDepartment(name="Electrical - Wire", code="ELW"),
    SeedDepartment(name="Fans", code="FAN"),
    SeedDepartment(name="Fasteners", code="FAS"),
    SeedDepartment(name="Flooring", code="FLO"),
    SeedDepartment(name="Fuel", code="FUE"),
    SeedDepartment(name="HVAC", code="HVA"),
    SeedDepartment(name="HVAC - Filters", code="HVF"),
    SeedDepartment(name="Hand Tool Accessories", code="HTA"),
    SeedDepartment(name="Hand Tools", code="HTL"),
    SeedDepartment(name="Handles and Knobs", code="HNK"),
    SeedDepartment(name="Handrail", code="HRL"),
    SeedDepartment(name="Home Protection", code="HPR"),
    SeedDepartment(name="Insulation", code="INS"),
    SeedDepartment(name="Keys", code="KEY"),
    SeedDepartment(name="Landscaping Supplies", code="LND"),
    SeedDepartment(name="Light Bulbs", code="LBL"),
    SeedDepartment(name="Light Fixtures", code="LFX"),
    SeedDepartment(name="Locks/Knobs", code="LOK"),
    SeedDepartment(name="Lubes", code="LUB"),
    SeedDepartment(name="Lumber", code="LUM"),
    SeedDepartment(name="Mailboxes", code="MBX"),
    SeedDepartment(name="Masonry", code="MAS"),
    SeedDepartment(name="Miscellaneous", code="MSC"),
    SeedDepartment(name="Miscellaneous Parts", code="MSP"),
    SeedDepartment(name="Paint Products", code="PNT"),
    SeedDepartment(name="Paint Supplies", code="PNS"),
    SeedDepartment(name="Pest Control", code="PST"),
    SeedDepartment(name="Plumbing - Fittings", code="PLF"),
    SeedDepartment(name="Plumbing - Fixtures", code="PLX"),
    SeedDepartment(name="Plumbing - Gas", code="PLG"),
    SeedDepartment(name="Plumbing - General", code="PLM"),
    SeedDepartment(name="Plumbing - Pipe", code="PLP"),
    SeedDepartment(name="Plumbing - Sink Repair", code="PSR"),
    SeedDepartment(name="Plumbing - Sinks", code="PSK"),
    SeedDepartment(name="Plumbing - Toilet Repair", code="PTR"),
    SeedDepartment(name="Power Tool Accessories", code="PTA"),
    SeedDepartment(name="Power Tools", code="PWR"),
    SeedDepartment(name="Roofing Supplies", code="ROF"),
    SeedDepartment(name="Safety", code="SAF"),
    SeedDepartment(name="Small Appliances", code="SMA"),
    SeedDepartment(name="Trash Cans", code="TRS"),
    SeedDepartment(name="Window", code="WIN"),
    SeedDepartment(name="Winter", code="WNT"),
]

# Name → code lookup for import scripts
DEPT_CODE_BY_NAME = {d.name: d.code for d in DEPARTMENTS}

# ── Dev user (local auth only — not for production) ──────────────────────────

DEV_USER = SeedUser(
    email="dev@supply-yard.local",
    password="dev123",  # noqa: S106
    name="Dev Admin",
    role="admin",
)

DEV_CONTRACTOR = SeedUser(
    email="contractor@supply-yard.local",
    password="dev123",  # noqa: S106
    name="Dev Contractor",
    role="contractor",
)
