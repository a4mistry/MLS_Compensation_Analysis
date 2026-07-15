"""Experiment: does pay INEQUALITY within a squad help or hurt results?

Question: is it better to field a balanced roster (pay close to the average)
or a top-heavy one (a few superstars carried by minimum-wage players)?

Approach
--------
1. Compute each club's Gini coefficient of guaranteed compensation
   (0 = everyone paid equally, 1 = one player takes everything).
2. Relate Gini to points-per-game (PPG), the season-to-date performance rate.
3. Crucially, CONTROL FOR TOTAL PAYROLL. Top-heavy squads also tend to be
   big spenders, so a raw Gini-vs-PPG link could just be a spending effect.
   A partial correlation and a multiple regression isolate the pure effect of
   *concentration* at a given budget.
4. Cross-check with two simpler inequality measures (top earner's share of
   payroll, and the top/median pay ratio) so the finding isn't a Gini artifact.

Reads:  data/mls_salaries_2026.csv, data/standings_2026.csv
Writes: experiments/outputs/gini_vs_performance.csv
        experiments/outputs/gini_vs_ppg.png
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = Path(__file__).resolve().parent / "outputs"
os.makedirs(OUT, exist_ok=True)
PAY = "guaranteed_comp"


def gini(x):
    x = np.sort(np.asarray(x, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return np.nan
    return (2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum())) - (n + 1) / n


def partial_corr(a, b, c):
    """Correlation of a and b after removing the linear effect of control c."""
    ra = a - np.poly1d(np.polyfit(c, a, 1))(c)
    rb = b - np.poly1d(np.polyfit(c, b, 1))(c)
    r, p = stats.pearsonr(ra, rb)
    return r, p


# ---------- build per-club table ----------
sal = pd.read_csv(DATA / "mls_salaries_2026.csv")
sal = sal[sal["club"] != "MLS Pool"]

g = sal.groupby("club")[PAY]
club = pd.DataFrame({
    "gini": g.apply(lambda s: gini(s.values)),
    "payroll": g.sum(),
    "median": g.median(),
    "top": g.max(),
    "roster": g.count(),
})
club["top_share"] = club["top"] / club["payroll"]      # share taken by top earner
club["top_to_median"] = club["top"] / club["median"]   # superstar / typical player

st = pd.read_csv(DATA / "standings_2026.csv").set_index("club")
df = club.join(st).reset_index()
df["ppg"] = df["pts"] / df["gp"]
df["log_payroll"] = np.log10(df["payroll"])

df = df.sort_values("gini", ascending=False).reset_index(drop=True)

# ---------- correlations ----------
def line(name, r, p):
    sig = "significant" if p < 0.05 else "not significant"
    print(f"  {name:<46} r = {r:+.2f}   p = {p:.3f}   ({sig})")

print("=" * 74)
print("PAY CONCENTRATION vs PERFORMANCE  (30 clubs, 2026 YTD)")
print("=" * 74)
print(f"Gini range: {df.gini.min():.2f} (most balanced: {df.loc[df.gini.idxmin(),'club']})"
      f"  ->  {df.gini.max():.2f} (most top-heavy: {df.loc[df.gini.idxmax(),'club']})")
print(f"Mean club Gini: {df.gini.mean():.2f}\n")

print("Raw correlations with points-per-game:")
line("Gini vs PPG", *stats.pearsonr(df.gini, df.ppg))
line("Top earner's payroll share vs PPG", *stats.pearsonr(df.top_share, df.ppg))
line("Top/median pay ratio vs PPG", *stats.pearsonr(df.top_to_median, df.ppg))
line("(reference) log payroll vs PPG", *stats.pearsonr(df.log_payroll, df.ppg))

print("\nControlling for total payroll (does concentration help at a fixed budget?):")
line("Gini vs PPG | payroll (partial)", *partial_corr(df.gini.values, df.ppg.values, df.log_payroll.values))
line("Top share vs PPG | payroll (partial)", *partial_corr(df.top_share.values, df.ppg.values, df.log_payroll.values))

# ---------- multiple regression: PPG ~ payroll + gini ----------
def ols(X, y):
    X1 = np.column_stack([np.ones(len(X))] + [X[:, i] for i in range(X.shape[1])])
    beta, *_ = np.linalg.lstsq(X1, y, rcond=None)
    yhat = X1 @ beta
    ss_res = np.sum((y - yhat) ** 2)
    ss_tot = np.sum((y - y.mean()) ** 2)
    return beta, 1 - ss_res / ss_tot

y = df.ppg.values
# standardize predictors so coefficients are comparable (per 1 SD)
zp = (df.log_payroll - df.log_payroll.mean()) / df.log_payroll.std()
zg = (df.gini - df.gini.mean()) / df.gini.std()
b_pay, r2_pay = ols(zp.values.reshape(-1, 1), y)
b_both, r2_both = ols(np.column_stack([zp, zg]), y)

print("\nMultiple regression of PPG (standardized predictors, per +1 SD):")
print(f"  payroll only          : R^2 = {r2_pay:.3f}   payroll beta = {b_pay[1]:+.3f} PPG/SD")
print(f"  payroll + gini        : R^2 = {r2_both:.3f}   payroll beta = {b_both[1]:+.3f}, "
      f"gini beta = {b_both[2]:+.3f} PPG/SD")
print(f"  extra variance from adding gini: {r2_both - r2_pay:+.3f}")

# ---------- tercile comparison ----------
df["gini_group"] = pd.qcut(df.gini, 3, labels=["Balanced", "Middle", "Top-heavy"])
grp = df.groupby("gini_group", observed=True).agg(
    n=("club", "count"), mean_ppg=("ppg", "mean"),
    mean_pts=("pts", "mean"), mean_payroll=("payroll", "mean"))
print("\nClubs split into thirds by Gini:")
for name, r in grp.iterrows():
    print(f"  {name:<10} n={int(r.n)}  avg {r.mean_ppg:.2f} PPG  "
          f"(~{r.mean_pts:.0f} pts)  avg payroll ${r.mean_payroll/1e6:.1f}M")

# ---------- save table ----------
cols = ["club", "gini", "top_share", "top_to_median", "payroll", "roster",
        "gp", "pts", "ppg", "gini_group"]
df[cols].to_csv(OUT / "gini_vs_performance.csv", index=False)

# ---------- chart: Gini vs PPG, quadrant view ----------
fig, ax = plt.subplots(figsize=(11, 7.5))
gmed, pmed = df.gini.median(), df.ppg.median()
ax.axvline(gmed, color="#bbb", lw=1, ls="--", zorder=1)
ax.axhline(pmed, color="#bbb", lw=1, ls="--", zorder=1)

sizes = 40 + (df.payroll / df.payroll.max()) * 900
colors = ["#0f8a3c" if c == "East" else "#1f7ac4" for c in df.get("conf", ["East"] * len(df))]
ax.scatter(df.gini, df.ppg, s=sizes, c=colors, alpha=.8, edgecolor="white", linewidth=1.2, zorder=3)
for _, r in df.iterrows():
    ax.annotate(r.club, (r.gini, r.ppg), fontsize=7.5, xytext=(5, 4),
                textcoords="offset points", color="#333")

# quadrant labels
ax.text(0.98, 0.97, "TOP-HEAVY + WINNING", transform=ax.transAxes, ha="right", va="top",
        fontsize=9, color="#0a6b2f", weight="bold")
ax.text(0.02, 0.97, "BALANCED + WINNING", transform=ax.transAxes, ha="left", va="top",
        fontsize=9, color="#0a6b2f", weight="bold")
ax.text(0.98, 0.03, "TOP-HEAVY + LOSING", transform=ax.transAxes, ha="right", va="bottom",
        fontsize=9, color="#b23", weight="bold")
ax.text(0.02, 0.03, "BALANCED + LOSING", transform=ax.transAxes, ha="left", va="bottom",
        fontsize=9, color="#b23", weight="bold")

r_all, p_all = stats.pearsonr(df.gini, df.ppg)
ax.set_xlabel("Pay inequality within squad  (Gini of guaranteed comp)")
ax.set_ylabel("Points per game")
ax.set_title(f"Squad pay concentration vs performance  (r = {r_all:+.2f}, "
             f"p = {p_all:.2f}; bubble = payroll)")
fig.tight_layout()
fig.savefig(OUT / "gini_vs_ppg.png", dpi=130)
plt.close(fig)

print(f"\nSaved: {OUT / 'gini_vs_performance.csv'}")
print(f"Saved: {OUT / 'gini_vs_ppg.png'}")
