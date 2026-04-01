'''
PURPOSE:
    Pulls longitudinal IPEDS data for Bowdoin College (unitid=161004)
    from the Urban Institute Education Data Portal API — no API key required.
    Fetches three survey endpoints (admissions, fall-enrollment, grad-rates),
    filters each to Bowdoin only, merges them on year, and saves a single CSV.

FLOW:
    1. Loop over each year in YEARS range for each endpoint
    2. Build URL with year in path: /api/v1/college-university/ipeds/{endpoint}/{year}/
    3. Filter results to Bowdoin by unitid, paginate if needed
    4. Clean and reshape each dataset using confirmed API column names
    5. Merge all three datasets on year into one wide DataFrame
    6. Derive calculated fields: acceptance_rate, yield_rate
    7. Save to bowdoin_ipeds.csv

RETURNS:
    bowdoin_ipeds.csv — one row per year containing:
        year, applied, admitted, enrolled,
        acceptance_rate, yield_rate,
        est_fte, grad_rate_150
'''

import requests
import pandas as pd

# ── CONFIG -------------------------------------------------------------------
UNIT_ID    = 161004
OUTPUT_CSV = "/Users/raychellin/Desktop/Bowdoin/bowdoin_ipeds.csv"
BASE_URL   = "https://educationdata.urban.org/api/v1/college-university/ipeds"
YEARS      = range(2001, 2023)   # 2023 returned no data across all endpoints
# ----------------------------------------------------------------------------


'''
PURPOSE:
    Fetches all records for a single endpoint + year, filtered to one
    institution by unitid. The Urban Institute API requires year in the
    URL path: /endpoint/year/. Paginates automatically via "next" field.

RETURNS:
    list of dicts — all matching records for that endpoint/year combination,
    or empty list if the request fails or returns no results.
'''
def fetch_year(endpoint, year, unitid):
    url  = f"{BASE_URL}/{endpoint}/{year}/?unitid={unitid}"
    rows = []
    while url:
        resp = requests.get(url, timeout=30)
        if resp.status_code != 200:
            return []
        data  = resp.json()
        rows += data.get("results", [])
        url   = data.get("next")
    return rows


'''
PURPOSE:
    Loops over all years in YEARS and fetches admissions data for each.
    Confirmed API columns: number_applied, number_admitted,
    number_enrolled_total, sex (1=men, 2=women — no total row).
    Aggregates men + women to produce institution-level totals per year.

RETURNS:
    pd.DataFrame — columns: year, applied, admitted, enrolled
    Only years with valid data are included.
'''
def get_admissions(unitid):
    print("Fetching admissions data...")
    rows = []
    for yr in YEARS:
        yr_rows = fetch_year("admissions-enrollment", yr, unitid)
        rows.extend(yr_rows)
        print(f"  {'✓' if yr_rows else '–'} {yr}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # No total row — sum men (sex=1) and women (sex=2) to get institution totals
    df = df[df["sex"].isin([1, 2])]
    df = df.groupby("year", as_index=False).agg(
        applied  = ("number_applied",       "sum"),
        admitted = ("number_admitted",       "sum"),
        enrolled = ("number_enrolled_total", "sum"),
    )
    return df


'''
PURPOSE:
    Loops over all years in YEARS and fetches fall enrollment FTE data.
    Confirmed API columns: est_fte, rep_fte, level_of_study.
    Filters to level_of_study=1 (undergraduate) and uses rep_fte
    (reported FTE) as the enrollment proxy since headcount is not available
    in this endpoint.

RETURNS:
    pd.DataFrame — columns: year, est_fte
    Only years with valid data are included.
'''
def get_enrollment(unitid):
    print("Fetching enrollment (FTE) data...")
    rows = []
    for yr in YEARS:
        yr_rows = fetch_year("fall-enrollment", yr, unitid)
        rows.extend(yr_rows)
        print(f"  {'✓' if yr_rows else '–'} {yr}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Keep undergraduate level only
    if "level_of_study" in df.columns:
        df = df[df["level_of_study"] == 1]

    cols = {"year": "year", "rep_fte": "est_fte"}
    df = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    return df.groupby("year", as_index=False).first()


'''
PURPOSE:
    Loops over all years in YEARS and fetches 6-year graduation rate data.
    Confirmed API columns: completion_rate_150pct, subcohort, race, sex.
    Filters to total cohort: subcohort=99 (all), race=99 (all), sex=2
    (sex=2 is the "total" row in this endpoint based on diagnostic output).

RETURNS:
    pd.DataFrame — columns: year, grad_rate_150
    Rates are stored as decimals (0.922); multiplied by 100 for percentages.
    Only years with valid data are included.
'''
def get_grad_rates(unitid):
    print("Fetching graduation rate data...")
    rows = []
    for yr in YEARS:
        yr_rows = fetch_year("grad-rates", yr, unitid)
        rows.extend(yr_rows)
        print(f"  {'✓' if yr_rows else '–'} {yr}")

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)

    # Filter to total cohort row: subcohort=99, race=99, sex=2
    for col, val in [("subcohort", 99), ("race", 99), ("sex", 2)]:
        if col in df.columns:
            df = df[df[col] == val]

    if "completion_rate_150pct" not in df.columns:
        return pd.DataFrame()

    df = df[["year", "completion_rate_150pct"]].rename(
        columns={"completion_rate_150pct": "grad_rate_150"})

    # Convert decimal to percentage
    df["grad_rate_150"] = (df["grad_rate_150"] * 100).round(1)

    return df.groupby("year", as_index=False).first()


# ── MAIN --------------------------------------------------------------------
adm_df  = get_admissions(UNIT_ID)
enr_df  = get_enrollment(UNIT_ID)
grad_df = get_grad_rates(UNIT_ID)

# Guard: only merge DataFrames that are non-empty and have a year column -----
dfs = [d for d in [adm_df, enr_df, grad_df]
       if not d.empty and "year" in d.columns]

if not dfs:
    print("No data retrieved — check your internet connection or YEARS range.")
else:
    df = dfs[0]
    for d in dfs[1:]:
        df = df.merge(d, on="year", how="outer")
    df = df.sort_values("year").reset_index(drop=True)

    # Derived Metrics (Acceptance Rate & Yield) ----------------------------------
    if {"applied", "admitted"}.issubset(df.columns):
        df["acceptance_rate"] = (df["admitted"] / df["applied"] * 100).round(1)
    if {"admitted", "enrolled"}.issubset(df.columns):
        df["yield_rate"] = (df["enrolled"] / df["admitted"] * 100).round(1)

    # Save to CSV ----------------------------------------------------------------
    df.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(df)} rows → {OUTPUT_CSV}")

    # Print only columns that actually exist ------------------------------------
    display_cols = [c for c in
        ["year", "applied", "admitted", "enrolled",
         "acceptance_rate", "yield_rate", "est_fte", "grad_rate_150"]
        if c in df.columns]
    print(df[display_cols].to_string())