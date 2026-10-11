"""
Part (a) – Canada's export exposure to U.S. Section 338 tariffs, 2025.

Research question
-----------------
Using the latest applicable U.S. Section 338 product lists and appropriate
Canadian trade data, estimate Canada's total export exposure to the United
States' Section 338 tariffs and show how that exposure is distributed across
provinces and territories.

I map Yale Budget Lab HTS8 codes to HS6 for an upper-bound screen, and I match
Canadian HS8 codes exactly to listed U.S. HTS8 codes for a lower-bound screen.
True exposure sits between those bounds because U.S. and Canadian HS8 lines do
not concord one-to-one.

Large CIMT CSVs are not committed. You can run this script to reuse a local
CIMT extract if present, or download the official zip when they are missing.

Run from this package root:
    python3 Q2a.py
"""
from __future__ import annotations

import re
import shutil
import ssl
import urllib.request
import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data" / "q2a"
OUTPUT_DIR = ROOT / "outputs" / "q2a"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

S338_URL = (
    "https://raw.githubusercontent.com/Budget-Lab-Yale/tariff-rate-tracker/"
    "master/resources/s338_products.csv"
)
DOMESTIC_EXPORTS_URL = (
    "https://www150.statcan.gc.ca/n1/pub/71-607-x/2021004/zip/CIMT-CICM_Dom_Exp_2025.zip"
)

S338_PATH = DATA_DIR / "s338_products.csv"
ZIP_PATH = DATA_DIR / "CIMT-CICM_Dom_Exp_2025.zip"
EXTRACT_DIR = DATA_DIR / "CIMT-CICM_Dom_Exp_2025"
HS6_FILE = "ODPFN018_202512N.csv"
HS8_FILE = "ODPFN016_202512N.csv"

LOCAL_CIMT_CANDIDATES = [
    ROOT.parent / "Alberta_Assignment" / "data" / "CIMT-CICM_Dom_Exp_2025",
    ROOT.parent / "Final_assignment" / "data" / "q1a" / "CIMT-CICM_Dom_Exp_2025",
]

COLUMN_NAMES_HS6 = {
    "YearMonth/AnnéeMois": "year_month",
    "HS6": "hs6",
    "Country/Pays": "country_code",
    "Province": "province_code",
    "Value/Valeur": "value_cad",
}

COLUMN_NAMES_HS8 = {
    "YearMonth/AnnéeMois": "year_month",
    "HS8": "hs8",
    "Country/Pays": "country_code",
    "Province": "province_code",
    "Value/Valeur": "value_cad",
}

PROVINCE_ORDER = [
    "NL",
    "PE",
    "NS",
    "NB",
    "QC",
    "ON",
    "MB",
    "SK",
    "AB",
    "BC",
    "YT",
    "NT",
    "NU",
]


def download(url: str, destination: Path) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=180, context=context) as response:
            destination.write_bytes(response.read())
            return
    except (ssl.SSLError, urllib.error.URLError):
        insecure = ssl._create_unverified_context()
        with urllib.request.urlopen(request, timeout=180, context=insecure) as response:
            destination.write_bytes(response.read())


def english_name(text: str) -> str:
    trailer = text.find("ODPF")
    if trailer != -1:
        text = text[:trailer]
    return re.split(r"\s{2,}", text.strip())[0]


def names_in_force(path: Path, code_pattern: str, code_column: str) -> pd.DataFrame:
    rows = []
    unread = []
    for line_number, line in enumerate(path.read_text(encoding="latin-1").splitlines(), start=1):
        match = re.match(code_pattern, line)
        if not match:
            unread.append(line_number)
            continue
        rows.append(
            {
                code_column: match.group("code"),
                "name_start": int(match.group("start")),
                "name_end": int(match.group("end")),
                "name": english_name(match.group("text")),
            }
        )
    if unread:
        raise ValueError(f"{path.name}: could not read lines {unread[:5]}")
    names = pd.DataFrame(rows)
    in_2025 = names[(names["name_start"] <= 202512) & (names["name_end"] >= 202501)]
    in_2025 = in_2025.sort_values("name_start").drop_duplicates(code_column, keep="last")
    return in_2025[[code_column, "name"]]


def ensure_cimt() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    local_hs6 = EXTRACT_DIR / HS6_FILE
    local_hs8 = EXTRACT_DIR / HS8_FILE
    if local_hs6.exists() and local_hs8.exists():
        return EXTRACT_DIR

    for candidate in LOCAL_CIMT_CANDIDATES:
        if (candidate / HS6_FILE).exists() and (candidate / HS8_FILE).exists():
            print(f"Reusing CIMT extract from {candidate}")
            if EXTRACT_DIR.exists():
                shutil.rmtree(EXTRACT_DIR)
            shutil.copytree(candidate, EXTRACT_DIR)
            return EXTRACT_DIR

    print("Downloading domestic exports for 2025...")
    download(DOMESTIC_EXPORTS_URL, ZIP_PATH)
    with zipfile.ZipFile(ZIP_PATH) as archive:
        archive.extractall(DATA_DIR)
    if not (EXTRACT_DIR / HS6_FILE).exists() or not (EXTRACT_DIR / HS8_FILE).exists():
        raise FileNotFoundError(f"Expected {HS6_FILE} and {HS8_FILE} after extracting CIMT zip")
    return EXTRACT_DIR


def ensure_s338() -> pd.DataFrame:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not S338_PATH.exists():
        print("Downloading Section 338 product list...")
        download(S338_URL, S338_PATH)
    s338 = pd.read_csv(S338_PATH, dtype=str)
    required = {"hts8", "program", "ch99_heading"}
    missing = required - set(s338.columns)
    if missing:
        raise ValueError(f"s338_products.csv missing columns: {sorted(missing)}")
    s338["hts8"] = s338["hts8"].str.zfill(8)
    s338["hs6"] = s338["hts8"].str[:6]
    return s338


def load_us_exports_hs6(extract_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        extract_dir / HS6_FILE,
        usecols=list(COLUMN_NAMES_HS6),
        dtype={
            "YearMonth/AnnéeMois": str,
            "HS6": str,
            "Country/Pays": str,
            "Province": str,
        },
    )
    frame = frame.rename(columns=COLUMN_NAMES_HS6)
    frame["value_cad"] = pd.to_numeric(frame["value_cad"], errors="coerce").fillna(0.0)
    frame["hs6"] = frame["hs6"].str.zfill(6)
    frame["province_code"] = frame["province_code"].str.strip()
    frame["country_code"] = frame["country_code"].str.strip()

    months = sorted(frame["year_month"].dropna().unique())
    expected = [f"2025{month:02d}" for month in range(1, 13)]
    if months != expected:
        raise AssertionError("The CIMT HS6 file does not contain all 12 months of 2025.")

    us = frame.loc[frame["country_code"].eq("US")].copy()
    if us.empty:
        raise AssertionError("No United States rows found in CIMT HS6 domestic exports.")
    return us


# Back-compat alias used by Q2b.py
def load_us_exports(extract_dir: Path) -> pd.DataFrame:
    return load_us_exports_hs6(extract_dir)


def load_us_exports_hs8(extract_dir: Path) -> pd.DataFrame:
    frame = pd.read_csv(
        extract_dir / HS8_FILE,
        usecols=list(COLUMN_NAMES_HS8),
        dtype={
            "YearMonth/AnnéeMois": str,
            "HS8": str,
            "Country/Pays": str,
            "Province": str,
        },
    )
    frame = frame.rename(columns=COLUMN_NAMES_HS8)
    frame["value_cad"] = pd.to_numeric(frame["value_cad"], errors="coerce").fillna(0.0)
    frame["hs8"] = frame["hs8"].str.zfill(8)
    frame["hs6"] = frame["hs8"].str[:6]
    frame["hs4"] = frame["hs8"].str[:4]
    frame["province_code"] = frame["province_code"].str.strip()
    frame["country_code"] = frame["country_code"].str.strip()

    months = sorted(frame["year_month"].dropna().unique())
    expected = [f"2025{month:02d}" for month in range(1, 13)]
    if months != expected:
        raise AssertionError("The CIMT HS8 file does not contain all 12 months of 2025.")

    us = frame.loc[frame["country_code"].eq("US")].copy()
    if us.empty:
        raise AssertionError("No United States rows found in CIMT HS8 domestic exports.")
    return us


def main() -> None:
    s338 = ensure_s338()
    extract_dir = ensure_cimt()

    province_pattern = (
        r"^\d+\s+(?P<code>\S{2})\s+(?P<start>\d{6})\s+(?P<end>\d{6})\s(?P<text>.*)$"
    )
    provinces = names_in_force(
        extract_dir / "ODPF_8_ProvDesc.TXT", province_pattern, "province_code"
    )
    provinces = provinces.rename(columns={"name": "province"})

    us6 = load_us_exports_hs6(extract_dir)
    us8 = load_us_exports_hs8(extract_dir)
    canada_us_total = float(us6["value_cad"].sum())

    hs6_program = (
        s338.sort_values(["hs6", "hts8"])
        .drop_duplicates("hs6", keep="first")[["hs6", "program", "ch99_heading"]]
        .copy()
    )
    s338_hs6 = set(hs6_program["hs6"])
    s338_hts8 = set(s338["hts8"])

    # Upper bound: any listed US HTS8 truncates to this HS6 → full Canadian HS6→US value
    us_hs6 = us6.groupby(["province_code", "hs6"], as_index=False)["value_cad"].sum()
    exposed_ub = us_hs6.loc[us_hs6["hs6"].isin(s338_hs6)].copy()
    exposed_ub = exposed_ub.merge(hs6_program, on="hs6", how="left")
    exposed_ub = exposed_ub.merge(provinces, on="province_code", how="left")
    national_ub = float(exposed_ub["value_cad"].sum())

    # Lower bound: Canadian HS8 code equals a listed US HTS8 code
    exposed_lb = us8.loc[us8["hs8"].isin(s338_hts8)].copy()
    national_lb = float(exposed_lb["value_cad"].sum())

    national = pd.DataFrame(
        [
            {
                "year": 2025,
                "destination": "United States",
                "s338_hts8_codes": int(s338["hts8"].nunique()),
                "s338_hs6_codes": int(len(s338_hs6)),
                "canada_us_exports_cad": canada_us_total,
                "s338_exposed_lower_cad": national_lb,
                "s338_exposed_upper_cad": national_ub,
                "lb_to_ub_ratio": national_lb / national_ub if national_ub else np.nan,
                "share_of_canada_us_exports_lower": national_lb / canada_us_total,
                "share_of_canada_us_exports_upper": national_ub / canada_us_total,
            }
        ]
    )

    province_us = (
        us6.groupby("province_code", as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "province_us_exports_cad"})
    )
    ub_by_province = (
        exposed_ub.groupby("province_code", as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "s338_exposed_upper_cad"})
    )
    lb_by_province = (
        exposed_lb.groupby("province_code", as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "s338_exposed_lower_cad"})
    )
    by_province = (
        province_us.merge(ub_by_province, on="province_code", how="left")
        .merge(lb_by_province, on="province_code", how="left")
        .merge(provinces, on="province_code", how="left")
    )
    by_province["s338_exposed_upper_cad"] = by_province["s338_exposed_upper_cad"].fillna(0.0)
    by_province["s338_exposed_lower_cad"] = by_province["s338_exposed_lower_cad"].fillna(0.0)
    by_province["lb_to_ub_ratio"] = np.where(
        by_province["s338_exposed_upper_cad"] > 0,
        by_province["s338_exposed_lower_cad"] / by_province["s338_exposed_upper_cad"],
        np.nan,
    )
    by_province["share_of_national_s338_exposure_upper"] = (
        by_province["s338_exposed_upper_cad"] / national_ub if national_ub else 0.0
    )
    by_province["provincial_exposure_intensity_upper"] = (
        by_province["s338_exposed_upper_cad"] / by_province["province_us_exports_cad"]
    )
    by_province["provincial_exposure_intensity_lower"] = (
        by_province["s338_exposed_lower_cad"] / by_province["province_us_exports_cad"]
    )
    # Back-compat aliases used by older notebook cells / readers
    by_province["s338_exposed_exports_cad"] = by_province["s338_exposed_upper_cad"]
    by_province["share_of_national_s338_exposure"] = by_province[
        "share_of_national_s338_exposure_upper"
    ]
    by_province["share_of_province_us_exports"] = by_province[
        "provincial_exposure_intensity_upper"
    ]

    order = {code: index for index, code in enumerate(PROVINCE_ORDER)}
    by_province["sort_key"] = by_province["province_code"].map(order).fillna(99)
    by_province = by_province.sort_values(
        ["s338_exposed_upper_cad", "sort_key"], ascending=[False, True]
    ).drop(columns=["sort_key"])
    by_province.insert(0, "rank", range(1, len(by_province) + 1))

    by_program = (
        exposed_ub.groupby(["program", "ch99_heading"], as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "s338_exposed_upper_cad"})
        .sort_values("s338_exposed_upper_cad", ascending=False)
    )
    by_program["share_of_national_s338_exposure_upper"] = (
        by_program["s338_exposed_upper_cad"] / national_ub if national_ub else 0.0
    )

    by_province_program = (
        exposed_ub.groupby(["province_code", "province", "program"], as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "s338_exposed_upper_cad"})
        .sort_values(
            ["province_code", "s338_exposed_upper_cad", "program"],
            ascending=[True, False, True],
        )
    )

    # Grouped LB/UB bars for the largest absolute exposures
    chart = by_province.sort_values("s338_exposed_upper_cad", ascending=True)
    fig, axis = plt.subplots(figsize=(9.5, 6.5))
    y = np.arange(len(chart))
    height = 0.38
    axis.barh(
        y - height / 2,
        chart["s338_exposed_lower_cad"] / 1e9,
        height=height,
        color="#7a9bb8",
        label="Lower bound (exact HS8 match)",
    )
    axis.barh(
        y + height / 2,
        chart["s338_exposed_upper_cad"] / 1e9,
        height=height,
        color="#1f4e79",
        label="Upper bound (HS6 any-match)",
    )
    axis.set_yticks(y)
    axis.set_yticklabels(chart["province"])
    axis.set_xlabel("Section 338–exposed domestic exports to the U.S., 2025 (billion CAD)")
    axis.set_title("Canada's Section 338 export exposure range by province and territory, 2025")
    axis.legend(loc="lower right", frameon=False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2a_exposure_by_province.png", dpi=150)
    plt.close(fig)

    national.to_csv(OUTPUT_DIR / "q2a_national_exposure.csv", index=False)
    by_province[
        [
            "rank",
            "province_code",
            "province",
            "s338_exposed_lower_cad",
            "s338_exposed_upper_cad",
            "lb_to_ub_ratio",
            "share_of_national_s338_exposure_upper",
            "province_us_exports_cad",
            "provincial_exposure_intensity_lower",
            "provincial_exposure_intensity_upper",
            "s338_exposed_exports_cad",
            "share_of_national_s338_exposure",
            "share_of_province_us_exports",
        ]
    ].to_csv(OUTPUT_DIR / "q2a_exposure_by_province.csv", index=False)
    by_program.to_csv(OUTPUT_DIR / "q2a_exposure_by_program.csv", index=False)
    by_province_program.to_csv(OUTPUT_DIR / "q2a_exposure_by_province_program.csv", index=False)

    hs6_program.to_csv(DATA_DIR / "s338_hs6_unique.csv", index=False)

    print(f"Section 338 list: {s338['hts8'].nunique()} HTS8 codes → {len(s338_hs6)} HS6 codes")
    print(f"Canada → U.S. domestic exports, 2025: ${canada_us_total:,.0f}")
    print(f"Section 338 exposure lower bound: ${national_lb:,.0f}")
    print(f"Section 338 exposure upper bound: ${national_ub:,.0f}")
    print(f"LB / UB ratio: {national_lb / national_ub:.1%}")
    print(
        f"Share of Canada → U.S. exports: "
        f"{national_lb / canada_us_total:.1%} – {national_ub / canada_us_total:.1%}"
    )
    print("Top provinces by upper-bound exposure:")
    for _, row in by_province.head(5).iterrows():
        print(
            f"  {row['province']}: "
            f"${row['s338_exposed_lower_cad']:,.0f} – ${row['s338_exposed_upper_cad']:,.0f} "
            f"(UB share of national {row['share_of_national_s338_exposure_upper']:.1%})"
        )
    print("Wrote", OUTPUT_DIR)


if __name__ == "__main__":
    main()
