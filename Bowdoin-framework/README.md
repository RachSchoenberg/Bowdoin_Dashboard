# LAC Admissions Intelligence Dashboard

A 25-year interactive comparison of liberal arts college admissions data - built with [Observable Framework](https://observablehq.com/framework/) for the Bowdoin College Director of Admissions Operations role.

**Schools covered:** Bowdoin · Bates · Colby · Williams · Amherst · Middlebury  
**Metrics:** Acceptance rate trends · Application volume · Yield rate · Estimated enrollment

---

## Quick Start

```bash
npm install
npm run dev
```

Then open [http://localhost:3000](http://localhost:3000).

---

## Deploy to GitHub Pages

### One-time setup
1. Push this repo to GitHub
2. Go to **Settings → Pages**
3. Set Source to **GitHub Actions**
4. In `observablehq.config.js`, uncomment and set `base` to your repo name:
   ```js
   base: "/your-repo-name/",
   ```
5. Push to `main` - GitHub Actions will build and deploy automatically

Your dashboard will be live at: `https://your-username.github.io/your-repo-name/`

---

## Updating the Data

All data lives in `src/data/`. The CSVs are pre-populated with best-available estimates from IPEDS and Common Data Sets. **Before presenting, verify against official sources:**

| File | Source | Update frequency |
|------|--------|-----------------|
| `acceptance_rates.csv` | CDS Section C or IPEDS | Annual |
| `applications.csv` | CDS Section C or IPEDS | Annual |
| `yield_rates.csv` | CDS Section C or IPEDS | Annual |

### Where to get verified data
- **IPEDS Data Center:** [nces.ed.gov/ipeds](https://nces.ed.gov/ipeds/datacenter) - download "Admissions and Test Scores" survey
- **Common Data Sets:** Search `"[School Name] Common Data Set [year]"` - each school publishes PDFs annually
- **Bowdoin:** [bowdoin.edu/institutional-research](https://www.bowdoin.edu/institutional-research/)

### Adding a school
1. Add a key to `SCHOOLS`, `NAMES`, and `COLORS` in each page
2. Add the corresponding column to each CSV
3. Pick a distinct hex color

---

## Pages

| Page | Path | What it shows |
|------|------|---------------|
| Overview | `/` | Acceptance rate trends + 2024 snapshot cards |
| Selectivity & Demand | `/selectivity` | Application volume growth + The Colby Effect |
| Yield & Enrollment | `/yield` | Yield rate trends + Yield vs. selectivity scatter |

---

## Tech Stack

- [Observable Framework](https://observablehq.com/framework/) - reactive Markdown + JavaScript
- [Observable Plot](https://observablehq.com/plot/) - charting library (bundled)
- GitHub Actions + GitHub Pages - zero-cost hosting

---

*Data disclaimer: Values are estimates compiled from publicly available IPEDS data and Common Data Sets. They are intended for illustrative and analytical purposes. Verify with official institutional records before using in formal reporting.*
