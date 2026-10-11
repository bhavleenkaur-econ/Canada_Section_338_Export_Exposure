# Q2b methodology – products, peers, concentration, employment proxy

## Research questions

1. For Alberta, which HS4 products carry the most Section 338 export exposure, how intense is that exposure within each product, and how much of Alberta's total exposure does each product contribute?
2. How does Alberta compare with Saskatchewan, Ontario, Quebec, and British Columbia on value, intensity, product mix, concentration, and an employment-linked risk proxy?

## Product metrics

I start from the Part (a) screens. Product tables use the **upper-bound** HS6 screen rolled to HS4, and also report lower-bound HS8-matched dollars rolled to HS4 where available.

For province \(p\) and HS4 product \(k\):

\[
E^{UB}_{p,k} = \sum_{\text{HS6 } \in k,\ \text{HS6 on S338 list}} \text{CAD domestic exports}_{p,\text{US},\text{HS6}}
\]

\[
T_{p,k} = \sum_{\text{all HS6 } \in k} \text{CAD domestic exports}_{p,\text{US},\text{HS6}}
\]

**Exposure intensity**

\[
I_{p,k} = \frac{E^{UB}_{p,k}}{T_{p,k}}
\]

Share of that province's U.S. shipments in HS4 \(k\) that sit in Section 338–listed HS6 lines.

**Contribution to provincial exposure**

\[
C_{p,k} = \frac{E^{UB}_{p,k}}{\sum_j E^{UB}_{p,j}}
\]

Share of the province's total upper-bound S338 exposure that comes from HS4 \(k\).

Alberta's major products are the **top 10 HS4 by \(E^{UB}_{AB,k}\)**.

## Peer comparison

I compare Alberta with **Saskatchewan, Ontario, Quebec, and British Columbia**.

- Territories remain in the Part (a) Canada-wide table only. Their U.S. trade bases are tiny, so intensity ratios are volatile and not useful as peers.
- Saskatchewan is included as a prairie peer with a more similar energy and agriculture trade structure to Alberta than the large manufacturing or coastal exporters.

## Composition similarity

- **Jaccard** on each province's top-10 exposed HS4 set versus Alberta (set overlap).
- **Cosine similarity** on the full vector of HS4 exposure shares \(C_{p,\cdot}\) versus Alberta (composition similarity that respects dollar weights across all exposed products).

I prefer cosine for overall mix comparison; Jaccard answers whether the same headline products appear in both top-10 lists.

## Concentration (HHI)

\[
HHI^{HS4}_p = \sum_k C_{p,k}^2, \qquad HHI^{HS2}_p = \sum_h \left(\sum_{k \in h} C_{p,k}\right)^2
\]

Higher HHI means S338 exposure is concentrated in fewer products or chapters. I also report the top-10 HS4 share of provincial S338 exposure.

## Employment-risk proxy

This is an **illustrative proxy**, not a forecast of job losses.

1. I use Statistics Canada Labour Force Survey employment by industry and province (table 14-10-0023), Employment, Total gender, age 15+, latest annual year in the extract.
2. I map exposed HS2 chapters to broad LFS goods industries with `data/q2b/hs2_naics_bridge.csv`.
3. I report:
   - upper-bound exposed exports per goods-producing-sector employee
   - share of goods-sector employment in LFS industries touched by any exposed HS2
   - intensity-weighted employment \(\sum_s \text{emp}_s \times (E_s / T_s)\) for mapped goods industries

HS product codes and NAICS employment do not match one-to-one. You should read these figures as relative labour-market context across provinces, not as workers “at risk” of layoff.

## How to replicate

```bash
python3 Q2a.py
python3 Q2b.py
```

Or open `Q2_Section_338_Exposure.ipynb` with `REFIT = False` to read saved tables, or `REFIT = True` to re-run both scripts.
