# Data terms and how to cite sources

I used third-party open data for this research package. You should check each provider's current licence before redistributing raw files.

| Source | What I used it for | Starting point |
| --- | --- | --- |
| Yale Budget Lab tariff-rate-tracker | Section 338 HTS8 product list | [s338_products.csv](https://github.com/Budget-Lab-Yale/tariff-rate-tracker/blob/master/resources/s338_products.csv) |
| Statistics Canada CIMT domestic exports 2025 | Canada → U.S. export values by province, HS6 and HS8 | [Open Government record](https://open.canada.ca/data/en/dataset/2909a648-5753-4924-878a-b069392d9cde); [2025 zip](https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/CIMT-CICM_Dom_Exp_2025.zip) |
| Statistics Canada LFS table 14-10-0023 | Employment by industry and province (employment-risk proxy) | [Table 14-10-0023-01](https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410002301) |
| Harmonized System names | HS4 product labels | [datasets/harmonized-system](https://github.com/datasets/harmonized-system) (ODC-PDDL) |

I commit the Section 338 list, the derived HS6 crosswalk, the HS2–NAICS bridge, a slim LFS cache, HS names, and result tables so the repo stays small. You can re-download full StatCan CIMT and LFS zips by running `python3 Q2a.py` and `python3 Q2b.py` when those archives are missing.
