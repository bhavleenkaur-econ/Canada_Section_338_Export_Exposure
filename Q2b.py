"""
Part (b) – Provincial Section 338 product exposure at HS4.

Research questions
------------------
For Alberta, identify the major exposed products at the HS4 level (code, name,
export exposure value, exposure intensity, contribution to provincial exposure).
Compare Alberta's exposure profile with Saskatchewan, Ontario, Quebec, and
British Columbia on value, intensity, product composition, concentration, and
an illustrative employment-risk proxy.

I reuse the Part (a) upper-bound HS6 screen and lower-bound exact HS8 match,
roll trade to HS4, and define:
  intensity I = exposed / all U.S. exports in that HS4
  contribution C = exposed HS4 / province total S338 exposure (upper bound)

Run from this package root:
    python3 Q2b.py
"""
from __future__ import annotations

import zipfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import Q2a

ROOT = Path(__file__).resolve().parent
DATA_DIR_A = ROOT / "data" / "q2a"
DATA_DIR_B = ROOT / "data" / "q2b"
OUTPUT_DIR = ROOT / "outputs" / "q2b"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR_B.mkdir(parents=True, exist_ok=True)

HS4_NAMES_URL = (
    "https://raw.githubusercontent.com/datasets/harmonized-system/master/data/harmonized-system.csv"
)
HS4_NAMES_PATH = DATA_DIR_A / "harmonized-system.csv"
BRIDGE_PATH = DATA_DIR_B / "hs2_naics_bridge.csv"
LFS_ZIP_URL = "https://www150.statcan.gc.ca/n1/tbl/csv/14100023-eng.zip"
LFS_ZIP_PATH = DATA_DIR_B / "14100023-eng.zip"
LFS_CACHE_PATH = DATA_DIR_B / "lfs_employment_by_industry_province.csv"

COMPARATOR_CODES = ["AB", "SK", "ON", "QC", "BC"]
TOP_N = 10

PROVINCE_NAME_TO_CODE = {
    "Alberta": "AB",
    "Saskatchewan": "SK",
    "Ontario": "ON",
    "Quebec": "QC",
    "British Columbia": "BC",
}


def ensure_hs4_names() -> pd.DataFrame:
    DATA_DIR_A.mkdir(parents=True, exist_ok=True)
    if not HS4_NAMES_PATH.exists():
        print("Downloading HS4 product names...")
        Q2a.download(HS4_NAMES_URL, HS4_NAMES_PATH)
    hs_names = pd.read_csv(HS4_NAMES_PATH, dtype=str)
    return (
        hs_names.loc[hs_names["level"].eq("4"), ["hscode", "description"]]
        .drop_duplicates("hscode")
        .rename(columns={"hscode": "hs4", "description": "product_name"})
    )


def province_hs4_tables(
    us: pd.DataFrame, s338_hs6: set[str], provinces: pd.DataFrame
) -> pd.DataFrame:
    frame = us.copy()
    frame["hs4"] = frame["hs6"].str[:4]
    frame["is_s338"] = frame["hs6"].isin(s338_hs6)

    totals = (
        frame.groupby(["province_code", "hs4"], as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "us_exports_hs4_cad"})
    )
    exposed = (
        frame.loc[frame["is_s338"]]
        .groupby(["province_code", "hs4"], as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "export_exposure_upper_cad"})
    )
    out = totals.merge(exposed, on=["province_code", "hs4"], how="left")
    out["export_exposure_upper_cad"] = out["export_exposure_upper_cad"].fillna(0.0)
    out["exposure_intensity"] = out["export_exposure_upper_cad"] / out["us_exports_hs4_cad"]
    out = out.merge(provinces, on="province_code", how="left")
    return out


def lower_bound_hs4(us8: pd.DataFrame, s338_hts8: set[str]) -> pd.DataFrame:
    lb = us8.loc[us8["hs8"].isin(s338_hts8)].copy()
    lb["hs4"] = lb["hs8"].str[:4]
    return (
        lb.groupby(["province_code", "hs4"], as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "export_exposure_lower_cad"})
    )


def top_hs4_for_province(hs4_table: pd.DataFrame, province_code: str, top_n: int) -> pd.DataFrame:
    prov = hs4_table.loc[hs4_table["province_code"].eq(province_code)].copy()
    prov_exposed_total = float(prov["export_exposure_upper_cad"].sum())
    top = (
        prov.loc[prov["export_exposure_upper_cad"].gt(0)]
        .sort_values(["export_exposure_upper_cad", "hs4"], ascending=[False, True])
        .head(top_n)
        .copy()
    )
    top.insert(0, "product_rank", range(1, len(top) + 1))
    top["contribution_to_provincial_exposure"] = (
        top["export_exposure_upper_cad"] / prov_exposed_total if prov_exposed_total else 0.0
    )
    return top


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def exposure_share_vector(hs4_table: pd.DataFrame, province_code: str, hs4_index: list[str]) -> np.ndarray:
    prov = hs4_table.loc[hs4_table["province_code"].eq(province_code)].copy()
    total = float(prov["export_exposure_upper_cad"].sum())
    shares = (
        prov.set_index("hs4")["export_exposure_upper_cad"] / total if total else prov.set_index("hs4")["export_exposure_upper_cad"] * 0
    )
    return shares.reindex(hs4_index).fillna(0.0).to_numpy(dtype=float)


def hhi_from_shares(shares: pd.Series) -> float:
    positive = shares.loc[shares > 0]
    if positive.empty:
        return 0.0
    total = float(positive.sum())
    if total <= 0:
        return 0.0
    weights = positive / total
    return float((weights ** 2).sum())


def save_barh(
    frame: pd.DataFrame,
    label_col: str,
    value_col: str,
    title: str,
    xlabel: str,
    path: Path,
    value_scale: float = 1e6,
    value_suffix: str = "M",
    contribution_col: str | None = None,
) -> None:
    chart = frame.sort_values(value_col, ascending=True)
    fig, axis = plt.subplots(figsize=(9.5, 5.8))
    bars = axis.barh(chart[label_col], chart[value_col] / value_scale, color="#1f4e79")
    axis.set_xlabel(xlabel)
    axis.set_title(title)
    xmax = chart[value_col].max() / value_scale
    for bar, (_, row) in zip(bars, chart.iterrows()):
        scaled = row[value_col] / value_scale
        label = f"${scaled:.1f}{value_suffix}"
        if contribution_col and contribution_col in row.index:
            label += f"  (C={row[contribution_col]:.1%})"
        axis.text(
            bar.get_width() + max(xmax * 0.01, 0.05),
            bar.get_y() + bar.get_height() / 2,
            label,
            va="center",
            fontsize=8,
        )
    axis.set_xlim(0, xmax * 1.28 if xmax else 1)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def map_hs2_to_naics_key(hs2: str, bridge: pd.DataFrame) -> str | None:
    code = int(hs2)
    for _, row in bridge.iterrows():
        if int(row["hs2_start"]) <= code <= int(row["hs2_end"]):
            return str(row["naics_match_key"])
    return None


def match_lfs_label(naics_key: str, labels: pd.Series) -> str | None:
    """Map a short bridge key to the full LFS NAICS label string."""
    hits = labels[labels.str.startswith(naics_key, na=False)]
    if hits.empty:
        hits = labels[labels.str.contains(naics_key.split("[")[0].strip(), regex=False, na=False)]
    if hits.empty:
        return None
    # Prefer the aggregate goods industry row (contains '[' and not Durables/Non-durables)
    preferred = hits[~hits.str.contains("Durables|Non-durables|logging|Fishing|Mining, quarrying", regex=True)]
    return str((preferred if not preferred.empty else hits).iloc[0])


def ensure_lfs_employment(force: bool = False) -> pd.DataFrame:
    """Load annual LFS employment by province and NAICS (table 14-10-0023)."""
    if LFS_CACHE_PATH.exists() and not force:
        cached = pd.read_csv(LFS_CACHE_PATH)
        # Rebuild if an older buggy cache summed over gender/age (implausibly large).
        ab_total = cached.loc[
            cached["province_code"].eq("AB")
            & cached["naics_lfs_label"].str.startswith("Total", na=False),
            "employment_thousands",
        ]
        if not ab_total.empty and float(ab_total.iloc[0]) < 5000:
            return cached

    if not LFS_ZIP_PATH.exists():
        print("Downloading Labour Force Survey employment by industry (14-10-0023)...")
        Q2a.download(LFS_ZIP_URL, LFS_ZIP_PATH)
    else:
        print("Using cached LFS zip; rebuilding employment extract...")

    with zipfile.ZipFile(LFS_ZIP_PATH) as archive:
        data_name = [
            name
            for name in archive.namelist()
            if name.endswith(".csv") and "MetaData" not in name
        ][0]
        raw = pd.read_csv(
            archive.open(data_name),
            usecols=[
                "REF_DATE",
                "GEO",
                "Labour force characteristics",
                "North American Industry Classification System (NAICS)",
                "Gender",
                "Age group",
                "VALUE",
            ],
            dtype={"REF_DATE": str, "GEO": str, "VALUE": str},
            low_memory=False,
        )

    frame = raw.rename(
        columns={
            "GEO": "geography",
            "North American Industry Classification System (NAICS)": "naics_lfs_label",
            "VALUE": "employment_thousands",
            "REF_DATE": "ref_date",
        }
    )
    frame["employment_thousands"] = pd.to_numeric(frame["employment_thousands"], errors="coerce")
    frame["province_code"] = frame["geography"].map(PROVINCE_NAME_TO_CODE)
    frame = frame.loc[frame["province_code"].isin(COMPARATOR_CODES)].copy()
    frame = frame.loc[frame["Labour force characteristics"].eq("Employment")].copy()
    frame = frame.loc[frame["Gender"].eq("Total - Gender")].copy()
    frame = frame.loc[frame["Age group"].eq("15 years and over")].copy()

    frame["year"] = frame["ref_date"].astype(str).str.extract(r"(\d{4})")[0]
    latest = frame["year"].dropna().max()
    frame = frame.loc[frame["year"].eq(latest)].copy()

    slim = frame[
        ["year", "province_code", "geography", "naics_lfs_label", "employment_thousands"]
    ].drop_duplicates()
    slim.to_csv(LFS_CACHE_PATH, index=False)
    return slim


def build_employment_risk(
    us: pd.DataFrame,
    s338_hs6: set[str],
    summary: pd.DataFrame,
) -> pd.DataFrame:
    bridge = pd.read_csv(BRIDGE_PATH, dtype=str)
    lfs = ensure_lfs_employment(force=False)

    exposed = us.loc[us["hs6"].isin(s338_hs6)].copy()
    exposed["hs2"] = exposed["hs6"].str[:2]
    exposed["naics_key"] = exposed["hs2"].map(lambda x: map_hs2_to_naics_key(x, bridge))

    us_hs2 = us.copy()
    us_hs2["hs2"] = us_hs2["hs6"].str[:2]
    us_hs2["naics_key"] = us_hs2["hs2"].map(lambda x: map_hs2_to_naics_key(x, bridge))

    rows = []
    for code in COMPARATOR_CODES:
        prov_lfs = lfs.loc[lfs["province_code"].eq(code)].copy()
        labels = prov_lfs["naics_lfs_label"]

        goods_row = prov_lfs.loc[labels.eq("Goods-producing sector"), "employment_thousands"]
        goods_emp = float(goods_row.iloc[0]) * 1000.0 if not goods_row.empty else 0.0

        # Employment in broad goods industries touched by any exposed HS2
        keys_present = set(
            exposed.loc[exposed["province_code"].eq(code), "naics_key"].dropna().unique()
        )
        touched_labels = []
        for key in keys_present:
            label = match_lfs_label(key, labels)
            if label:
                touched_labels.append(label)
        touched_emp = float(
            prov_lfs.loc[prov_lfs["naics_lfs_label"].isin(touched_labels), "employment_thousands"].sum()
        ) * 1000.0

        prov_sum = summary.loc[summary["province_code"].eq(code)].iloc[0]
        exposed_ub = float(prov_sum["s338_exposed_exports_cad"])

        # Intensity-weighted employment by mapped goods industry
        exp_by_key = (
            exposed.loc[exposed["province_code"].eq(code)]
            .groupby("naics_key", as_index=False)["value_cad"]
            .sum()
            .rename(columns={"value_cad": "exposed_exports_upper_cad"})
        )
        us_by_key = (
            us_hs2.loc[us_hs2["province_code"].eq(code)]
            .groupby("naics_key", as_index=False)["value_cad"]
            .sum()
            .rename(columns={"value_cad": "sector_us_exports_cad"})
        )
        merged = exp_by_key.merge(us_by_key, on="naics_key", how="left")
        intensity_weighted_emp = 0.0
        for _, row in merged.iterrows():
            label = match_lfs_label(str(row["naics_key"]), labels)
            if not label:
                continue
            emp = float(
                prov_lfs.loc[prov_lfs["naics_lfs_label"].eq(label), "employment_thousands"].iloc[0]
            ) * 1000.0
            sector_us = float(row["sector_us_exports_cad"] or 0)
            intensity = float(row["exposed_exports_upper_cad"]) / sector_us if sector_us else 0.0
            intensity_weighted_emp += emp * intensity

        rows.append(
            {
                "province_code": code,
                "province": prov_sum["province"],
                "lfs_year": int(lfs["year"].iloc[0]) if len(lfs) else np.nan,
                "s338_exposed_upper_cad": exposed_ub,
                "goods_sector_employment": goods_emp,
                "touched_sector_employment": touched_emp,
                "exposed_exports_per_goods_employee_cad": exposed_ub / goods_emp if goods_emp else np.nan,
                "share_of_goods_employment_in_touched_sectors": touched_emp / goods_emp if goods_emp else np.nan,
                "intensity_weighted_employment": intensity_weighted_emp,
                "note": "Illustrative proxy only; not a job-loss forecast",
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    s338 = Q2a.ensure_s338()
    extract_dir = Q2a.ensure_cimt()
    hs4_names = ensure_hs4_names()

    province_pattern = (
        r"^\d+\s+(?P<code>\S{2})\s+(?P<start>\d{6})\s+(?P<end>\d{6})\s(?P<text>.*)$"
    )
    provinces = Q2a.names_in_force(
        extract_dir / "ODPF_8_ProvDesc.TXT", province_pattern, "province_code"
    ).rename(columns={"name": "province"})

    us = Q2a.load_us_exports(extract_dir)
    us8 = Q2a.load_us_exports_hs8(extract_dir)
    hs6_program = (
        s338.sort_values(["hs6", "hts8"])
        .drop_duplicates("hs6", keep="first")[["hs6", "program"]]
        .copy()
    )
    s338_hs6 = set(hs6_program["hs6"])
    s338_hts8 = set(s338["hts8"])

    hs4_table = province_hs4_tables(us, s338_hs6, provinces)
    hs4_table = hs4_table.merge(hs4_names, on="hs4", how="left")
    lb_hs4 = lower_bound_hs4(us8, s338_hts8)
    hs4_table = hs4_table.merge(lb_hs4, on=["province_code", "hs4"], how="left")
    hs4_table["export_exposure_lower_cad"] = hs4_table["export_exposure_lower_cad"].fillna(0.0)
    # Alias for charts that still say export_exposure_cad
    hs4_table["export_exposure_cad"] = hs4_table["export_exposure_upper_cad"]

    province_us = (
        us.groupby("province_code", as_index=False)["value_cad"]
        .sum()
        .rename(columns={"value_cad": "province_us_exports_cad"})
    )
    province_exposed = (
        hs4_table.groupby("province_code", as_index=False)["export_exposure_upper_cad"]
        .sum()
        .rename(columns={"export_exposure_upper_cad": "s338_exposed_exports_cad"})
    )
    province_lb = (
        hs4_table.groupby("province_code", as_index=False)["export_exposure_lower_cad"]
        .sum()
        .rename(columns={"export_exposure_lower_cad": "s338_exposed_lower_cad"})
    )
    summary = (
        province_us.merge(province_exposed, on="province_code", how="left")
        .merge(province_lb, on="province_code", how="left")
        .merge(provinces, on="province_code", how="left")
    )
    summary["s338_exposed_exports_cad"] = summary["s338_exposed_exports_cad"].fillna(0.0)
    summary["s338_exposed_lower_cad"] = summary["s338_exposed_lower_cad"].fillna(0.0)
    summary["provincial_exposure_intensity"] = (
        summary["s338_exposed_exports_cad"] / summary["province_us_exports_cad"]
    )
    summary["provincial_exposure_intensity_lower"] = (
        summary["s338_exposed_lower_cad"] / summary["province_us_exports_cad"]
    )
    summary = summary.loc[summary["province_code"].isin(COMPARATOR_CODES)].copy()
    order = {code: i for i, code in enumerate(COMPARATOR_CODES)}
    summary["sort_key"] = summary["province_code"].map(order)
    summary = summary.sort_values("sort_key").drop(columns=["sort_key"])

    alberta_top = top_hs4_for_province(hs4_table, "AB", TOP_N)
    alberta_top["province_code"] = "AB"
    alberta_top["province"] = provinces.loc[
        provinces["province_code"].eq("AB"), "province"
    ].item()

    comparator_tops = []
    top_sets: dict[str, set[str]] = {}
    for code in COMPARATOR_CODES:
        top = top_hs4_for_province(hs4_table, code, TOP_N)
        top["province_code"] = code
        top["province"] = provinces.loc[
            provinces["province_code"].eq(code), "province"
        ].item()
        comparator_tops.append(top)
        top_sets[code] = set(top["hs4"])
    comparator_top = pd.concat(comparator_tops, ignore_index=True)

    # Similarity: Jaccard on top-10 + cosine on full HS4 exposure-share vectors
    all_hs4 = sorted(hs4_table.loc[hs4_table["export_exposure_upper_cad"].gt(0), "hs4"].unique())
    ab_vec = exposure_share_vector(hs4_table, "AB", all_hs4)
    similarity_rows = []
    for code in [c for c in COMPARATOR_CODES if c != "AB"]:
        other = top_sets[code]
        shared = sorted(top_sets["AB"] & other)
        other_vec = exposure_share_vector(hs4_table, code, all_hs4)
        similarity_rows.append(
            {
                "alberta_comparator": f"AB vs {code}",
                "shared_top10_hs4_count": len(shared),
                "jaccard_top10": jaccard(top_sets["AB"], other),
                "cosine_similarity_hs4_shares": cosine_similarity(ab_vec, other_vec),
                "shared_hs4_codes": ";".join(shared),
            }
        )
    similarity = pd.DataFrame(similarity_rows)

    # HHI at HS4 and HS2
    hhi_rows = []
    for code in COMPARATOR_CODES:
        prov = hs4_table.loc[hs4_table["province_code"].eq(code)].copy()
        hs4_shares = prov.set_index("hs4")["export_exposure_upper_cad"]
        prov["hs2"] = prov["hs4"].str[:2]
        hs2_shares = prov.groupby("hs2")["export_exposure_upper_cad"].sum()
        top10_share = float(
            comparator_top.loc[comparator_top["province_code"].eq(code), "contribution_to_provincial_exposure"].sum()
        )
        hhi_rows.append(
            {
                "province_code": code,
                "province": provinces.loc[provinces["province_code"].eq(code), "province"].item(),
                "hhi_hs4": hhi_from_shares(hs4_shares),
                "hhi_hs2": hhi_from_shares(hs2_shares),
                "top10_share_of_s338_exposure": top10_share,
                "s338_exposed_upper_cad": float(
                    summary.loc[summary["province_code"].eq(code), "s338_exposed_exports_cad"].item()
                ),
            }
        )
    hhi = pd.DataFrame(hhi_rows)

    print("Building employment-risk proxy from LFS...")
    employment = build_employment_risk(us, s338_hs6, summary)

    # Charts
    ab_chart = alberta_top.copy()
    ab_chart["label"] = ab_chart["hs4"] + " – " + ab_chart["product_name"].fillna("").str.slice(0, 40)
    save_barh(
        ab_chart,
        "label",
        "export_exposure_upper_cad",
        "Alberta's major Section 338–exposed HS4 products, 2025 (upper bound)",
        "Export exposure to the U.S. (million CAD)",
        OUTPUT_DIR / "q2b_alberta_top_hs4.png",
        value_scale=1e6,
        value_suffix="M",
        contribution_col="contribution_to_provincial_exposure",
    )

    intensity_chart = summary.sort_values("provincial_exposure_intensity", ascending=True)
    fig, axis = plt.subplots(figsize=(8.5, 4.8))
    y = np.arange(len(intensity_chart))
    height = 0.35
    axis.barh(
        y - height / 2,
        intensity_chart["provincial_exposure_intensity_lower"] * 100,
        height=height,
        color="#7a9bb8",
        label="Lower bound",
    )
    axis.barh(
        y + height / 2,
        intensity_chart["provincial_exposure_intensity"] * 100,
        height=height,
        color="#1f4e79",
        label="Upper bound",
    )
    axis.set_yticks(y)
    axis.set_yticklabels(intensity_chart["province"])
    axis.set_xlabel("Provincial exposure intensity (% of province → U.S. exports)")
    axis.set_title("Section 338 provincial exposure intensity range, 2025")
    axis.legend(frameon=False, loc="lower right")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2b_province_intensity.png", dpi=150)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8.5, 4.8))
    order_hhi = hhi.set_index("province_code").loc[COMPARATOR_CODES]
    x = np.arange(len(order_hhi))
    width = 0.35
    axis.bar(x - width / 2, order_hhi["hhi_hs4"], width=width, color="#1f4e79", label="HHI (HS4)")
    axis.bar(x + width / 2, order_hhi["hhi_hs2"], width=width, color="#7a9bb8", label="HHI (HS2)")
    axis.set_xticks(x)
    axis.set_xticklabels(order_hhi["province"], rotation=15, ha="right")
    axis.set_ylabel("Herfindahl–Hirschman index of S338 exposure shares")
    axis.set_title("How concentrated is Section 338 exposure across products?")
    axis.legend(frameon=False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2b_concentration_hhi.png", dpi=150)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4.5))
    sim_plot = similarity.copy()
    axis.bar(
        np.arange(len(sim_plot)) - 0.2,
        sim_plot["jaccard_top10"],
        width=0.4,
        color="#7a9bb8",
        label="Jaccard (top-10 HS4)",
    )
    axis.bar(
        np.arange(len(sim_plot)) + 0.2,
        sim_plot["cosine_similarity_hs4_shares"],
        width=0.4,
        color="#1f4e79",
        label="Cosine (full HS4 shares)",
    )
    axis.set_xticks(np.arange(len(sim_plot)))
    axis.set_xticklabels(sim_plot["alberta_comparator"])
    axis.set_ylim(0, 1)
    axis.set_ylabel("Similarity to Alberta")
    axis.set_title("Alberta Section 338 product-mix similarity")
    axis.legend(frameon=False)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2b_composition_similarity.png", dpi=150)
    plt.close(fig)

    fig, axis = plt.subplots(figsize=(8, 4.5))
    emp_plot = employment.set_index("province_code").loc[COMPARATOR_CODES]
    axis.bar(emp_plot["province"], emp_plot["exposed_exports_per_goods_employee_cad"] / 1000, color="#1f4e79")
    axis.set_ylabel("Exposed exports per goods-sector employee (thousand CAD)")
    axis.set_title("Illustrative employment-linked exposure proxy, 2025 trade / LFS employment")
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2b_employment_risk.png", dpi=150)
    plt.close(fig)

    # Keep top-10 concentration chart
    composition = hhi[
        ["province_code", "province", "top10_share_of_s338_exposure", "s338_exposed_upper_cad"]
    ].merge(
        summary[["province_code", "provincial_exposure_intensity"]],
        on="province_code",
        how="left",
    )
    fig, axis = plt.subplots(figsize=(8, 4.5))
    order_frame = composition.set_index("province_code").loc[COMPARATOR_CODES]
    axis.bar(order_frame["province"], order_frame["top10_share_of_s338_exposure"] * 100, color="#1f4e79")
    axis.set_ylabel("Top-10 HS4 share of provincial S338 exposure (%)")
    axis.set_title("How concentrated is Section 338 exposure in the top 10 HS4s?")
    axis.set_ylim(0, 100)
    axis.spines["top"].set_visible(False)
    axis.spines["right"].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "q2b_top10_concentration.png", dpi=150)
    plt.close(fig)

    alberta_out = alberta_top[
        [
            "product_rank",
            "hs4",
            "product_name",
            "export_exposure_upper_cad",
            "export_exposure_lower_cad",
            "exposure_intensity",
            "contribution_to_provincial_exposure",
            "us_exports_hs4_cad",
        ]
    ].rename(
        columns={
            "hs4": "hs4_code",
            "export_exposure_upper_cad": "export_exposure_cad",
        }
    )
    alberta_out.to_csv(OUTPUT_DIR / "q2b_alberta_top_hs4.csv", index=False)

    comparator_out = comparator_top[
        [
            "province_code",
            "province",
            "product_rank",
            "hs4",
            "product_name",
            "export_exposure_upper_cad",
            "export_exposure_lower_cad",
            "exposure_intensity",
            "contribution_to_provincial_exposure",
            "us_exports_hs4_cad",
        ]
    ].rename(
        columns={
            "hs4": "hs4_code",
            "export_exposure_upper_cad": "export_exposure_cad",
        }
    )
    comparator_out.to_csv(OUTPUT_DIR / "q2b_comparator_top_hs4.csv", index=False)

    summary[
        [
            "province_code",
            "province",
            "province_us_exports_cad",
            "s338_exposed_lower_cad",
            "s338_exposed_exports_cad",
            "provincial_exposure_intensity_lower",
            "provincial_exposure_intensity",
        ]
    ].rename(columns={"s338_exposed_exports_cad": "s338_exposed_upper_cad"}).to_csv(
        OUTPUT_DIR / "q2b_province_summary.csv", index=False
    )

    similarity.to_csv(OUTPUT_DIR / "q2b_composition_similarity.csv", index=False)
    # Keep old filename as alias for notebook continuity
    similarity.to_csv(OUTPUT_DIR / "q2b_composition_overlap.csv", index=False)
    hhi.to_csv(OUTPUT_DIR / "q2b_concentration_hhi.csv", index=False)
    composition.to_csv(OUTPUT_DIR / "q2b_top10_concentration.csv", index=False)
    employment.to_csv(OUTPUT_DIR / "q2b_employment_risk.csv", index=False)

    print("Alberta top HS4 by Section 338 exposure (upper bound):")
    for _, row in alberta_out.iterrows():
        print(
            f"  {int(row['product_rank'])}. {row['hs4_code']}  "
            f"${row['export_exposure_cad']:,.0f}  "
            f"intensity={row['exposure_intensity']:.1%}  "
            f"contribution={row['contribution_to_provincial_exposure']:.1%}"
        )
    print("\nProvincial exposure intensity (LB – UB):")
    for _, row in summary.iterrows():
        print(
            f"  {row['province']}: "
            f"${row['s338_exposed_lower_cad']:,.0f} – ${row['s338_exposed_exports_cad']:,.0f}  "
            f"intensity {row['provincial_exposure_intensity_lower']:.1%} – "
            f"{row['provincial_exposure_intensity']:.1%}"
        )
    print("\nSimilarity to Alberta:")
    for _, row in similarity.iterrows():
        print(
            f"  {row['alberta_comparator']}: Jaccard={row['jaccard_top10']:.2f}  "
            f"cosine={row['cosine_similarity_hs4_shares']:.2f}"
        )
    print("\nHHI (HS4):")
    for _, row in hhi.iterrows():
        print(f"  {row['province']}: {row['hhi_hs4']:.3f}")
    print("\nEmployment proxy (exposed CAD per goods employee):")
    for _, row in employment.iterrows():
        print(
            f"  {row['province']}: ${row['exposed_exports_per_goods_employee_cad']:,.0f} "
            f"(touched emp share {row['share_of_goods_employment_in_touched_sectors']:.1%})"
        )
    print("Wrote", OUTPUT_DIR)


if __name__ == "__main__":
    main()
