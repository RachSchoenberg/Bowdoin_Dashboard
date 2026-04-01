'''
PURPOSE:
    Extracts key admissions and enrollment metrics from Bowdoin College's
    Common Data Set (CDS) PDF files spanning 2001–2026.

FLOW:
    1. Iterates over all PDF files in CDS_pdfs/
    2. Concatenates all page text from each PDF into a single string
    3. Parses the academic year from the document header
    4. Uses regex patterns to extract key metrics from Sections B, C, and H
    5. Derives calculated fields (acceptance rate, yield rate) from raw counts
    6. Skips PDFs where admit_rate == 100% as a bad-data guard (blank templates)
    7. Collects all years into a DataFrame, sorts by year, and saves to CSV

RETURNS:
    bowdoin_cds.csv — one row per academic year containing:
        year, source_file, apps_men, apps_women, total_apps,
        admits_men, admits_women, total_admits,
        enrolled_men, enrolled_women, total_enrolled,
        accept_rate, yield_rate, total_undergrad,
        retention_rate, grad_rate_6yr, ed_apps, ed_admits
'''

import pdfplumber
import pandas as pd
import re
import os

# ── CONFIG -------------------------------------------------------------------
PDF_DIR    = "./CDS_pdfs"       # folder containing all your CDS PDFs
OUTPUT_CSV = "bowdoin_cds.csv"
# ----------------------------------------------------------------------------


'''
PURPOSE:
    Extracts the starting academic year from the full text of a CDS PDF.
    Searches for a year-range pattern such as "2001-2002" or "2024–2025".
    Uses the filename as a fallback if the pattern is not found in the text,
    since some PDFs (e.g. 2005-2006) have inconsistent header formatting that
    causes the regex to grab the second year instead of the first.

RETURNS:
    int — the first (starting) year of the academic year range (e.g. 2001),
    or None if no match is found in either the text or filename.
'''
def extract_year(text, filename=""):
    # Try filename first — most reliable since you named them consistently
    m = re.search(r'(20\d{2})-20\d{2}', filename)
    if m:
        return int(m.group(1))
    # Fall back to PDF text content
    m = re.search(r'(19|20)(\d{2})[\-–](19|20)\d{2}', text)
    if m:
        return int(m.group(1) + m.group(2))
    return None


'''
PURPOSE:
    Searches the PDF text for an integer value using one or more regex patterns.
    Tries each pattern in order and returns the first successful integer match.
    Commas in numbers (e.g. "4,536") are handled automatically.

RETURNS:
    int — the first matched numeric value,
    or None if no pattern produces a match.
'''
def find_number(text, *patterns):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1).replace(",", "").strip())
            except (ValueError, IndexError):
                pass
    return None


'''
PURPOSE:
    Searches the PDF text for a float value using one or more regex patterns.
    Behaves identically to find_number() but returns a float instead of an int.
    Used for rates and percentages such as acceptance rate or retention rate.

RETURNS:
    float — the first matched numeric value,
    or None if no pattern produces a match.
'''
def find_float(text, *patterns):
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "").strip())
            except (ValueError, IndexError):
                pass
    return None


'''
PURPOSE:
    Orchestrates the full extraction pipeline for a single CDS PDF file.
    Opens the PDF, concatenates all page text, then calls extract_year(),
    find_number(), and find_float() to pull metrics from Sections B, C, and H.
    Derives acceptance rate and yield rate from raw applicant counts.
    Passes the filename into extract_year() so year parsing uses the
    filename as the primary source, avoiding header-parsing ambiguity.

RETURNS:
    dict — one key-value pair per metric for the given academic year:
        year, source_file, apps_men, apps_women, total_apps,
        admits_men, admits_women, total_admits,
        enrolled_men, enrolled_women, total_enrolled,
        accept_rate, yield_rate, total_undergrad,
        retention_rate, grad_rate_6yr, ed_apps, ed_admits
'''
def parse_cds_pdf(path):
    fname = os.path.basename(path)

    with pdfplumber.open(path) as pdf:
        full_text = "\n".join(p.extract_text() or "" for p in pdf.pages)

    year = extract_year(full_text, filename=fname)

    # Applications, Admits, Enrolled (C1) ----------------------------------------
    apps_men   = find_number(full_text,
        r'first-year.*?men who applied[^\d]*([\d,]+)',
        r'men who applied\s+([\d,]+)')
    apps_women = find_number(full_text,
        r'first-year.*?women who applied[^\d]*([\d,]+)',
        r'women who applied\s+([\d,]+)')

    adm_men    = find_number(full_text,
        r'men who were admitted[^\d]*([\d,]+)')
    adm_women  = find_number(full_text,
        r'women who were admitted[^\d]*([\d,]+)')

    enr_men    = find_number(full_text,
        r'full-time.*?men who enrolled[^\d]*([\d,]+)')
    enr_women  = find_number(full_text,
        r'full-time.*?women who enrolled[^\d]*([\d,]+)')

    # Derived Metrics ------------------------------------------------------------
    total_apps     = (apps_men   or 0) + (apps_women   or 0) or None
    total_admits   = (adm_men    or 0) + (adm_women    or 0) or None
    total_enrolled = (enr_men    or 0) + (enr_women    or 0) or None

    accept_rate = round(total_admits / total_apps * 100, 1) \
        if total_admits and total_apps else None
    yield_rate  = round(total_enrolled / total_admits * 100, 1) \
        if total_enrolled and total_admits else None

    # Total Undergrad Enrollment (B1) --------------------------------------------
    total_undergrad = find_number(full_text,
        r'total all undergraduates[^\d]*([\d,]+)',
        r'grand total all students[^\d]*([\d,]+)')

    # Retention Rate (B22) -------------------------------------------------------
    # Old patterns matched the "Retention Rates" section header and then
    # crawled forward to the first %, which was the SAT submission rate (67%),
    # not the B22 value. Fix: anchor to B22 label and find the blank field.
    # (?s) enables DOTALL so .*? crosses newlines (B22 question spans 3 lines).
    retention = find_float(full_text,
        r'(?s)B22[.\s].*?_{2,}\s*([\d.]+)\s*_{0,}\s*%')

    # 6 Year Grad Rate (B11) -----------------------------------------------------
    # Old patterns matched "Six-year graduation rate for 1995 cohort" and
    # captured "1995" (the cohort year), not the rate. Fix: anchor to B11 label
    # and skip past the colon to the blank field value.
    # (?s) enables DOTALL in case B11 line wraps across lines in some PDFs.
    grad_rate_6yr = find_float(full_text,
        r'(?s)B11[.\s].*?:\s*_{2,}\s*([\d.]+)')

    # Early Decision (C21) -------------------------------------------------------
    ed_apps = find_number(full_text,
        r'early decision applications received.*?([\d,]+)')
    ed_admits = find_number(full_text,
        r'admitted under early decision.*?([\d,]+)')

    return {
        "year":            year,
        "source_file":     fname,
        "apps_men":        apps_men,
        "apps_women":      apps_women,
        "total_apps":      total_apps,
        "admits_men":      adm_men,
        "admits_women":    adm_women,
        "total_admits":    total_admits,
        "enrolled_men":    enr_men,
        "enrolled_women":  enr_women,
        "total_enrolled":  total_enrolled,
        "accept_rate":     accept_rate,
        "yield_rate":      yield_rate,
        "total_undergrad": total_undergrad,
        "retention_rate":  retention,
        "grad_rate_6yr":   grad_rate_6yr,
        "ed_apps":         ed_apps,
        "ed_admits":       ed_admits,
    }


# ── MAIN --------------------------------------------------------------------
rows = []
skipped = []

for fname in sorted(os.listdir(PDF_DIR)):
    if not fname.lower().endswith(".pdf"):
        continue
    fpath = os.path.join(PDF_DIR, fname)
    print(f"Processing: {fname}")
    try:
        row = parse_cds_pdf(fpath)

        # Bad-data guard: skip blank/unfilled template PDFs.
        # Two failure modes trigger this:
        #   1. accept_rate == 100% -- usually means admits parsed but apps did
        #      not, so the derived rate is meaningless.
        #   2. apps_men == apps_women and both are year-shaped integers -- the
        #      C1 fields are empty and the pattern captured the academic year
        #      (e.g. 2024) from nearby B1 text, producing an identical spurious
        #      value for both sexes (e.g. 2024 + 2024 = 4048 total apps).
        apps_m = row.get("apps_men")
        apps_w = row.get("apps_women")
        spurious_year_capture = (
            apps_m is not None
            and apps_w is not None
            and apps_m == apps_w
            and apps_m > 1990
        )
        if row.get("accept_rate") == 100.0 or spurious_year_capture:
            print(f"  Skipped -- blank or unparseable template "
                  f"(accept_rate={row.get('accept_rate')}%, "
                  f"apps_men={apps_m}, apps_women={apps_w})")
            skipped.append(fname)
            continue

        rows.append(row)
        print(f"  → year={row['year']}, apps={row['total_apps']}, "
              f"admit_rate={row['accept_rate']}%, yield={row['yield_rate']}%")
    except Exception as e:
        print(f"  ✗ Error: {e}")

df = pd.DataFrame(rows).sort_values("year").reset_index(drop=True)
df.to_csv(OUTPUT_CSV, index=False)

print(f"\nSaved {len(df)} rows → {OUTPUT_CSV}")
if skipped:
    print(f"Skipped {len(skipped)} blank template(s): {skipped}")
print(df[["year", "source_file", "total_apps",
          "accept_rate", "yield_rate", "total_enrolled"]].to_string())