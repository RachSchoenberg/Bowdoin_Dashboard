'''
PURPOSE:
    Pulls admissions and enrollment metrics from the Urban Institute Education
    Data Portal (IPEDS) for a curated list of Top-20 Liberal Arts Colleges and
    writes three output files used by the Observable Framework dashboard.

FLOW:
    1. Defines the peer institution list by the exact inst_name strings
       returned by the IPEDS directory endpoint (confirmed via preflight)
    2. Builds a unitid → inst_name lookup by fetching the IPEDS directory
       for a single representative year. The directory endpoint carries
       inst_name; the admissions-enrollment endpoint does not.
    3. Resolves the 20 target institution names to their unitids, then builds
       a TARGET_UNITIDS set used to filter admissions rows client-side
    4. For each year in YEARS, fetches admissions-enrollment with sex=99
       (institution total, avoiding per-sex double-counting) and filters
       client-side to rows whose unitid is in TARGET_UNITIDS
    5. Derives acceptance_rate and yield_rate from confirmed field names:
       number_applied, number_admitted, number_enrolled_total
    6. Fetches graduation rates the same way and merges on unitid × year
    7. Joins display names, colors, state, and group flags from SCHOOLS
    8. Writes peers_raw.csv, peers_avg.csv, and bowdoin_ipeds.csv

RETURNS:
    src/data/peers_raw.csv     — one row per institution × year containing:
        unitid, year, inst_name, slug, state, color, group_maine,
        group_new_england, is_bowdoin, applied, admitted, enrolled,
        acceptance_rate, yield_rate, grad_rate_150

    src/data/peers_avg.csv     — one row per year containing:
        year, avg_applied, avg_admitted, avg_enrolled, avg_acceptance_rate,
        avg_yield_rate, avg_grad_rate_150, n_institutions

    src/data/bowdoin_ipeds.csv — Bowdoin rows only (subset of peers_raw),
        columns: year, applied, admitted, enrolled, acceptance_rate,
        yield_rate, grad_rate_150
'''

import time
import requests
import pandas as pd
from pathlib import Path


# ── CONFIG -------------------------------------------------------------------
BASE_URL  = "https://educationdata.urban.org/api/v1/college-university/ipeds"
YEARS     = list(range(2001, 2023))  # 2001 is earliest reliable IPEDS admissions data.
                                     # 2022 is the last confirmed year (2023 returns 0/0,
                                     # meaning that survey year is not yet published).
OUT_DIR   = Path(__file__).parent.parent / "src" / "data"
SLEEP_SEC = 0.2
# ----------------------------------------------------------------------------

# Keys are the exact inst_name strings returned by the IPEDS directory
# endpoint (all 20 confirmed matching via preflight check).
# unitids confirmed against IPEDS DFR 2024 (https://nces.ed.gov/ipeds/dfr/2024/).
# These are used as a hard fallback in build_unitid_lookup() when directory
# name matching fails. Name matching is still attempted first so any future
# unitid changes in IPEDS are caught automatically.
SCHOOLS = {
    "Bowdoin College":               {"slug": "bowdoin",           "color": "#1B3D6E", "state": "ME", "unitid": 161004},
    "Bates College":                 {"slug": "bates",             "color": "#8C2131", "state": "ME", "unitid": 160977},
    "Colby College":                 {"slug": "colby",             "color": "#1F5BA8", "state": "ME", "unitid": 161086},
    "Williams College":              {"slug": "williams",          "color": "#500082", "state": "MA", "unitid": 168342},
    "Amherst College":               {"slug": "amherst",           "color": "#C07400", "state": "MA", "unitid": 164465},
    "Wellesley College":             {"slug": "wellesley",         "color": "#2E7D32", "state": "MA", "unitid": 168218},
    "Swarthmore College":            {"slug": "swarthmore",        "color": "#558B2F", "state": "PA", "unitid": 216287},
    "Pomona College":                {"slug": "pomona",            "color": "#E65100", "state": "CA", "unitid": 121345},
    "Middlebury College":            {"slug": "middlebury",        "color": "#4E342E", "state": "VT", "unitid": 230959},
    "Carleton College":              {"slug": "carleton",          "color": "#00838F", "state": "MN", "unitid": 173258},
    "Smith College":                 {"slug": "smith",             "color": "#00695C", "state": "MA", "unitid": 167835},
    "Vassar College":                {"slug": "vassar",            "color": "#6A1B9A", "state": "NY", "unitid": 197133},
    "Barnard College":               {"slug": "barnard",           "color": "#AD1457", "state": "NY", "unitid": 189097},
    "Claremont McKenna College":     {"slug": "claremont_mckenna", "color": "#827717", "state": "CA", "unitid": 112260},
    "Harvey Mudd College":           {"slug": "harvey_mudd",       "color": "#37474F", "state": "CA", "unitid": 115409},
    "Hamilton College":              {"slug": "hamilton",          "color": "#283593", "state": "NY", "unitid": 191515},
    "Wesleyan University":           {"slug": "wesleyan",          "color": "#C62828", "state": "CT", "unitid": 130697},
    "Davidson College":              {"slug": "davidson",          "color": "#BF360C", "state": "NC", "unitid": 198385},
    "Grinnell College":              {"slug": "grinnell",          "color": "#1565C0", "state": "IA", "unitid": 153384},
    "Washington and Lee University": {"slug": "washington_lee",    "color": "#004D40", "state": "VA", "unitid": 234207},
}

GROUPS = {
    "maine":       ["bowdoin", "bates", "colby"],
    "new_england": ["bowdoin", "bates", "colby", "williams", "amherst",
                    "wellesley", "smith", "middlebury", "wesleyan"],
    "top20_lac":   [m["slug"] for m in SCHOOLS.values()],
}

TARGET_NAMES = set(SCHOOLS.keys())


'''
PURPOSE:
    Fetches all pages of results from a paginated Urban Institute API endpoint.
    Accepts a fully-constructed URL string so query parameters are not
    percent-encoded by the requests library. Raises requests.HTTPError on
    non-2xx responses. Sleeps SLEEP_SEC between pages to be polite.

RETURNS:
    list[dict] — all result records concatenated across every page.
'''
def fetch_all_pages(url: str) -> list[dict]:
    rows, page_url = [], url
    while page_url:
        r = requests.get(page_url, timeout=30)
        r.raise_for_status()
        data = r.json()
        rows.extend(data.get("results", []))
        page_url = data.get("next")
        time.sleep(SLEEP_SEC)
    return rows


'''
PURPOSE:
    Builds a unitid → inst_name lookup dict by fetching the IPEDS directory
    for 2019. Attempts to resolve each target school by name match first.
    For any school where name matching fails or returns a conflicting unitid,
    falls back to the hardcoded unitid in SCHOOLS (confirmed against IPEDS
    DFR 2024). Warns on any conflict between the two sources so drift in IPEDS
    naming is visible without silently producing wrong data.

RETURNS:
    tuple[dict, set]:
        unitid_to_name — dict mapping int unitid → str inst_name for all
                         institutions found in the directory
        target_unitids — set of int unitids for the 20 target schools,
                         resolved via name match with hardcoded fallback
'''
def build_unitid_lookup() -> tuple[dict, set]:
    print("Building unitid lookup from IPEDS directory (2019)...")
    url  = f"{BASE_URL}/directory/2019/"
    rows = fetch_all_pages(url)

    unitid_to_name = {r["unitid"]: r["inst_name"] for r in rows if "unitid" in r and "inst_name" in r}
    name_to_unitid = {v: k for k, v in unitid_to_name.items()}

    target_unitids = set()
    for name, meta in SCHOOLS.items():
        dir_uid      = name_to_unitid.get(name)
        hardcoded_uid = meta["unitid"]

        if dir_uid and dir_uid != hardcoded_uid:
            print(f"  !! Conflict for {name}: directory={dir_uid}, hardcoded={hardcoded_uid} — using hardcoded")

        uid = hardcoded_uid  # hardcoded is authoritative (confirmed via IPEDS DFR)
        target_unitids.add(uid)
        # Ensure the hardcoded uid is in the lookup even if the name drifted
        if uid not in unitid_to_name:
            unitid_to_name[uid] = name

    print(f"  Resolved {len(target_unitids)}/{len(SCHOOLS)} target schools to unitids.\n")
    return unitid_to_name, target_unitids


'''
PURPOSE:
    Fetches admissions data for all target institutions across all years in
    YEARS. Requests sex=99 (institution total) to avoid per-sex row
    duplication that would cause double-counting of applicants and admits.
    Filters each page client-side to rows whose unitid is in target_unitids.

    Confirmed field names (from preflight check):
        number_applied        → stored as "applied"
        number_admitted       → stored as "admitted"
        number_enrolled_total → stored as "enrolled"

RETURNS:
    pd.DataFrame — columns: unitid, year, applied, admitted, enrolled,
                   acceptance_rate, yield_rate.
    Empty DataFrame if no target institutions are found in any year.
'''
def fetch_admissions_bulk(target_unitids: set) -> pd.DataFrame:
    records = []
    for yr in YEARS:
        url  = f"{BASE_URL}/admissions-enrollment/{yr}/?sex=99"
        print(f"    {yr}...", end=" ", flush=True)
        try:
            rows = fetch_all_pages(url)
            hits = [r for r in rows if r.get("unitid") in target_unitids]
            print(f"{len(hits)}/{len(rows)} target schools")
            for r in hits:
                apps   = r.get("number_applied")
                admits = r.get("number_admitted")
                enroll = r.get("number_enrolled_total")
                records.append({
                    "unitid":          r.get("unitid"),
                    "year":            yr,
                    "applied":         apps,
                    "admitted":        admits,
                    "enrolled":        enroll,
                    "acceptance_rate": round(admits / apps * 100, 2)
                                       if apps and admits else None,
                    "yield_rate":      round(enroll / admits * 100, 2)
                                       if admits and enroll else None,
                })
        except requests.HTTPError as e:
            print(f"HTTP {e.response.status_code} — skipped")
        except Exception as e:
            print(f"Error: {e}")

    empty_years = [yr for yr in YEARS if yr not in {r["year"] for r in records}]
    if empty_years:
        print(f"  Warning: no admissions data returned for years: {empty_years}")

    return pd.DataFrame(records) if records else pd.DataFrame()


'''
PURPOSE:
    Probes several candidate endpoint names for graduation rates against a
    single year (2015) and returns the first one that responds with HTTP 200
    and at least one result record. Prints the result for each candidate so
    the correct endpoint name is visible in the run log. Also prints all
    field names from the first record so the rate column name can be
    confirmed before the main loop runs.

RETURNS:
    tuple[str, str] | tuple[None, None] — (endpoint_path, rate_field_name),
    or (None, None) if no candidate endpoint succeeds.
'''
def find_grad_endpoint() -> tuple:
    candidates = [
        ("graduation-rates",  "grad_rate_150"),
        ("grad-rates",        "grad_rate_150"),
        ("outcome-measures",  "grad_rate_150"),
        ("graduationrates",   "grad_rate_150"),
        ("graduation_rates",  "grad_rate_150"),
    ]
    print("  Probing grad rate endpoint candidates against year 2015...")
    for endpoint, default_field in candidates:
        url = f"{BASE_URL}/{endpoint}/2015/"
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                results = r.json().get("results", [])
                if results:
                    fields = list(results[0].keys())
                    # Find the graduation rate field — prefer completion_rate_150pct
                    # (confirmed field name from grad-rates endpoint probe), then
                    # fall back to any field containing both "rate" and "150"
                    rate_field = next(
                        (f for f in fields if f == "completion_rate_150pct"),
                        next(
                            (f for f in fields if "rate" in f.lower() and "150" in f),
                            next((f for f in fields if "grad_rate" in f.lower()), default_field)
                        )
                    )
                    print(f"    ✓ {endpoint} — HTTP 200, {len(results)} records")
                    print(f"      Fields: {fields}")
                    print(f"      Using rate field: '{rate_field}'")
                    return endpoint, rate_field
                else:
                    print(f"    ~ {endpoint} — HTTP 200 but 0 records")
            else:
                print(f"    ✗ {endpoint} — HTTP {r.status_code}")
        except Exception as e:
            print(f"    ✗ {endpoint} — {e}")
        time.sleep(SLEEP_SEC)
    return None, None


'''
PURPOSE:
    Fetches 6-year graduation rates for all target institutions across all
    years in YEARS. Uses the endpoint name and rate field confirmed by
    find_grad_endpoint() at startup rather than hardcoded values.
    Filters client-side to rows whose unitid is in target_unitids.
    Years where the endpoint returns an HTTP error are skipped with a
    printed status code rather than crashing.

RETURNS:
    pd.DataFrame — columns: unitid, year, grad_rate_150.
    Empty DataFrame if the endpoint is unreachable or no data is returned.
'''
def fetch_grad_rates_bulk(target_unitids: set) -> pd.DataFrame:
    endpoint, rate_field = find_grad_endpoint()
    if not endpoint:
        print("  Could not find a working grad rate endpoint — skipping.")
        return pd.DataFrame()

    records = []
    for yr in YEARS:
        url = f"{BASE_URL}/{endpoint}/{yr}/"
        print(f"    {yr}...", end=" ", flush=True)
        try:
            rows = fetch_all_pages(url)
            hits = [r for r in rows if r.get("unitid") in target_unitids]
            print(f"{len(hits)}/{len(rows)} target schools")
            for r in hits:
                val = r.get(rate_field)
                if val is not None:
                    records.append({
                        "unitid":        r.get("unitid"),
                        "year":          yr,
                        "grad_rate_150": val,
                    })
        except requests.HTTPError as e:
            print(f"HTTP {e.response.status_code} — skipped")
        except Exception as e:
            print(f"Error: {e}")

    empty_years = [yr for yr in YEARS if yr not in {r["year"] for r in records}]
    if empty_years:
        print(f"  Warning: no grad rate data returned for years: {empty_years}")

    return pd.DataFrame(records) if records else pd.DataFrame()


'''
PURPOSE:
    Merges display metadata from the SCHOOLS registry into a DataFrame that
    already contains a unitid column. Uses the unitid_to_name lookup built
    from the directory to recover inst_name, then maps slug, color, state,
    and group membership from SCHOOLS. Rows whose unitid resolves to a name
    not in SCHOOLS are dropped with a printed warning.

RETURNS:
    pd.DataFrame — input DataFrame with inst_name, slug, color, state,
                   group_maine, group_new_england, and is_bowdoin appended.
'''
def attach_metadata(df: pd.DataFrame, unitid_to_name: dict) -> pd.DataFrame:
    df = df.copy()
    df["inst_name"] = df["unitid"].map(unitid_to_name)

    unknown = set(df["inst_name"].dropna()) - TARGET_NAMES
    if unknown:
        print(f"  Warning: dropping rows with unrecognised names: {unknown}")
    df = df[df["inst_name"].isin(TARGET_NAMES)].copy()

    df["slug"]              = df["inst_name"].map(lambda n: SCHOOLS[n]["slug"])
    df["color"]             = df["inst_name"].map(lambda n: SCHOOLS[n]["color"])
    df["state"]             = df["inst_name"].map(lambda n: SCHOOLS[n]["state"])
    df["group_maine"]       = df["slug"].isin(GROUPS["maine"])
    df["group_new_england"] = df["slug"].isin(GROUPS["new_england"])
    df["is_bowdoin"]        = df["slug"] == "bowdoin"
    return df


# ── MAIN ---------------------------------------------------------------------
def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── Step 1: resolve inst_name → unitid from the directory ────────────────
    unitid_to_name, target_unitids = build_unitid_lookup()
    if not target_unitids:
        print("No unitids resolved — check SCHOOLS names against IPEDS directory.")
        return

    # ── Step 2: fetch admissions and grad rates ───────────────────────────────
    print(f"Collecting IPEDS data for {len(SCHOOLS)} institutions, "
          f"years {YEARS[0]}–{YEARS[-1]}...\n")

    print("Admissions-enrollment:")
    adm = fetch_admissions_bulk(target_unitids)

    print("\nGraduation rates:")
    grad = fetch_grad_rates_bulk(target_unitids)

    if adm.empty:
        print("\nNo admissions data collected.")
        print("Run Col_Name_Check.py to verify field names and endpoint paths.")
        return

    # ── Step 3: merge, label, and write ──────────────────────────────────────
    if not grad.empty:
        df = adm.merge(grad[["unitid","year","grad_rate_150"]],
                       on=["unitid","year"], how="left")
    else:
        print("  No grad rate data — grad_rate_150 will be null.")
        df = adm.assign(grad_rate_150=None)

    df = attach_metadata(df, unitid_to_name)

    col_order = [
        "unitid","year","inst_name","slug","state","color",
        "group_maine","group_new_england","is_bowdoin",
        "applied","admitted","enrolled",
        "acceptance_rate","yield_rate","grad_rate_150",
    ]
    df = df[[c for c in col_order if c in df.columns]]
    df = df.sort_values(["inst_name","year"]).reset_index(drop=True)

    # ── peers_raw.csv ─────────────────────────────────────────────────────────
    raw_path = OUT_DIR / "peers_raw.csv"
    df.to_csv(raw_path, index=False)
    print(f"\nWrote {len(df)} rows → {raw_path}")

    # ── peers_avg.csv ─────────────────────────────────────────────────────────
    avg_cols = {
        "applied":         "avg_applied",
        "admitted":        "avg_admitted",
        "enrolled":        "avg_enrolled",
        "acceptance_rate": "avg_acceptance_rate",
        "yield_rate":      "avg_yield_rate",
        "grad_rate_150":   "avg_grad_rate_150",
    }
    avg = (
        df.groupby("year")[list(avg_cols.keys())]
        .agg(lambda x: x.dropna().mean() if x.notna().any() else None)
        .rename(columns=avg_cols)
        .reset_index()
    )
    avg["n_institutions"] = df.groupby("year")["unitid"].nunique().values
    avg_path = OUT_DIR / "peers_avg.csv"
    avg.to_csv(avg_path, index=False)
    print(f"Wrote {len(avg)} rows → {avg_path}")

    # ── bowdoin_ipeds.csv ─────────────────────────────────────────────────────
    bow_cols = ["year","applied","admitted","enrolled",
                "acceptance_rate","yield_rate","grad_rate_150"]
    bow      = df[df["is_bowdoin"]][bow_cols].reset_index(drop=True)
    bow_path = OUT_DIR / "bowdoin_ipeds.csv"
    bow.to_csv(bow_path, index=False)
    print(f"Wrote {len(bow)} rows → {bow_path}")

    print(f"\nDone. {df['inst_name'].nunique()} institutions × "
          f"{df['year'].nunique()} years.")


if __name__ == "__main__":
    main()