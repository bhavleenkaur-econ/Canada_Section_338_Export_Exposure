# Q2a methodology – Section 338 export exposure

## Research question

Using the latest applicable U.S. Section 338 product lists and appropriate Canadian trade data, I estimate Canada's total export exposure to U.S. Section 338 tariffs and show how that exposure is distributed across provinces and territories.

## Exposure range (lower and upper bound)

U.S. lists are published at HTS8. Canadian trade is easiest to align at HS6, but that conversion is imperfect. I therefore report a range.

**Upper bound (UB).** Truncate each Yale HTS8 code to HS6. If a Canadian HS6 appears in that set, I count **all** Canada → U.S. domestic export value in that HS6 (CIMT HS6 file). This overstates exposure when only some eight-digit lines under the HS6 are listed.

**Lower bound (LB).** Count Canada → U.S. domestic export value only where the Canadian HS8 code **exactly equals** a listed U.S. HTS8 code (CIMT HS8 file). This understates exposure because U.S. and Canadian eight-digit codes do not concord one-to-one even for the same goods.

I treat the economically relevant exposure as lying between LB and UB. National and provincial tables report both, plus the LB/UB ratio and intensity under each bound.

## What I did

1. I downloaded the Yale Budget Lab Section 338 product list (`s338_products.csv`).
2. I loaded Statistics Canada CIMT domestic merchandise exports for 2025 at HS6 and HS8, kept rows destined for the United States, and summed all twelve months.
3. I computed UB and LB as above, distributed values across provinces and territories, and broke UB exposure out by Yale program for context.

## Data vintage

| Source | Vintage / role |
| --- | --- |
| Yale Budget Lab tariff-rate-tracker `s338_products.csv` | Latest file from the repo at run time |
| Statistics Canada CIMT domestic exports | Calendar year 2025, HS6 (`ODPFN018`) and HS8 (`ODPFN016`) |

Values stay in Canadian dollars to match CIMT.

## How to replicate

```bash
python3 Q2a.py
```

You can swap in a newer `s338_products.csv` and re-run. You can also tighten the range later with a formal Canada–U.S. HS8 concordance.
