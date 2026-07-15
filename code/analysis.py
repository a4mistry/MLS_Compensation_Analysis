"""Analysis of 2026 MLS player compensation (from mls_salaries_2026.csv).

Uses 'guaranteed_comp' (guaranteed compensation) as the headline pay figure,
since it captures base salary plus marketing/bonus money and is the standard
metric for MLS pay comparisons.

Outputs:
  - Console summary tables
  - charts/*.png visualizations
"""
import os
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = DATA / "charts"

sns.set_theme(style="whitegrid")
os.makedirs(CHARTS, exist_ok=True)

df = pd.read_csv(DATA / "mls_salaries_2026.csv")
# Focus on real clubs; drop the league "MLS Pool" bucket for club comparisons.
players = df[df["club"] != "MLS Pool"].copy()
PAY = "guaranteed_comp"


def money(x):
    return f"${x:,.0f}"


def usd_axis(ax, axis="x"):
    fmt = mticker.FuncFormatter(lambda v, _: f"${v/1e6:.0f}M" if v >= 1e6 else f"${v/1e3:.0f}K")
    (ax.xaxis if axis == "x" else ax.yaxis).set_major_formatter(fmt)


# ---------------------------------------------------------------- league-wide
print("=" * 64)
print("LEAGUE-WIDE COMPENSATION (guaranteed comp, 2026)")
print("=" * 64)
s = players[PAY]
print(f"Players            : {len(players)}")
print(f"Total payroll      : {money(s.sum())}")
print(f"Mean               : {money(s.mean())}")
print(f"Median             : {money(s.median())}")
print(f"Std dev            : {money(s.std())}")
print(f"Min / Max          : {money(s.min())} / {money(s.max())}")
for p in (90, 95, 99):
    print(f"{p}th percentile    : {money(np.percentile(s, p))}")

# Inequality: share of pay taken by the top earners + a Gini coefficient
def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return (2 * np.sum((np.arange(1, n + 1)) * x) / (n * x.sum())) - (n + 1) / n

top1_share = s.nlargest(max(1, len(s) // 100)).sum() / s.sum()
top10_share = s.nlargest(len(s) // 10).sum() / s.sum()
print(f"\nGini coefficient   : {gini(s):.3f}  (0=equal, 1=maximally unequal)")
print(f"Top 1% earn        : {top1_share:5.1%} of all pay")
print(f"Top 10% earn       : {top10_share:5.1%} of all pay")
print(f"Median as % of mean: {s.median()/s.mean():5.1%}  (right-skew indicator)")

# ---------------------------------------------------------------- top earners
print("\n" + "=" * 64)
print("TOP 15 EARNERS")
print("=" * 64)
top = players.nlargest(15, PAY)[["first_name", "last_name", "club", "position", PAY]]
for _, r in top.iterrows():
    name = f"{r.first_name} {r.last_name}".strip()
    print(f"  {money(r[PAY]):>14}  {name:<24} {r.club:<22} {r.position}")

# ---------------------------------------------------------------- by club
print("\n" + "=" * 64)
print("CLUB PAYROLL (total guaranteed comp)")
print("=" * 64)
club = players.groupby("club")[PAY].agg(
    total="sum", mean="mean", median="median", n="count", top="max"
).sort_values("total", ascending=False)
club["total_$"] = club["total"].map(money)
club["median_$"] = club["median"].map(money)
print(club[["n", "total_$", "median_$"]].to_string())
print(f"\nMost top-heavy (mean/median ratio):")
club["skew"] = club["mean"] / club["median"]
for c, row in club.sort_values("skew", ascending=False).head(5).iterrows():
    print(f"  {c:<22} mean/median = {row['skew']:4.1f}x")

# ---------------------------------------------------------------- by position
print("\n" + "=" * 64)
print("PAY BY POSITION (median guaranteed comp)")
print("=" * 64)
pos = players.groupby("position")[PAY].agg(
    median="median", mean="mean", n="count"
).query("n >= 5").sort_values("median", ascending=False)
for p, row in pos.iterrows():
    print(f"  {money(row['median']):>12} (median)  n={int(row.n):>3}  {p}")

# ================================================================ charts
# 1. Distribution of pay (log scale) with median/mean lines
fig, ax = plt.subplots(figsize=(9, 5))
ax.hist(s, bins=np.logspace(np.log10(s.min()), np.log10(s.max()), 40),
        color="#4C72B0", edgecolor="white")
ax.set_xscale("log")
ax.axvline(s.median(), color="#C44E52", ls="--", label=f"median {money(s.median())}")
ax.axvline(s.mean(), color="#55A868", ls="--", label=f"mean {money(s.mean())}")
ax.set_xlabel("Guaranteed compensation (log scale)")
ax.set_ylabel("Number of players")
ax.set_title("MLS 2026 pay distribution is heavily right-skewed")
ax.legend()
fig.tight_layout()
fig.savefig(CHARTS / "01_pay_distribution.png", dpi=130)
plt.close(fig)

# 2. Club total payroll (stacked: not-top vs top earner to show DP effect)
fig, ax = plt.subplots(figsize=(9, 9))
order = club.sort_values("total").index
rest = (club.loc[order, "total"] - club.loc[order, "top"])
ax.barh(order, rest, color="#4C72B0", label="rest of roster")
ax.barh(order, club.loc[order, "top"], left=rest, color="#C44E52",
        label="top earner")
usd_axis(ax, "x")
ax.set_xlabel("Total guaranteed compensation")
ax.set_title("Club payrolls and the weight of each club's top earner")
ax.legend(loc="lower right")
fig.tight_layout()
fig.savefig(CHARTS / "02_club_payroll.png", dpi=130)
plt.close(fig)

# 3. Median pay by position
fig, ax = plt.subplots(figsize=(9, 7))
pos_sorted = pos.sort_values("median")
ax.barh(pos_sorted.index, pos_sorted["median"], color="#55A868")
usd_axis(ax, "x")
ax.set_xlabel("Median guaranteed compensation")
ax.set_title("Median MLS pay by position (positions with 5+ players)")
fig.tight_layout()
fig.savefig(CHARTS / "03_pay_by_position.png", dpi=130)
plt.close(fig)

# 4. Club distributions (boxplot, log scale) ordered by median
fig, ax = plt.subplots(figsize=(10, 9))
med_order = players.groupby("club")[PAY].median().sort_values().index
sns.boxplot(data=players, y="club", x=PAY, order=med_order, ax=ax,
            color="#8172B3", whis=(0, 100), showfliers=False)
ax.set_xscale("log")
usd_axis(ax, "x")
ax.set_xlabel("Guaranteed compensation (log scale)")
ax.set_ylabel("")
ax.set_title("Within-club pay spread (ordered by median)")
fig.tight_layout()
fig.savefig(CHARTS / "04_club_boxplots.png", dpi=130)
plt.close(fig)

print("\nCharts written to charts/  (4 PNGs)")
