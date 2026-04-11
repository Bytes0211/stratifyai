"""Generate 1000 rows of synthetic accounting data as a CSV."""

import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

VENDORS = [
    "Acme Office Supplies",
    "TechVault Solutions",
    "Summit Logistics",
    "Greenfield Energy",
    "Pinnacle Manufacturing",
    "Atlas Cloud Services",
    "Meridian Consulting",
    "Cornerstone IT",
    "Vanguard Equipment Co",
    "Evergreen Facilities",
    "Horizon Telecom",
    "Sterling Furniture",
    "Nexus Software",
    "Ironclad Security",
    "BlueSky Marketing",
    "Pacific Fleet Services",
    "Redwood Analytics",
    "Granite Construction",
    "Apex Janitorial",
    "Catalyst Training Group",
    "Metro Print & Copy",
    "Silverline Insurance",
    "Trident HVAC Systems",
    "Oasis Water Services",
    "Phoenix Data Centers",
    "Keystone Legal Services",
    "Harbor Freight Supplies",
    "Crestview Landscaping",
    "Quantum Electronics",
    "Bridgeport Packaging",
]

PAYMENT_STATUSES = ["Paid", "Pending", "Overdue", "Partial", "Scheduled"]

DEPRECIATION_METHODS = [
    "Straight-Line",
    "Double Declining Balance",
    "Sum-of-Years-Digits",
    "Units of Production",
    "MACRS",
]

ASSET_PREFIXES = {
    "IT": ["Laptop", "Server", "Monitor", "Printer", "Router", "Switch"],
    "VH": ["Truck", "Van", "Forklift", "Company Car"],
    "FF": ["Desk", "Chair", "Filing Cabinet", "Conference Table"],
    "EQ": ["Generator", "Compressor", "CNC Machine", "HVAC Unit"],
    "BL": ["Office Renovation", "Warehouse Expansion", "Parking Lot"],
}


def random_date(start_year: int, end_year: int) -> datetime:
    start = datetime(start_year, 1, 1)
    end = datetime(end_year, 12, 31)
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def generate_row(row_num: int) -> dict:
    vendor = random.choice(VENDORS)
    acq_date = random_date(2019, 2026)
    discount_due = acq_date + timedelta(days=random.choice([10, 15, 30, 45]))
    category = random.choice(list(ASSET_PREFIXES.keys()))
    asset_name = random.choice(ASSET_PREFIXES[category])
    useful_life = random.choice([3, 5, 7, 10, 15, 20])
    cost_basis = random.randint(500, 250_000)
    salvage_pct = random.uniform(0.05, 0.20)

    return {
        "Vendor Name": vendor,
        "Invoice Number": f"INV-{random.randint(100000, 999999)}",
        "Purchase Order (PO) ID": f"PO-{random.randint(10000, 99999)}",
        "Payment Status": random.choice(PAYMENT_STATUSES),
        "Discount Due Date": discount_due.strftime("%Y-%m-%d"),
        "Asset ID": f"{category}-{row_num:04d}",
        "Asset Description": asset_name,
        "Acquisition Date": acq_date.strftime("%Y-%m-%d"),
        "Depreciation Method": random.choice(DEPRECIATION_METHODS),
        "Useful Life (Years)": useful_life,
        "Salvage Value": round(cost_basis * salvage_pct, 2),
    }


def main() -> None:
    random.seed(42)
    output = Path(__file__).parent / "accounting_data.csv"
    rows = [generate_row(i + 1) for i in range(1000)]

    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    print(f"Written {len(rows)} rows to {output}")


if __name__ == "__main__":
    main()
