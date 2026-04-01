'''
Fetch_peers.py
==============
Fetches enriched peer data from the Urban Institute IPEDS API:
  • Ethnicity   — enrolled undergrads by race/ethnicity
  • Geography   — in-state / out-of-state / international
  • Degrees     — bachelor's degrees conferred by broad CIP field

Fixes applied vs. original:
  FIX 1: Corrected unitids (verified against IPEDS lookup)
  FIX 2: inst_name matching uses unitid lookup instead of string match
          so peers_raw.csv name variations don't break the join
  FIX 3: Year range derived from peers_raw.csv automatically
  FIX 4: Geography pulled from same endpoint as ethnicity (level_of_study=1,
          sex=99) — avoids slow unfiltered second call that often returns nothing
  FIX 5: Working directory forced to project root so script runs from anywhere

Usage
-----
  python src/data/Fetch_peers.py            # fetch all schools + years
  python src/data/Fetch_peers.py --test     # Bowdoin 2019 only
  python src/data/Fetch_peers.py --resume   # skip already-written rows
'''

import argparse, csv, os, sys, time
from collections import defaultdict
from pathlib import Path

# ── Force working directory to project root (parent of src/) ─────────────────
os.chdir(Path(__file__).parent.parent.parent)

try:
    import requests
    import pandas as pd
except ImportError:
    sys.exit("Run:  pip install requests pandas")

# ── Paths & constants ─────────────────────────────────────────────────────────
BASE_URL = "https://educationdata.urban.org/api/v1/college-university/ipeds"
INPUT    = Path("src/data/peers_raw_2.csv")
OUTPUT   = Path("src/data/peers_enriched_retention.csv")

SLEEP    = 0.5
TIMEOUT  = 120
RETRIES  = 3

# FIX 1: Verified unitids from IPEDS College Navigator
SCHOOLS = {
    "Amherst College":               164465,
    "Barnard College":               189097,
    "Bates College":                 160977,
    "Bowdoin College":               161226,   # was 161004 (wrong)
    "Carleton College":              173258,
    "Claremont McKenna College":     112260,
    "Colby College":                 161217,   # was 161086 (wrong)
    "Davidson College":              198385,
    "Grinnell College":              153384,
    "Hamilton College":              191515,
    "Harvey Mudd College":           115409,
    "Middlebury College":            230959,
    "Pomona College":                121345,
    "Smith College":                 167835,
    "Swarthmore College":            216287,
    "Vassar College":                197133,
    "Washington and Lee University": 234207,
    "Wellesley College":             168218,
    "Wesleyan University":           130697,
    "Williams College":              168342,
}

# FIX 2: Reverse lookup unitid → canonical name so we can join on unitid
#         instead of fragile string matching against peers_raw inst_name
UNITID_TO_NAME = {v: k for k, v in SCHOOLS.items()}

RACE_COLS = {
    1: "enroll_nonresident",
    2: "enroll_hispanic",
    3: "enroll_aian",
    4: "enroll_asian",
    5: "enroll_black",
    6: "enroll_nhpi",
    7: "enroll_white",
    8: "enroll_two_or_more",
    9: "enroll_unknown",
}

CIP_TO_COL = {
    "03": "deg_pct_natural_resources",
    "05": "deg_pct_area_ethnic_studies",
    "11": "deg_pct_computer_info_sciences",
    "13": "deg_diploma_pct_education",
    "16": "deg_pct_foreign_languages",
    "23": "deg_pct_english",
    "26": "deg_pct_biological_life_sciences",
    "27": "deg_pct_mathematics",
    "30": "deg_pct_interdisciplinary",
    "38": "deg_pct_philosophy_religion",
    "40": "deg_pct_physical_sciences",
    "42": "deg_pct_psychology",
    "45": "deg_pct_social_sciences",
    "50": "deg_pct_visual_performing_arts",
    "54": "deg_pct_history",
}
DEG_PCT_COLS = sorted(set(CIP_TO_COL.values()))

BASE_COLS = ["unitid","year","inst_name","applied","admitted","enrolled",
             "est_fte","grad_rate_150","acceptance_rate","yield_rate","is_bowdoin"]
ETH_COLS  = list(RACE_COLS.values())
GEO_COLS  = ["enroll_instate","enroll_outofstate","enroll_intl"]
RET_COLS  = ["retention_rate_full_time", "retention_rate_part_time"]
ALL_COLS  = BASE_COLS + ETH_COLS + GEO_COLS + RET_COLS + DEG_PCT_COLS + ["deg_total_graduates"]


# ── HTTP helper ───────────────────────────────────────────────────────────────

def fetch_all_pages(url, params=None):
    rows = []
    if params:
        param_str = "&".join(f"{k}={v}" for k, v in params.items())
        current_url = f"{url}?{param_str}"
    else:
        current_url = url

    while current_url:
        for attempt in range(1, RETRIES + 1):
            try:
                resp = requests.get(current_url, timeout=TIMEOUT)
                if resp.status_code == 404:
                    return rows
                if resp.status_code != 200:
                    print(f"\n    ⚠  HTTP {resp.status_code} — skipping")
                    return rows
                data        = resp.json()
                rows       += data.get("results", [])
                current_url = data.get("next")
                time.sleep(SLEEP)
                break
            except requests.exceptions.ReadTimeout:
                wait = attempt * 10
                print(f"\n    ⏱ Timeout (attempt {attempt}/{RETRIES}) — retrying in {wait}s…")
                time.sleep(wait)
            except Exception as e:
                if attempt == RETRIES:
                    print(f"\n    ⚠  {e} — skipping")
                    return rows
                time.sleep(attempt * 3)
        else:
            return rows
    return rows


# ── Fetchers ──────────────────────────────────────────────────────────────────

def fetch_ethnicity_and_geography(unitid: int, year: int) -> dict:
    '''
    FIX 4: Pulls ethnicity AND geography in a single API call.
    level_of_study=1 (undergrad), sex=99 (all) returns one row per race code.
    efres01/02/03 residence fields appear on these same rows.
    '''
    url  = f"{BASE_URL}/fall-enrollment/{year}/"
    rows = fetch_all_pages(url, {
        "unitid":         unitid,
        "level_of_study": 1,
        "sex":            99,
    })

    out = {col: None for col in RACE_COLS.values()}
    out.update({"enroll_instate": None, "enroll_outofstate": None, "enroll_intl": None})

    geo_found = False
    for row in rows:
        # Ethnicity
        code = int(row.get("race") or 0)
        if code in RACE_COLS:
            val = row.get("ftftp01")
            if val in (None, ""):
                val = row.get("efytotlt")
            if val not in (None, ""):
                out[RACE_COLS[code]] = int(float(val))

        # Geography — grab from first row that has it
        if not geo_found and row.get("efres01") not in (None, ""):
            out["enroll_instate"]    = int(float(row["efres01"]))
            out["enroll_outofstate"] = int(float(row.get("efres02") or 0))
            out["enroll_intl"]       = int(float(row.get("efres03") or 0))
            geo_found = True

    return out


def fetch_retention(unitid: int, year: int) -> dict:
    '''
    IPEDS EFD — First-to-second-year retention rate.
    Endpoint: /retention-rates/{year}/
    Fields:
      ret_pcf  = full-time cohort retention rate (pct, 0–100)
      ret_pcp  = part-time cohort retention rate (pct, 0–100)
    Returns None if not reported (small schools sometimes skip part-time).
    '''
    url  = f"{BASE_URL}/retention-rates/{year}/"
    rows = fetch_all_pages(url, {"unitid": unitid})

    out = {"retention_rate_full_time": None, "retention_rate_part_time": None}
    for row in rows:
        if row.get("ret_pcf") not in (None, ""):
            out["retention_rate_full_time"] = float(row["ret_pcf"])
        if row.get("ret_pcp") not in (None, ""):
            out["retention_rate_part_time"] = float(row["ret_pcp"])
        break   # only one row per school/year
    return out


def fetch_degrees(unitid: int, year: int) -> dict:
    url  = f"{BASE_URL}/completions/{year}/"
    rows = fetch_all_pages(url, {
        "unitid":      unitid,
        "award_level": 5,
    })

    total, cip_counts = 0, defaultdict(int)
    for row in rows:
        cip6  = str(row.get("cipcode") or "").zfill(6)
        cip2  = cip6[:2]
        count = int(float(row.get("ctotalt") or 0))
        total += count
        cip_counts[cip2] += count

    out = {col: None for col in DEG_PCT_COLS}
    out["deg_total_graduates"] = total if total > 0 else None
    if total > 0:
        for cip2, col in CIP_TO_COL.items():
            pct = round(cip_counts.get(cip2, 0) / total * 100, 2)
            out[col] = pct
    return out


# ── I/O helpers ───────────────────────────────────────────────────────────────

def load_base() -> tuple[dict, list]:
    '''
    FIX 2+3: Join on unitid instead of inst_name string.
    Also derives the year range automatically from peers_raw.csv.
    Returns (data_dict keyed by (unitid, year), sorted list of years).
    '''
    if not INPUT.exists():
        sys.exit(f"Cannot find {INPUT}. Run from your project root "
                 f"(the folder containing src/).")

    data  = {}
    years = set()
    valid_unitids = set(SCHOOLS.values())

    with open(INPUT) as f:
        for r in csv.DictReader(f):
            uid = int(r.get("unitid") or 0)
            yr  = int(r["year"])
            if uid in valid_unitids:
                data[(uid, yr)] = dict(r)
                years.add(yr)

    if not years:
        # peers_raw.csv may not have unitid — fall back to name matching
        print("  ⚠  No unitid column found in peers_raw.csv — falling back to name match")
        name_to_uid = {v: k for k, v in UNITID_TO_NAME.items()}  # name→unitid
        with open(INPUT) as f:
            for r in csv.DictReader(f):
                name = r.get("inst_name", "")
                yr   = int(r["year"])
                uid  = SCHOOLS.get(name)
                if uid:
                    data[(uid, yr)] = dict(r)
                    years.add(yr)

    return data, sorted(years)


def already_done() -> set:
    done = set()
    if OUTPUT.exists():
        with open(OUTPUT) as f:
            for r in csv.DictReader(f):
                if r.get("enroll_white") not in (None, ""):
                    done.add((int(r.get("unitid") or 0), int(r["year"])))
    return done

def write_row(writer, f, row: dict):
    writer.writerow({col: row.get(col, "") for col in ALL_COLS})
    f.flush()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--test",   action="store_true",
                        help="Bowdoin 2019 only — quick smoke test")
    parser.add_argument("--resume", action="store_true",
                        help="Skip rows already written to output")
    args = parser.parse_args()

    print("=" * 60)
    print("Fetch_peers.py")
    print("=" * 60)

    base_data, all_years = load_base()
    done = already_done() if args.resume else set()

    # FIX 3: year range comes from peers_raw.csv, not hardcoded
    schools = {"Bowdoin College": 161226} if args.test else SCHOOLS
    years   = [2019]                       if args.test else all_years

    if args.test:
        print(f"TEST MODE — Bowdoin 2019 only\n")
    else:
        print(f"Schools: {len(schools)}   Years: {min(years)}–{max(years)}\n")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume and OUTPUT.exists() else "w"

    with open(OUTPUT, mode, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=ALL_COLS, extrasaction="ignore")
        if mode == "w":
            writer.writeheader()

        for name, unitid in schools.items():
            print(f"\n{'='*55}")
            print(f"  {name}  (unitid={unitid})")
            print(f"{'='*55}")

            for year in years:
                key = (unitid, year)
                if key in done:
                    print(f"  {year}: already done — skipping")
                    continue

                # Seed from peers_raw row if available, else build minimal row
                row = dict(base_data.get(key, {
                    "unitid":     unitid,
                    "year":       year,
                    "inst_name":  name,
                    "is_bowdoin": str(name == "Bowdoin College"),
                }))
                row["unitid"]    = unitid
                row["inst_name"] = name   # use canonical name

                print(f"  {year}:", end="  ", flush=True)

                print("ethnicity+geography…", end=" ", flush=True)
                row.update(fetch_ethnicity_and_geography(unitid, year))

                print("retention…", end=" ", flush=True)
                row.update(fetch_retention(unitid, year))

                print("degrees…", end=" ", flush=True)
                row.update(fetch_degrees(unitid, year))

                print("✓")
                write_row(writer, f, row)

    if args.test:
        print("\n--- TEST OUTPUT ---")
        with open(OUTPUT) as f:
            for r in csv.DictReader(f):
                print(f"\nSchool : {r['inst_name']}  Year: {r['year']}")
                print("  Ethnicity:")
                for col in ETH_COLS:
                    print(f"    {col}: {r.get(col, '—')}")
                print("  Geography:")
                for col in GEO_COLS:
                    print(f"    {col}: {r.get(col, '—')}")
                print("  Retention:")
                for col in RET_COLS:
                    print(f"    {col}: {r.get(col, '—')}")
                print("  Degrees:")
                print(f"    deg_total_graduates:         {r.get('deg_total_graduates','—')}")
                print(f"    deg_pct_social_sciences:     {r.get('deg_pct_social_sciences','—')}")
                print(f"    deg_pct_biological_...:      {r.get('deg_pct_biological_life_sciences','—')}")
    else:
        print(f"\n✅  Done → {OUTPUT}")
        print(f"\nNew columns added:")
        print(f"  Ethnicity ({len(ETH_COLS)}): {', '.join(ETH_COLS)}")
        print(f"  Geography ({len(GEO_COLS)}): {', '.join(GEO_COLS)}")
        print(f"  Degrees   ({len(DEG_PCT_COLS)+1}): deg_total_graduates + {len(DEG_PCT_COLS)} pct fields")


if __name__ == "__main__":
    main()