# Canada's Section 338 export exposure

How U.S. Section 338 tariff product lists map onto Canadian provincial merchandise exports. I estimate a national exposure **range**, distribute it across provinces and territories, then compare Alberta with Saskatchewan, Ontario, Quebec, and British Columbia on products, intensity, composition, concentration, and an employment-linked proxy.

**Skills demonstrated.** HTS8→HS6 crosswalk with lower/upper bounds, Statistics Canada CIMT provincial trade, exposure intensity and contribution, cosine composition similarity, HHI concentration, LFS employment proxy.

## Key results (from my last run)

### National exposure range (Q2a)

| Metric | Value |
| --- | ---: |
| Canada → U.S. domestic exports, 2025 | $517.3B CAD |
| Section 338 exposure, lower bound (exact HS8 match) | $10.0B CAD (1.9%) |
| Section 338 exposure, upper bound (HS6 any-match) | $33.2B CAD (6.4%) |
| LB / UB ratio | 30.2% |
| Yale list coverage | 554 HTS8 → 373 HS6 |

Largest upper-bound exposure: Ontario ($17.2B), Quebec ($9.1B), British Columbia ($3.8B), Alberta ($1.6B), Manitoba ($0.7B).

### Alberta products (Q2b, upper bound)

| HS4 | Product (short) | Exposure | Intensity | Contribution |
| --- | --- | ---: | ---: | ---: |
| 8414 | Air/vacuum pumps, compressors, fans | $214M | 90.1% | 13.6% |
| 8537 | Electricity control/distribution boards | $176M | 95.3% | 11.1% |
| 3824 | Chemical preparations n.e.s. | $160M | 92.7% | 10.1% |
| 9403 | Furniture and parts n.e.c. | $104M | 59.0% | 6.6% |
| 8526 | Radar / radio navigational aid apparatus | $95M | 100% | 6.0% |

**Intensity** \(I\) = exposed HS6 dollars in an HS4 ÷ all U.S. exports in that HS4.  
**Contribution** \(C\) = that product's exposed dollars ÷ the province's total S338 exposure.

### Peer comparison

Provincial exposure intensity (LB – UB): Alberta **0.3% – 1.0%**, Saskatchewan **0.6% – 1.2%**, Ontario **3.0% – 9.0%**, Quebec **2.7% – 10.8%**, British Columbia **4.1% – 13.6%**. Alberta and Saskatchewan look alike on intensity (low share of a large energy-heavy U.S. basket); ON/QC/BC have much higher intensity and larger absolute dollars.

Composition vs Alberta: cosine similarity is highest with B.C. (~0.52) and Ontario (~0.51); Jaccard on top-10 sets is modest (~0.18–0.25). Saskatchewan shares more top-10 membership with Alberta (Jaccard 0.25) but a lower cosine (0.25), so the overlapping products are not the dollar-dominant ones.

HS4 HHI of S338 exposure shares: Saskatchewan 0.163 (most concentrated among peers), Alberta 0.064, B.C. 0.082, Ontario 0.032, Quebec 0.028.

Employment proxy (exposed exports per goods-sector employee, LFS 2025): Alberta ~$2.6k, Saskatchewan ~$2.1k, B.C. ~$7.3k, Quebec ~$9.5k, Ontario ~$10.9k. This is illustrative context only, not a job-loss estimate.

## Quick start

```bash
cd <this-repo>
python3 -m pip install -r requirements.txt
python3 Q2a.py
python3 Q2b.py
```

Or open [`Q2_Section_338_Exposure.ipynb`](Q2_Section_338_Exposure.ipynb) with `REFIT = False` to read saved tables. You can set `REFIT = True` to call both scripts from the notebook.

Large CIMT and LFS zip files are not committed. The scripts download them into `data/` when missing.

## Research questions

**Part (a).** Using the latest applicable U.S. Section 338 product lists and Canadian trade data, estimate Canada's total export exposure to U.S. Section 338 tariffs and show how that exposure is distributed across provinces and territories. Aggregate at HS6 for international consistency, and report a lower/upper range because HS8 codes do not match one-to-one.

**Part (b).** For Alberta, identify major exposed products at HS4 (code, name, exposure value, intensity, contribution). Compare Alberta with other major exporting provinces on value, intensity, product composition, concentration, and an employment-linked proxy.

Product list: [Yale Budget Lab `s338_products.csv`](https://github.com/Budget-Lab-Yale/tariff-rate-tracker/blob/master/resources/s338_products.csv).

## Method in brief

- **Upper bound:** any Yale HTS8 → HS6 match counts full Canadian HS6→U.S. value.  
- **Lower bound:** Canadian HS8 code equals a listed U.S. HTS8.  
- **Peers:** AB, SK, ON, QC, BC (territories stay in the Canada-wide table only).  
- **Similarity:** Jaccard on top-10 HS4 sets; cosine on full HS4 exposure-share vectors.  
- **HHI:** concentration of S338 exposure shares at HS4 and HS2.  
- **Employment proxy:** LFS table 14-10-0023 with a coarse HS2→NAICS bridge.

Details: [`methodology/Q2a_methodology.md`](methodology/Q2a_methodology.md), [`methodology/Q2b_methodology.md`](methodology/Q2b_methodology.md).

## Folder map

```
.
  Q2a.py / Q2b.py
  Q2_Section_338_Exposure.ipynb
  README.md / DATA_TERMS.md / requirements.txt
  methodology/
  data/q2a/          # s338 list, HS6 crosswalk, HS names; CIMT on demand
  data/q2b/          # HS2–NAICS bridge; LFS extract on demand
  outputs/q2a/       # national + provincial exposure range
  outputs/q2b/       # Alberta HS4, peers, HHI, employment proxy
```

## Extending the work

You can replace `data/q2a/s338_products.csv` with a newer Yale release and re-run both scripts. You can tighten the LB/UB range with a Canada–U.S. HS8 concordance. You can refine `data/q2b/hs2_naics_bridge.csv` if you want a finer employment mapping.
