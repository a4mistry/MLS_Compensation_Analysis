# The Price of a Point — MLS 2026 Compensation

An interactive data narrative on Major League Soccer 2026 player pay and how it
translates into on-field results. Built from the MLSPA Spring 2026 Salary Guide.

**Live site:** https://a4mistry.github.io/MLS_Compensation_Analysis/

## What's here

```
├── main.py            # runs the full pipeline: python main.py
├── code/              # analysis scripts
│   ├── extract_salaries.py   # PDF  -> data/mls_salaries_2026.csv
│   ├── analysis.py           # league-wide pay analysis + charts
│   ├── efficiency.py         # payroll vs results (cost/point, value residual)
│   └── export_web_data.py    # -> web/site_data.js (feeds the website)
├── data/              # source PDF, CSVs, generated charts
└── web/               # the static website (deployed to GitHub Pages)
    ├── index.html
    ├── styles.css
    ├── app.js
    └── site_data.js   # generated analysis data (committed so Pages is static)
```

## Reproduce the analysis

```bash
python -m pip install pdfplumber pandas numpy scipy matplotlib seaborn
python main.py          # regenerates CSVs, charts, and web/site_data.js
```

Then open `web/index.html` locally, or push to GitHub to update the live site.

## How the site is deployed

`.github/workflows/deploy.yml` publishes the `web/` folder to GitHub Pages on
every push to `main` (via GitHub Actions). No build step runs in CI — the site
is fully static and `web/site_data.js` is committed.

## Data & caveats

- Pay = **guaranteed compensation** (base + marketing/bonus), the MLSPA snapshot
  dated April 14, 2026.
- Standings are mid-season 2026 (~13–15 of 34 games); results will shift.
- Guaranteed comp is not the same as MLS salary-cap/roster-rules spending.
