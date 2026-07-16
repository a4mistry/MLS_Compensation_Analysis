"""Pay-for-performance: compare 2026 club payroll to on-field results.

Season is partial (~14-15 of 34 games, standings as of ~2026-07-14), so we use
rate stats (points per game) rather than raw totals to keep clubs comparable.

Efficiency question: which clubs turn payroll dollars into points most (and
least) effectively?  We look at two lenses:
  1. Cost per point   = payroll / points earned  (lower = more efficient)
  2. Regression residual = actual PPG vs. the PPG that spending predicts
     (positive = overperforming the money; negative = underperforming)
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
CHARTS = DATA / "charts"

sns.set_theme(style="whitegrid")

sal = pd.read_csv(DATA / "mls_salaries_2026.csv")
sal = sal[sal["club"] != "MLS Pool"]
pay = sal.groupby("club")["guaranteed_comp"].agg(payroll="sum", roster="count")

st = pd.read_csv(DATA / "standings_2026.csv").set_index("club")
df = st.join(pay).reset_index()
missing = df.loc[df["payroll"].isna(), "club"].tolist()
if missing:
    raise SystemExit(f"No salary data for clubs in standings: {missing}")

# --- rate + efficiency metrics ------------------------------------------
# Guard early-season divisions (0 games / 0 points -> NaN, never Infinity).
df["ppg"] = np.where(df["gp"] > 0, df["pts"] / df["gp"], np.nan)
df["payroll_m"] = df["payroll"] / 1e6
df["cost_per_point"] = np.where(df["pts"] > 0, df["payroll"] / df["pts"], np.nan)
df["pts_per_10m"] = df["pts"] / (df["payroll"] / 1e7)

# Regression: does spending predict results?  Log payroll vs PPG (played clubs).
_played = df[df["gp"] > 0]
x = np.log10(_played["payroll"])
y = _played["ppg"]
slope, intercept, r, p, se = stats.linregress(x, y)
df["ppg_pred"] = intercept + slope * np.log10(df["payroll"])
df["residual"] = df["ppg"] - df["ppg_pred"]          # over/under vs spend
r2 = r ** 2


def money(v):
    return f"${v:,.0f}"


print("=" * 70)
print("PAYROLL vs PERFORMANCE  (2026, ~mid-season)")
print("=" * 70)
print(f"Payroll explains {r2:5.1%} of the variation in points-per-game (R^2).")
print(f"Correlation payroll<->PPG: r = {r:+.2f}  (p = {p:.3f})")
print("Interpretation: money helps, but leaves most of performance unexplained.\n")

# --- Most / least efficient by cost per point ---------------------------
eff = df.sort_values("cost_per_point")
show = ["club", "pts", "ppg", "payroll_m", "cost_per_point", "pts_per_10m"]
print("-" * 70)
print("MOST EFFICIENT  (lowest $ per point)")
print("-" * 70)
for _, r_ in eff.head(8).iterrows():
    print(f"  {r_.club:<24} {money(r_.cost_per_point):>12}/pt  "
          f"{r_.pts:>2.0f} pts  ${r_.payroll_m:5.1f}M  "
          f"{r_.pts_per_10m:4.1f} pts/$10M")

print("\n" + "-" * 70)
print("LEAST EFFICIENT  (highest $ per point)")
print("-" * 70)
for _, r_ in eff.tail(8).iloc[::-1].iterrows():
    print(f"  {r_.club:<24} {money(r_.cost_per_point):>12}/pt  "
          f"{r_.pts:>2.0f} pts  ${r_.payroll_m:5.1f}M  "
          f"{r_.pts_per_10m:4.1f} pts/$10M")

# --- Over/under performers vs what spending predicts --------------------
res = df.sort_values("residual", ascending=False)
print("\n" + "=" * 70)
print("VALUE vs SPEND  (residual: actual PPG minus spend-predicted PPG)")
print("=" * 70)
print("Biggest OVERPERFORMERS (punching above their payroll):")
for _, r_ in res.head(6).iterrows():
    print(f"  {r_.club:<24} {r_.residual:+.2f} PPG   "
          f"(actual {r_.ppg:.2f} vs predicted {r_.ppg_pred:.2f})  ${r_.payroll_m:.1f}M")
print("\nBiggest UNDERPERFORMERS (paying for results they aren't getting):")
for _, r_ in res.tail(6).iloc[::-1].iterrows():
    print(f"  {r_.club:<24} {r_.residual:+.2f} PPG   "
          f"(actual {r_.ppg:.2f} vs predicted {r_.ppg_pred:.2f})  ${r_.payroll_m:.1f}M")

df.sort_values("residual", ascending=False).to_csv(DATA / "efficiency_2026.csv", index=False)
print("\nFull table -> efficiency_2026.csv")

# ================================================================ charts
fmt_m = mticker.FuncFormatter(lambda v, _: f"${v:.0f}M")

# 1. Scatter: payroll vs PPG with regression line + labels
fig, ax = plt.subplots(figsize=(11, 7.5))
ax.scatter(df["payroll_m"], df["ppg"], s=70, color="#4C72B0", zorder=3)
xs = np.linspace(df["payroll"].min(), df["payroll"].max(), 100)
ax.plot(xs / 1e6, intercept + slope * np.log10(xs), color="#C44E52", ls="--",
        label=f"trend (R²={r2:.2f})")
for _, r_ in df.iterrows():
    ax.annotate(r_.club, (r_.payroll_m, r_.ppg), fontsize=7.5,
                xytext=(4, 4), textcoords="offset points")
ax.set_xscale("log")
ax.xaxis.set_major_formatter(fmt_m)
ax.set_xlabel("Total payroll (guaranteed comp, log scale)")
ax.set_ylabel("Points per game")
ax.set_title("MLS 2026: spending vs results — above the line = good value")
ax.legend()
fig.tight_layout()
fig.savefig(CHARTS / "05_payroll_vs_points.png", dpi=130)
plt.close(fig)

# 2. Cost per point ranking
fig, ax = plt.subplots(figsize=(9, 9))
e = df.sort_values("cost_per_point", ascending=False)
colors = ["#C44E52" if v > df.cost_per_point.median() else "#55A868"
          for v in e["cost_per_point"]]
ax.barh(e["club"], e["cost_per_point"] / 1e6, color=colors)
ax.xaxis.set_major_formatter(fmt_m)
ax.set_xlabel("Cost per point ($M) — shorter is more efficient")
ax.set_title("Payroll efficiency: dollars spent per point earned (2026)")
fig.tight_layout()
fig.savefig(CHARTS / "06_cost_per_point.png", dpi=130)
plt.close(fig)

# 3. Value residual (over/underperformance vs spend)
fig, ax = plt.subplots(figsize=(9, 9))
v = df.sort_values("residual")
colors = ["#55A868" if x > 0 else "#C44E52" for x in v["residual"]]
ax.barh(v["club"], v["residual"], color=colors)
ax.axvline(0, color="k", lw=0.8)
ax.set_xlabel("PPG above (+) / below (−) what payroll predicts")
ax.set_title("Value for money: over- and under-performers vs spending (2026)")
fig.tight_layout()
fig.savefig(CHARTS / "07_value_residual.png", dpi=130)
plt.close(fig)

print("Charts -> charts/05_payroll_vs_points.png, 06_cost_per_point.png, 07_value_residual.png")
