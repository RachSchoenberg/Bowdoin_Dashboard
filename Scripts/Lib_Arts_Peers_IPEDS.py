'''
PURPOSE:
    Pulls longitudinal IPEDS data for ALL small private liberal arts colleges
    (Carnegie Classification 21 — Baccalaureate: Arts & Sciences Focus)
    from the Urban Institute Education Data Portal API.
    Fetches the same metrics as bowdoin_ipeds.csv so the two files can be
    merged and compared directly. Saves one CSV of all peer institutions
    and one CSV of peer averages per year for benchmark line visualization.

FLOW:
    1. Fetch the IPEDS directory for each year to identify all unitids
       with Carnegie class 21 and control=2 (private nonprofit)
    2. For each year, pull admissions, fall-enrollment, and grad-rate data
       for the full peer group in a single API call (no unitid filter)
    3. Filter results to only peer unitids identified in step 1
    4. Merge all three endpoints on year + unitid
    5. Derive acceptance_rate and yield_rate per institution per year
    6. Save full peer dataset and year-level averages to separate CSVs

RETURNS:
    peers_raw.csv       — one row per institution per year:
                          unitid, inst_name, year, applied, admitted,
                          enrolled, acceptance_rate, yield_rate,
                          est_fte, grad_rate_150

    peers_avg.csv       — one row per year (peer group averages):
                          year, avg_applied, avg_admitted, avg_enrolled,
                          avg_acceptance_rate, avg_yield_rate,
                          avg_est_fte, avg_grad_rate_150, n_institutions
'''

import requests
import pandas as pd
import time

# ── CONFIG -------------------------------------------------------------------
OUTPUT_RAW  = "/Users/raychellin/Desktop/Bowdoin/peers_raw.csv"
OUTPUT_AVG  = "/Users/raychellin/Desktop/Bowdoin/peers_avg.csv"
BASE_URL    = "https://educationdata.urban.org/api/v1/college-university/ipeds"
YEARS       = range(2001, 2023)
CARNEGIE    = 21    # Baccalaureate Colleges: Arts & Sciences Focus
CONTROL     = 2     # Private nonprofit
BOWDOIN_ID  = 161004
SLEEP       = 0.5   # seconds between requests — be polite to the API
TIMEOUT     = 120   # seconds — large responses need more time
MAX_RETRIES = 3     # retry failed requests before giving up
BATCH_SIZE  = 50    # unitids per request — keeps response sizes manageable
# ----------------------------------------------------------------------------


'''
PURPOSE:
    Fetches all pages from a given API endpoint URL, following the "next"
    pagination field until all records are retrieved. Includes a small sleep
    between requests to avoid overwhelming the API.

RETURNS:
    list of dicts — all records across all pages,
    or empty list if the initial request fails.
'''
def fetch_all_pages(url):
    rows = []
    while url:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                resp = requests.get(url, timeout=TIMEOUT)
                if resp.status_code != 200:
                    return []
                data  = resp.json()
                rows += data.get("results", [])
                url   = data.get("next")
                time.sleep(SLEEP)
                break                           # success — exit retry loop
            except requests.exceptions.ReadTimeout:
                wait = attempt * 10
                print(f"  ⏱ Timeout (attempt {attempt}/{MAX_RETRIES}) "
                      f"— retrying in {wait}s...")
                time.sleep(wait)
        else:
            print(f"  ✗ Failed after {MAX_RETRIES} attempts — skipping.")
            return rows
    return rows


'''
PURPOSE:
    Fetches the IPEDS institutional directory for a given year and filters
    to private nonprofit liberal arts colleges using the correct column names
    confirmed via diagnostic: inst_control=2 (private nonprofit) and the
    appropriate cc_basic_{decade} column = 21 (Baccalaureate: Arts & Sciences).
    Carnegie classification columns are decade-specific in this API:
      cc_basic_2000  → years 2001-2009
      cc_basic_2010  → years 2010-2014
      cc_basic_2015  → years 2015-2017
      cc_basic_2018  → years 2018-2020
      cc_basic_2021  → years 2021+

RETURNS:
    set of ints — unitids of all qualifying peer institutions for that year,
    or empty set if the request fails.
'''
def get_peer_unitids(year):
    url  = f"{BASE_URL}/directory/{year}/"
    rows = fetch_all_pages(url)
    if not rows:
        return set()
    df = pd.DataFrame(rows)

    # Pick the right Carnegie column for this year
    if year <= 2009:
        cc_col = "cc_basic_2000"
    elif year <= 2014:
        cc_col = "cc_basic_2010"
    elif year <= 2017:
        cc_col = "cc_basic_2015"
    elif year <= 2020:
        cc_col = "cc_basic_2018"
    else:
        cc_col = "cc_basic_2021"

    # Filter in-memory using confirmed column names
    if cc_col in df.columns:
        df = df[df[cc_col] == CARNEGIE]
    if "inst_control" in df.columns:
        df = df[df["inst_control"] == CONTROL]

    print(f"  → {len(df)} peer institutions (filter: {cc_col}=={CARNEGIE}, inst_control=={CONTROL})")
    return set(df["unitid"].tolist())


'''
PURPOSE:
    Fetches data for a given endpoint and year in batches of BATCH_SIZE
    unitids at a time, using the unitid filter in the URL to keep each
    request small and avoid timeouts. Combines all batch results into
    a single list.

RETURNS:
    list of dicts — all records for the given peer institutions,
    combined across all batches.
'''
def fetch_endpoint_batched(endpoint, year, peer_ids):
    id_list = list(peer_ids)
    all_rows = []
    for i in range(0, len(id_list), BATCH_SIZE):
        batch     = id_list[i:i + BATCH_SIZE]
        id_str    = ",".join(str(u) for u in batch)
        url       = f"{BASE_URL}/{endpoint}/{year}/?unitid={id_str}"
        batch_rows = fetch_all_pages(url)
        all_rows.extend(batch_rows)
        print(f"    batch {i // BATCH_SIZE + 1}: {len(batch_rows)} records")
    return all_rows


'''
PURPOSE:
    Fetches admissions data for a given year for all peer institutions
    using batched requests. Sums men + women rows (sex=1 and sex=2)
    to produce institution-level totals per year.

RETURNS:
    pd.DataFrame — columns: unitid, year, applied, admitted, enrolled
    Only peer institutions with valid data are included.
'''
def get_admissions_year(year, peer_ids):
    rows = fetch_endpoint_batched("admissions-enrollment", year, peer_ids)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    df = df[df["sex"].isin([1, 2])]
    df = df.groupby(["unitid", "year"], as_index=False).agg(
        applied  = ("number_applied",        "sum"),
        admitted = ("number_admitted",        "sum"),
        enrolled = ("number_enrolled_total",  "sum"),
    )
    return df


'''
PURPOSE:
    Fetches fall enrollment (FTE) data for a given year for all peer
    institutions using batched requests. Keeps undergraduate level only
    (level_of_study=1) and uses rep_fte as the enrollment proxy.

RETURNS:
    pd.DataFrame — columns: unitid, year, est_fte
    Only peer institutions with valid data are included.
'''
def get_enrollment_year(year, peer_ids):
    rows = fetch_endpoint_batched("fall-enrollment", year, peer_ids)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    if "level_of_study" in df.columns:
        df = df[df["level_of_study"] == 1]

    cols = {"unitid": "unitid", "year": "year", "rep_fte": "est_fte"}
    df = df[[c for c in cols if c in df.columns]].rename(columns=cols)
    return df.groupby(["unitid", "year"], as_index=False).first()


'''
PURPOSE:
    Fetches graduation rate data for a given year for all peer institutions
    using batched requests. Filters to total cohort (subcohort=99, race=99,
    sex=2) and converts decimal rates to percentages.

RETURNS:
    pd.DataFrame — columns: unitid, year, grad_rate_150
    Only peer institutions with valid data are included.
'''
def get_grad_rates_year(year, peer_ids):
    rows = fetch_endpoint_batched("grad-rates", year, peer_ids)
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows)
    for col, val in [("subcohort", 99), ("race", 99), ("sex", 2)]:
        if col in df.columns:
            df = df[df[col] == val]

    if "completion_rate_150pct" not in df.columns:
        return pd.DataFrame()

    df = df[["unitid", "year", "completion_rate_150pct"]].rename(
        columns={"completion_rate_150pct": "grad_rate_150"})
    df["grad_rate_150"] = (df["grad_rate_150"] * 100).round(1)
    return df.groupby(["unitid", "year"], as_index=False).first()


'''
PURPOSE:
    Fetches institution names from the IPEDS directory for a given year,
    filtered to peer unitids. Used to add human-readable names to the
    final output so schools can be identified in the visualization.

RETURNS:
    pd.DataFrame — columns: unitid, inst_name
    or empty DataFrame if the request fails.
'''
def get_inst_names(year, peer_ids):
    url  = f"{BASE_URL}/directory/{year}/"
    rows = fetch_all_pages(url)
    if not rows:
        return pd.DataFrame()
    df = pd.DataFrame(rows)
    df = df[df["unitid"].isin(peer_ids)]
    if "inst_name" not in df.columns:
        return pd.DataFrame()
    return df[["unitid", "inst_name"]].drop_duplicates()


# ── MAIN --------------------------------------------------------------------
all_rows  = []
name_rows = []

for yr in YEARS:
    print(f"\nProcessing {yr}...")

    # Build peer group for this year -----------------------------------------
    peer_ids = get_peer_unitids(yr)
    if not peer_ids:
        print(f"  ✗ No peer institutions found for {yr}")
        continue
    print(f"  → {len(peer_ids)} peer institutions identified")

    # Fetch institution names (once per year, deduplicated later) ------------
    names = get_inst_names(yr, peer_ids)
    name_rows.append(names)

    # Fetch all three endpoints ----------------------------------------------
    adm  = get_admissions_year(yr, peer_ids)
    enr  = get_enrollment_year(yr, peer_ids)
    grad = get_grad_rates_year(yr, peer_ids)

    # Merge on unitid + year -------------------------------------------------
    dfs = [d for d in [adm, enr, grad]
           if not d.empty and "unitid" in d.columns and "year" in d.columns]

    if not dfs:
        print(f"  ✗ No data merged for {yr}")
        continue

    merged = dfs[0]
    for d in dfs[1:]:
        merged = merged.merge(d, on=["unitid", "year"], how="outer")

    all_rows.append(merged)
    print(f"  ✓ {len(merged)} institution-year rows merged")

# ── BUILD FULL DATASET ------------------------------------------------------
if not all_rows:
    print("No data retrieved.")
else:
    df = pd.concat([r for r in all_rows if not r.empty], ignore_index=True)

    # Add institution names --------------------------------------------------
    all_names = pd.concat(name_rows, ignore_index=True).drop_duplicates("unitid")
    df = df.merge(all_names, on="unitid", how="left")

    # Derived Metrics --------------------------------------------------------
    if {"applied", "admitted"}.issubset(df.columns):
        df["acceptance_rate"] = (
            df["admitted"] / df["applied"].replace(0, pd.NA) * 100
        ).round(1)
    if {"admitted", "enrolled"}.issubset(df.columns):
        df["yield_rate"] = (
            df["enrolled"] / df["admitted"].replace(0, pd.NA) * 100
        ).round(1)

    # Flag Bowdoin -----------------------------------------------------------
    df["is_bowdoin"] = df["unitid"] == BOWDOIN_ID

    # Sort -------------------------------------------------------------------
    df = df.sort_values(["year", "unitid"]).reset_index(drop=True)

    # Save raw peer data -----------------------------------------------------
    df.to_csv(OUTPUT_RAW, index=False)
    print(f"\nSaved {len(df)} rows → {OUTPUT_RAW}")

    # ── PEER AVERAGES BY YEAR -----------------------------------------------
    avg_cols = [c for c in ["applied", "admitted", "enrolled",
                             "acceptance_rate", "yield_rate",
                             "est_fte", "grad_rate_150"] if c in df.columns]

    peers_only = df[df["unitid"] != BOWDOIN_ID]
    avg_df = peers_only.groupby("year")[avg_cols].mean().round(2).reset_index()
    avg_df.columns = ["year"] + [f"avg_{c}" for c in avg_cols]
    avg_df["n_institutions"] = peers_only.groupby("year")["unitid"].nunique().values

    avg_df.to_csv(OUTPUT_AVG, index=False)
    print(f"Saved {len(avg_df)} rows → {OUTPUT_AVG}")
    print(avg_df[["year", "avg_acceptance_rate",
                  "avg_yield_rate", "n_institutions"]].to_string())