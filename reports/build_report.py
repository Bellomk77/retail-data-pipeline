"""Build the pipeline report: a data-quality scorecard, KPIs and charts.

The scorecard compares the issues *injected* into the raw data (raw/_manifest.json)
with the issues the pipeline *detected and handled*, so data quality is measured,
not assumed.
"""
from __future__ import annotations

import json
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WAREHOUSE = ROOT / "data" / "warehouse.duckdb"
MANIFEST = ROOT / "data" / "raw" / "_manifest.json"
DOCS = ROOT / "docs"
NAVY, TEAL, GOLD, GREY = "#1f3b73", "#2a9d8f", "#e9c46a", "#8d99ae"

SCORECARD_SQL = {
    "duplicate_order_rows": ("Duplicate order rows", "Removed (dedup on order_id)",
        "select (select count(*) from raw.orders) - (select count(*) from staging.stg_orders)"),
    "messy_emails": ("Emails with bad casing/whitespace", "Normalized (lower + trim)",
        "select count(*) from raw.customers where email != lower(trim(email))"),
    "messy_provinces": ("Province codes with bad casing/whitespace", "Normalized (upper + trim)",
        "select count(*) from raw.customers where province != upper(trim(province))"),
    "guest_orders": ("Orders with no customer id", "Kept, flagged as guest checkout",
        "select count(*) from staging.stg_orders where is_guest_checkout"),
    "return_lines": ("Returns as negative quantities", "Moved to return_amount",
        "select count(*) from staging.stg_order_items where is_return"),
    "orphan_lines": ("Lines for products missing from catalogue", "Kept, flagged + dbt warning",
        "select count(*) from intermediate.int_order_lines where is_orphan_product"),
}


def scorecard(con) -> list[dict]:
    injected = json.loads(MANIFEST.read_text())["injected"]
    rows = []
    for key, (issue, handling, sql) in SCORECARD_SQL.items():
        detected = con.execute(sql).fetchone()[0]
        rows.append({"issue": issue, "injected": injected[key], "detected": detected,
                     "handled": handling, "match": injected[key] == detected})
    return rows


def kpis(con) -> dict:
    q = lambda s: con.execute(s).fetchone()  # noqa: E731
    gross, returns, net, orders = q("select sum(gross_sales), sum(return_amount), sum(net_revenue), "
                                    "count(*) filter (where status != 'cancelled') from marts.fct_orders")
    repeat = q("select avg((lifetime_orders >= 2)::int) from marts.dim_customers where customer_segment != 'Prospect'")[0]
    m1 = q("select avg(retention_rate) from marts.mart_cohort_retention where months_since_first = 1")[0]
    return {"gross_sales": float(gross), "returns": float(returns), "net_revenue": float(net), "orders": orders,
            "aov": float(net) / orders, "repeat_rate": float(repeat), "month1_retention": float(m1 or 0)}


def chart_monthly(con) -> Path:
    df = con.execute("""
        select date_trunc('month', order_date) as m, channel, sum(net_revenue) as rev
        from marts.fct_orders where order_date >= '2024-01-01' group by 1, 2 order by 1
    """).df()
    piv = df.pivot(index="m", columns="channel", values="rev").fillna(0)
    fig, ax = plt.subplots(figsize=(11, 4.6), dpi=150)
    bottom = np.zeros(len(piv))
    for ch, color in zip(["web", "mobile_app", "marketplace"], [NAVY, TEAL, GOLD]):
        if ch in piv:
            ax.bar(piv.index, piv[ch] / 1000, width=20, bottom=bottom, color=color, label=ch.replace("_", " "))
            bottom += piv[ch].values / 1000
    ax.set_title("Monthly net revenue by channel (CAD thousands)", loc="left", fontsize=13, fontweight="bold", color="#222")
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.25)
    ax.legend(frameon=False, ncol=3, loc="upper left")
    peak = piv.sum(axis=1).idxmax()
    ax.annotate("Holiday peak", xy=(peak, piv.sum(axis=1).max() / 1000), xytext=(0, 12),
                textcoords="offset points", ha="center", fontsize=9, color="#444")
    fig.tight_layout()
    path = DOCS / "monthly_revenue.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def chart_cohorts(con) -> Path:
    df = con.execute("""
        select strftime(cohort_month, '%Y-%m') as cohort, months_since_first, retention_rate
        from marts.mart_cohort_retention
        where cohort_month >= '2024-01-01' and cohort_month < '2025-07-01' and months_since_first <= 6
    """).df()
    piv = df.pivot(index="cohort", columns="months_since_first", values="retention_rate")
    fig, ax = plt.subplots(figsize=(8, 6.4), dpi=150)
    im = ax.imshow(piv.values, cmap="Blues", vmin=0, vmax=0.35, aspect="auto")
    for (i, j), v in np.ndenumerate(piv.values):
        if not np.isnan(v):
            ax.text(j, i, f"{v:.0%}", ha="center", va="center", fontsize=7.5,
                    color="white" if v > 0.22 else "#1d3557", fontweight="bold" if j == 0 else "normal")
    ax.set_xticks(range(len(piv.columns)), [f"M{c}" for c in piv.columns])
    ax.set_yticks(range(len(piv.index)), piv.index, fontsize=8)
    ax.set_title("Customer retention by first-order cohort", loc="left", fontsize=13, fontweight="bold")
    ax.set_xlabel("Months since first order")
    fig.colorbar(im, ax=ax, fraction=0.03, format=matplotlib.ticker.PercentFormatter(1.0))
    fig.tight_layout()
    path = DOCS / "cohort_retention.png"
    fig.savefig(path)
    plt.close(fig)
    return path


def build() -> dict:
    DOCS.mkdir(exist_ok=True)
    con = duckdb.connect(str(WAREHOUSE), read_only=True)
    card, k = scorecard(con), kpis(con)
    chart_monthly(con)
    chart_cohorts(con)
    segs = con.execute("select customer_segment, count(*), round(sum(lifetime_net_revenue)) from marts.dim_customers group by 1 order by 3 desc").fetchall()
    con.close()

    lines = ["# Pipeline report", "", "## Data quality scorecard", "",
             "| Issue in raw data | Injected | Detected | How the pipeline handles it | |", "|---|---|---|---|---|"]
    lines += [f"| {r['issue']} | {r['injected']:,} | {r['detected']:,} | {r['handled']} | {'✅' if r['match'] else '❌'} |" for r in card]
    lines += ["", "## KPIs", "",
              f"- Net revenue: **${k['net_revenue']:,.0f}** (gross ${k['gross_sales']:,.0f}, returns ${k['returns']:,.0f})",
              f"- Orders (excl. cancelled): **{k['orders']:,}** · Average order value: **${k['aov']:,.2f}**",
              f"- Repeat-customer rate: **{k['repeat_rate']:.1%}** · Average month-1 retention: **{k['month1_retention']:.1%}**",
              "", "## Customer segments", "", "| Segment | Customers | Lifetime net revenue |", "|---|---|---|"]
    lines += [f"| {s} | {n:,} | ${rev:,.0f} |" for s, n, rev in segs]
    (ROOT / "reports" / "pipeline_report.md").write_text("\n".join(lines) + "\n")
    return {"scorecard": card, "kpis": k}


if __name__ == "__main__":
    out = build()
    print(json.dumps(out, indent=2, default=str))
