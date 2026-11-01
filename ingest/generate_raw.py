"""Generate messy raw exports for a fictional Canadian online retailer ("Maple & Co.").

The data is synthetic, but the mess is realistic and *deliberate*, so the
pipeline has real problems to solve and the tests can prove they were solved:

- exact duplicate order rows (a re-sent export)
- emails and provinces with inconsistent casing and stray whitespace
- prices exported as text like "$1,299.00"
- order items pointing to a product that does not exist (orphans)
- returns recorded as negative quantities
- orders with a missing customer id (guest checkout)

Every injected issue is counted in raw/_manifest.json, which the tests use
as ground truth.
"""
from __future__ import annotations

import csv
import json
import random
from datetime import date, datetime, timedelta
from pathlib import Path

RAW = Path(__file__).resolve().parent.parent / "data" / "raw"

PROVINCES = ["ON", "ON", "ON", "QC", "BC", "AB", "MB", "NS"]  # Ontario-heavy, like real Canadian e-commerce
CATEGORIES = {
    "Electronics": [("Wireless Earbuds", 129.99), ("Smart Speaker", 89.99), ("4K Monitor", 429.00), ("Laptop Stand", 49.99)],
    "Home": [("Cast Iron Pan", 59.95), ("Linen Duvet", 189.00), ("Coffee Grinder", 74.50), ("Desk Lamp", 39.99)],
    "Outdoors": [("Down Jacket", 249.00), ("Hiking Boots", 179.99), ("Insulated Bottle", 34.95), ("Trail Backpack", 119.00)],
    "Beauty": [("Face Serum", 42.00), ("Hair Dryer", 99.99), ("Sunscreen SPF 50", 18.99)],
}
FIRST = ["Amara", "Liam", "Chloe", "Noah", "Fatima", "Ethan", "Zara", "Lucas", "Mei", "Omar", "Sofia", "Kofi", "Ava", "Raj", "Emma", "Tunde"]
LAST = ["Smith", "Tremblay", "Nguyen", "Okafor", "Patel", "Martin", "Roy", "Chen", "Ibrahim", "Wilson", "Gagnon", "Singh"]


def _money_text(x: float) -> str:
    return f"${x:,.2f}"


def generate(n_customers: int = 8000, seed: int = 7, out: Path = RAW) -> dict:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)
    manifest = {"seed": seed, "injected": {}}

    # ---- products ---------------------------------------------------------
    products = []
    pid = 100
    for cat, items in CATEGORIES.items():
        for name, price in items:
            pid += 1
            products.append({"product_id": pid, "product_name": name, "category": cat, "list_price": _money_text(price)})
    price_of = {p["product_id"]: float(p["list_price"].strip("$").replace(",", "")) for p in products}

    # ---- customers --------------------------------------------------------
    customers, messy_emails, messy_prov = [], 0, 0
    for cid in range(1, n_customers + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        email = f"{first}.{last}{cid}@example.com".lower()
        prov = rng.choice(PROVINCES)
        if rng.random() < 0.08:
            email = f"  {email.upper()} "
            messy_emails += 1
        if rng.random() < 0.06:
            prov = f" {prov.lower()}"
            messy_prov += 1
        signup = date(2024, 1, 1) + timedelta(days=rng.randint(0, 600))
        customers.append({"customer_id": cid, "first_name": first, "last_name": last, "email": email,
                          "province": prov, "signup_date": signup.isoformat()})
    manifest["injected"]["messy_emails"] = messy_emails
    manifest["injected"]["messy_provinces"] = messy_prov

    # ---- orders + items -----------------------------------------------------
    orders, items = [], []
    oid, line_id = 500000, 0
    for c in customers:
        signup = date.fromisoformat(c["signup_date"])
        # Some customers buy often, most buy a few times: a long-tailed distribution like real retail.
        n_orders = min(int(rng.paretovariate(1.6)), 15)
        for _ in range(n_orders):
            od = signup + timedelta(days=rng.randint(0, 420))
            if od > date(2025, 12, 31):
                continue
            oid += 1
            cust_id = "" if rng.random() < 0.03 else c["customer_id"]
            ts = datetime.combine(od, datetime.min.time()) + timedelta(minutes=rng.randint(0, 1439))
            orders.append({"order_id": oid, "customer_id": cust_id, "ordered_at": ts.isoformat(sep=" "),
                           "channel": rng.choice(["web", "web", "mobile_app", "marketplace"]),
                           "status": rng.choices(["delivered", "shipped", "cancelled"], [0.88, 0.07, 0.05])[0]})
            for _ in range(rng.randint(1, 4)):
                line_id += 1
                prod = rng.choice(products)["product_id"]
                if rng.random() < 0.004:
                    prod = 999  # orphan: product missing from the catalogue export
                qty = rng.randint(1, 3)
                if rng.random() < 0.04:
                    qty = -qty  # return
                unit = price_of.get(prod, 25.00)
                if od.month in (11, 12) and rng.random() < 0.5:
                    unit = round(unit * 0.8, 2)  # holiday discount
                items.append({"order_line_id": line_id, "order_id": oid, "product_id": prod,
                              "quantity": qty, "unit_price": _money_text(unit)})
    # Seasonality / holiday spike (Black Friday, December): clone half of Nov-Dec orders with new ids. extra Nov/Dec orders by cloning a share of them with new ids.
    holiday = [o for o in orders if o["ordered_at"][5:7] in ("11", "12")]
    extra = rng.sample(holiday, k=len(holiday) // 2)
    for o in extra:
        oid += 1
        clone = {**o, "order_id": oid}
        orders.append(clone)
        for it in [i for i in items if i["order_id"] == o["order_id"]]:
            line_id += 1
            items.append({**it, "order_line_id": line_id, "order_id": oid})

    # Duplicate export rows: the same order sent twice.
    dupes = rng.sample(orders, k=int(len(orders) * 0.02))
    orders.extend(dict(d) for d in dupes)
    manifest["injected"].update({
        "guest_orders": sum(1 for o in {o["order_id"]: o for o in orders}.values() if o["customer_id"] == ""),
        "return_lines": sum(1 for i in items if i["quantity"] < 0),
        "orphan_lines": sum(1 for i in items if i["product_id"] == 999),
        "duplicate_order_rows": len(dupes),
    })
    rng.shuffle(orders)

    def write(name: str, rows: list[dict]) -> None:
        with open(out / name, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        manifest.setdefault("row_counts", {})[name] = len(rows)

    write("products.csv", products)
    write("customers.csv", customers)
    write("orders.csv", orders)
    write("order_items.csv", items)
    (out / "_manifest.json").write_text(json.dumps(manifest, indent=2))
    return manifest


if __name__ == "__main__":
    m = generate()
    print(json.dumps(m, indent=2))
