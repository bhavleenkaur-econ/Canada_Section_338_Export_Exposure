# Data for parts (a) and (b)

I keep the Yale Section 338 product list (`s338_products.csv`), the derived unique HS6 crosswalk (`s338_hs6_unique.csv`), and the public HS4 name file here after the first run. I do **not** commit the large monthly CIMT CSVs.

You can restore the trade extract by running from the package root:

```bash
python3 Q2a.py
```

That reuses a local CIMT extract when present on this machine, or downloads the official 2025 domestic-exports zip when the HS6/HS8 files are missing. Then run `python3 Q2b.py` for the HS4 Alberta and comparator tables. The committed output CSVs and charts are enough if you only want to read results.
