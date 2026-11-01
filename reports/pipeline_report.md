# Pipeline report

## Data quality scorecard

| Issue in raw data | Injected | Detected | How the pipeline handles it | |
|---|---|---|---|---|
| Duplicate order rows | 291 | 291 | Removed (dedup on order_id) | ✅ |
| Emails with bad casing/whitespace | 596 | 596 | Normalized (lower + trim) | ✅ |
| Province codes with bad casing/whitespace | 460 | 460 | Normalized (upper + trim) | ✅ |
| Orders with no customer id | 449 | 449 | Kept, flagged as guest checkout | ✅ |
| Returns as negative quantities | 1,459 | 1,459 | Moved to return_amount | ✅ |
| Lines for products missing from catalogue | 148 | 148 | Kept, flagged + dbt warning | ✅ |

## KPIs

- Net revenue: **$7,381,701** (gross $7,716,146, returns $334,444)
- Orders (excl. cancelled): **13,865** · Average order value: **$532.40**
- Repeat-customer rate: **36.5%** · Average month-1 retention: **10.2%**

## Customer segments

| Segment | Customers | Lifetime net revenue |
|---|---|---|
| Repeat | 2,159 | $2,914,519 |
| One-time | 4,355 | $2,254,016 |
| VIP | 343 | $1,971,786 |
| Prospect | 1,143 | $0 |
