# AI Council Review — MLS 2026 Compensation Analysis

**Date:** July 15, 2026
**Scope:** numbers & data integrity · statistical methodology · code & pipeline · website content & UX
**Method:** 5 specialist review agents worked in parallel, each recomputing numbers independently from the raw CSVs (not trusting the pipeline code). Every finding was then handed to an adversarial verifier instructed to refute it. 43 agents ran in total. 25 findings were confirmed adversarially; 13 verifier agents were cut off by a session rate limit, and those findings were subsequently confirmed by direct code inspection. **0 findings were refuted.**

---

## Executive summary

The project's **data layer is in excellent shape**: every value in `web/site_data.js` — league totals, Gini, club payrolls, the regression, position medians, and all four derived blocks (roster/gap/goals/middle) — reproduces *exactly* from the raw CSVs under independent recomputation. The CSVs are internally consistent (`pts = 3w+d`, `w+l+d = gp`) and the standings show zero drift against the site.

The problems are concentrated in two places:

1. **Hardcoded prose.** One rank is flatly wrong (Atlanta has the **3rd**-largest payroll, not "5th"), one ratio is off ("a quarter" should be ~a fifth), and a family of standings-derived numbers is written into static HTML even though the pipeline re-fetches standings live — so accurate-today copy will silently go stale.
2. **Statistical overreach in the narrative.** The site converts fragile n=30 correlations into settled "verdicts" — several built on non-significant p-values — and ~15 correlations from the same sample carry auto-"significant" labels with no multiple-comparison control.

Nothing found threatens the core storyline (money buys little; Atlanta is inefficient; attack spend buys goals), but the copy asserts more certainty than the data supports.

---

## What checks out (verified clean)

- **All of `site_data.js`** matches independent recomputation exactly: 911 players, $624,722,690 payroll, mean $685,755 / median $350,000, Gini 0.6045, top-10% share 48.7%, the regression (slope 1.33124, intercept −8.31781, r 0.38737, R² 0.15005, p 0.03444), all 30 clubs' figures, position medians, top-earner list, and the roster/gap/goals/middle blocks.
- **README claims, the live GitHub Pages URL, the Unsplash photo credit** (qCrKTET_09o is indeed Vienna Reyes's stadium photo), hero stats, "half a billion", and the "Messi out-earns entire rosters" claim all verify.
- The duplicated regressions (`efficiency.py` vs `export_web_data.py`) currently agree to 6 decimals; the Gini implementation was validated against a mean-absolute-difference reference.
- **A correction to an earlier belief:** the feared PDF accent-mangling *does not exist in the data*. The CSV holds proper accented names ("Almirón", "Müller"); 0 replacement characters were found. The mangling seen during development was console display encoding only.

---

## Findings

### 🔴 Critical

**C1 — Atlanta United's payroll rank is wrong: "5th-largest" should be "3rd-largest"** (`web/index.html:199`)
Found independently by 4 of the 5 reviewers. Recomputed from the salary CSV (and confirmed against the site's own `site_data.js`): 1. Inter Miami $54.6M · 2. LAFC $32.6M · **3. Atlanta United $27.88M** · 4. LA Galaxy $26.4M · 5. Vancouver $24.6M. Payroll comes from the static April salary guide, so this was wrong at write time — not standings drift. Atlanta is 3rd by base salary too, so no alternative metric rescues it. The `$27.9M` figure itself is correct, and the app.js-wired pull quote ("a top-five payroll") is fine. **Fix: one word — or better, data-bind the rank.**

### 🟠 Major

**M1 — Verdicts assert conclusions from non-significant correlations** (`web/index.html` sections 07/09, roster section)
Three instances:
- §07 "The twist": treats r = −0.32 at **p = 0.087** as an established negative relationship, then converts a failure-to-reject into a proven null ("doesn't buy points"). 95% CI ≈ [−0.61, +0.05].
- §09 "Verdict: the stars edge it": the r = 0.32 vs r = 0.19 difference has **Steiger p ≈ 0.55** — far inside noise — and neither correlation is individually significant at n=30.
- The goalkeeper-top-earner story states a causal mechanism ("not because keepers lose games, but because…") generalized from **n = 2 clubs** (the stat card does disclose "2/30", to its credit), and the supporting t-test in `experiments/` compares n=27 vs n=3.

**M2 — ~15 correlations from the same 30 clubs, auto-"significant" labels, none survive multiplicity correction** (`web/app.js` `corrTxt`)
The site displays roughly 15 Pearson r values all computed on the same n=30 sample; `corrTxt` appends ", significant" whenever p < 0.05. Under Benjamini-Hochberg across the family, the minimum adjusted p is **0.172 — nothing survives**. (Side finding: `payrollGdR` is exported to `site_data.js` but never referenced anywhere — dead data.)

**M3 — The "Roster floor" tier is a near-constant variable** (`code/export_web_data.py`, §09 chart)
28 of 30 clubs have an identical floor ($88,025, the league minimum); only CF Montreal ($91,120) and NYRB ($99,925) differ. Every "Roster floor" correlation bar — including the eye-catching +0.23 vs goals conceded — is driven entirely by those two clubs. The bars are statistically meaningless and should be dropped or annotated.

**M4 — Hardcoded season-progress and standings-derived copy vs a live-refresh pipeline** (`web/index.html`, multiple)
`main.py` re-fetches standings from ESPN each run, but these are static prose: Atlanta's "66%", "12 points above the league's 54%", "60% of the wage bill", "2%"/"6%" GK shares, "0.79 PPG bottom-three side", the footer's "~13–15 of 34 games", "mid-season" (×3 including line 311's "half-season table"). All accurate today; the first re-run after more games will silently falsify them. Also: the site shows a salary "as of" date but **no standings as-of date** anywhere.

**M5 — "The cheapest points cost a quarter of what the priciest ones do" — actual ratio is ~a fifth** (`web/index.html:123`)
San Jose $494,540/pt vs Atlanta $2,534,912/pt → ratio **0.195** (a 5.1× spread). "A quarter" understates the very gap the section is about. (One verifier rated this minor since it's qualitative narrative over drifting data; another major. Either way it's a one-word fix — or compute the phrase from data.)

**M6 — No guard for pts = 0 / gp = 0** (`code/export_web_data.py:82`, `code/efficiency.py:39`)
`cost_per_point = payroll / pts` has no zero guard. A 0-point club (routine in the first 2–3 rounds of a season) yields `inf`; `json.dump` then writes a bare `Infinity` token into `site_data.js` (invalid JSON; and in the browser, `usd(Infinity)` renders "$∞" at the top of the Worst-value list). `gp = 0` produces NaN PPG. Verified: `json.dumps({'x': float('inf')})` → `{"x": Infinity}`.

**M7 — `fetch_standings.py` season drifts with the wall clock while filenames and labels are frozen at 2026**
`SEASON = datetime.now().year` but `OUT = standings_2026.csv`, and everything downstream (titles, site copy, `efficiency_2026.csv`) assumes 2026. Run during the 2027 season, it would silently join 2027 standings to 2026 salaries — a plausible-looking but wrong analysis. Also: conference parsing defaults any non-"East" child to "West".

**M8 — Analysis logic triplicated with divergent fallbacks**
`pos_bucket` defaults unknown positions to **"Midfield"** in `export_web_data.py` but **"Other"** in `experiments/positions_and_pay.py` (verified). All 14 current position strings match a rule, so nothing is misbucketed today — but a new label (e.g. "Sweeper") would be silently mis-assigned on the site and dropped in experiments. `gini()` is defined 3×; the payroll regression is computed twice (currently in agreement).

### 🟡 Minor

| # | Finding | Where |
|---|---|---|
| m1 | §09 middle-class scatter draws a **linear** trend line but quotes the **log-scale** r (+0.19) — the number doesn't describe the line shown | `web/app.js` |
| m2 | Goals correlations and goals-per-$10M use **raw GF/GA totals across unequal games played** (13–15 gp), penalizing 13-game clubs | `export_web_data.py` |
| m3 | Truncated position string **"Center Forward/Attacking Midfi"** (Müller) surfaces in tooltips and excludes hybrids from position medians | `data/mls_salaries_2026.csv` |
| m4 | `giniByClub` conference uses the hardcoded EAST fallback set even though the standings file now provides `conf` (currently identical) | `export_web_data.py` |
| m5 | Partial-correlation p-value uses n−2 df instead of n−3 (negligible here, technically wrong) | `export_web_data.py` |
| m6 | Goals-per-$10M ranking is denominator-driven — Spearman 0.80 with *inverse attack pay*; it mostly re-ranks payroll | §08 chart |
| m7 | Hero "payroll explains 15% of results" is an in-sample R² whose 95% CI spans ~0%–40% | hero copy |
| m8 | "Bottom quartile mirrors the league in every position except one" — Midfield (0.87×) also deviates | §06 copy |
| m9 | Stat card labels $1.33M (90th-percentile pay) as "**the DP threshold**" — contradicting the footer's own caveat that guaranteed comp ≠ roster-rules figures | §01 stat card |
| m10 | §03 lead overstates "wingers command the highest median pay" — Right Wing ranks 4th, below Defensive Midfield | §03 copy |
| m11 | Accessibility: `.tag` text contrast 3.1:1 fails WCAG AA; charts/key numbers have no non-visual alternative | `styles.css` |
| m12 | §04 payroll-vs-PPG scatter labels **all 30 clubs** at 10px (guaranteed overlap in the $21M cluster) — inconsistent with the outlier-only labeling used in §08 | `web/app.js` |
| m13 | Legend swatches don't match the multicolor bar series on the min-wage and Atlanta grouped charts (per-bar colors; legend shows a default swatch) | `web/app.js` |
| m14 | Copy/robustness polish: "Defence" (1×) vs "Defense" buckets; `usdShort(999999)` → "$1000K", `usdShort(<500)` → "$0K"; `extract_salaries` drops rows silently; console says "charts/" but files go to `data/charts/`; duplicated JS helpers with inconsistent null-guards | various |

---

## Improvement ideas (deduplicated & prioritized)

**1. Data-bind every narrative number.** *(Unanimous across all five reviewers — the single highest-leverage change.)* Compute payroll rank, cost-per-point spread, position shares, season-progress ("X of 34 games"), and the Atlanta paragraph in `export_web_data.py` and inject via `<span id>` like the rest of the site. This fixes C1/M4/M5 permanently instead of one word at a time, and adds a standings "as of" date to the footer.

**2. A statistical-honesty pass.** Report confidence intervals alongside (or instead of) "significant" flags; declare the family of tests and apply Benjamini-Hochberg; run a Steiger test before crowning stars-vs-depth; drop or annotate the roster-floor tier; soften deterministic copy ("law", "verdict", "really does buy", "the exceptions prove the point"). Check Inter Miami's leverage on the headline regression (one club far right on a log axis).

**3. Per-game normalization.** Use `gf/gp` and `ga/gp` in the goals and stars-vs-middle blocks, and consider per-game goals-per-$10M — clubs differ by 2 games of exposure.

**4. Pipeline robustness.** Guard zero-point/zero-game clubs; make `fetch_standings.py` season-aware end to end (filename + labels derive from `SEASON`); replace divergent duplicated logic with one shared helpers module (`pos_bucket`, `gini`, money formatting) imported by pipeline and experiments; make the standings join an explicit validated check; report dropped-row counts in `extract_salaries.py`.

**5. Site polish.** Outlier-only labels on the §04 scatter (same treatment as §08); fix legend swatches on the grouped multicolor charts; fix the m9 "DP threshold" label; contrast/accessibility pass; clean "Center Forward/Attacking Midfi" at extraction; unify Defence/Defense; add `experiments/` to the README tree.

**6. Deeper-analysis candidates.** Bias-corrected Gini (roster-size sensitivity); explicit handling of compositional payroll shares; prefer scatter-with-trend over ratio rankings for "efficiency"; document the top-1% definition (top 9 of 911 = int, vs 10 = ceil).

---

## Review telemetry

| | |
|---|---|
| Agents | 43 (5 reviewers, 37 verifiers, 1 orchestration) |
| Tokens | ~1.21M |
| Findings raised | 38 |
| Confirmed by adversarial verifier | 25 |
| Confirmed by direct inspection (verifier hit rate limit) | 13 |
| Refuted | 0 |

*Findings from the code dimension and four website findings were verified by inspection after their verifier agents failed on a session rate limit; every spot-check (Infinity in JSON, season/filename mismatch, divergent `pos_bucket` fallbacks, Defence/Defense count, `usdShort` edges) confirmed the reviewer's claim.*
