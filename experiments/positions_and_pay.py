"""Experiment: does WHERE you spend (by position) matter?

Two questions:
  A. TOP END  - what position is each club's highest-paid player, and does
     spending your top dollar on an attacker vs a defender/keeper relate to
     results? Also: does concentrating payroll on attack help?
  B. BOTTOM END - which positions fill the minimum-wage tier? i.e. which roles
     do clubs staff cheaply?

Reads:  data/mls_salaries_2026.csv, data/standings_2026.csv
Writes: experiments/outputs/top_earner_positions.csv
        experiments/outputs/position_pay_impact.png
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

BUCKET_COLOR = {"Attack": "#e23b3b", "Midfield": "#f2b705",
                "Defense": "#1f7ac4", "Goalkeeper": "#0f8a3c"}
ORDER = ["Attack", "Midfield", "Defense", "Goalkeeper"]


def bucket(pos):
    """Map a granular position to Attack / Midfield / Defense / Goalkeeper."""
    p = str(pos).split("/")[0].strip().lower()
    if "goalkeeper" in p:
        return "Goalkeeper"
    if "back" in p:                                  # center/left/right-back
        return "Defense"
    if "wing" in p or "forward" in p or "attacking mid" in p:
        return "Attack"
    if "midfield" in p:                              # central/defensive/L/R mid
        return "Midfield"
    return "Other"


sal = pd.read_csv(DATA / "mls_salaries_2026.csv")
sal = sal[sal["club"] != "MLS Pool"].copy()
sal["bucket"] = sal["position"].map(bucket)

st = pd.read_csv(DATA / "standings_2026.csv").set_index("club")
ppg = (st["pts"] / st["gp"]).rename("ppg")

# ======================================================================
# A. TOP END
# ======================================================================
print("=" * 74)
print("A.  THE TOP EARNER'S POSITION")
print("=" * 74)

top_rows = sal.loc[sal.groupby("club")[PAY].idxmax()].copy()
top_rows = top_rows.join(ppg, on="club")
top_rows["name"] = (top_rows["first_name"] + " " + top_rows["last_name"]).str.strip()

by_pos = (top_rows.groupby("bucket")
          .agg(clubs=("club", "count"), mean_ppg=("ppg", "mean"),
               mean_pay=(PAY, "mean"))
          .reindex([b for b in ORDER if b in top_rows["bucket"].unique()]))
print("Highest-paid player's position across the 30 clubs:")
for b, r in by_pos.iterrows():
    print(f"  {b:<11} is top earner at {int(r.clubs):>2} clubs   "
          f"avg team PPG {r.mean_ppg:.2f}   avg top-earner pay ${r.mean_pay/1e6:.1f}M")

# attacker-led vs not
atk = top_rows[top_rows.bucket == "Attack"].ppg
non = top_rows[top_rows.bucket != "Attack"].ppg
print(f"\nTop earner is an ATTACKER: {len(atk)} clubs, avg {atk.mean():.2f} PPG")
print(f"Top earner is NOT an attacker: {len(non)} clubs, avg {non.mean():.2f} PPG")
if len(atk) >= 2 and len(non) >= 2:
    t, p = stats.ttest_ind(atk, non, equal_var=False)
    print(f"  difference {atk.mean()-non.mean():+.2f} PPG  (Welch t p = {p:.2f}, "
          f"{'significant' if p < 0.05 else 'not significant'})")

# payroll share by position bucket, per club, vs PPG
share = (sal.groupby(["club", "bucket"])[PAY].sum()
         .groupby(level=0).apply(lambda s: s / s.sum())
         .unstack(fill_value=0.0))
share = share.join(ppg)
print("\nDoes concentrating payroll on a position group help? (share of team pay vs PPG)")
for b in ORDER:
    if b in share:
        r, p = stats.pearsonr(share[b], share["ppg"])
        print(f"  {b:<11} payroll share vs PPG:  r = {r:+.2f}  p = {p:.2f}  "
              f"({'significant' if p < 0.05 else 'n.s.'})")

# ======================================================================
# B. BOTTOM END
# ======================================================================
print("\n" + "=" * 74)
print("B.  THE MINIMUM-WAGE TIER")
print("=" * 74)
league_min = sal[PAY].min()
q25 = sal[PAY].quantile(0.25)
at_min = sal[sal[PAY] <= league_min * 1.0001]
bottomq = sal[sal[PAY] <= q25]
print(f"League minimum: ${league_min:,.0f}  ·  {len(at_min)} players sit exactly at it "
      f"({len(at_min)/len(sal):.0%} of the league)")
print(f"Bottom pay quartile threshold: ${q25:,.0f}\n")

overall = sal["bucket"].value_counts(normalize=True)
bq = bottomq["bucket"].value_counts(normalize=True)
print("Position mix of the BOTTOM pay quartile vs the whole league:")
print(f"  {'position':<11} {'bottom-Q':>9} {'league':>8} {'over/under':>12}")
for b in ORDER:
    o = overall.get(b, 0); q = bq.get(b, 0)
    idx = (q / o) if o else 0
    flag = "over" if idx > 1.08 else ("under" if idx < 0.92 else "same")
    print(f"  {b:<11} {q:>8.0%} {o:>8.0%}   {idx:>6.2f}x  {flag}")

# share of each position group paid at/near the minimum
print("\nShare of each position group earning at the league minimum:")
minshare = (sal.assign(is_min=sal[PAY] <= league_min * 1.0001)
            .groupby("bucket")["is_min"].mean().reindex(ORDER))
for b, v in minshare.items():
    if pd.notna(v):
        print(f"  {b:<11} {v:.0%} of players at the minimum")

# lowest-paid player per club position
low_rows = sal.loc[sal.groupby("club")[PAY].idxmin()]
lowmix = low_rows["bucket"].value_counts().reindex(ORDER, fill_value=0)
print("\nPosition of each club's LOWEST-paid player (30 clubs):")
for b, n in lowmix.items():
    print(f"  {b:<11} {int(n):>2} clubs")

# ---------- save + chart ----------
top_rows[["club", "name", "position", "bucket", PAY, "ppg"]].to_csv(
    OUT / "top_earner_positions.csv", index=False)

fig, axes = plt.subplots(1, 2, figsize=(13.5, 6))

# left: mean team PPG by top-earner position
d = by_pos.dropna()
axes[0].bar(d.index, d["mean_ppg"], color=[BUCKET_COLOR[b] for b in d.index])
for i, (b, r) in enumerate(d.iterrows()):
    axes[0].text(i, r["mean_ppg"] + 0.02, f"{r['mean_ppg']:.2f}\nn={int(r['clubs'])}",
                 ha="center", va="bottom", fontsize=9)
axes[0].axhline(top_rows["ppg"].mean(), color="#888", ls="--", lw=1,
                label=f"league avg {top_rows['ppg'].mean():.2f}")
axes[0].set_ylabel("Avg team points per game")
axes[0].set_title("Performance by the position of the top earner")
axes[0].legend(fontsize=8)
axes[0].set_ylim(0, max(d["mean_ppg"]) * 1.25)

# right: bottom-quartile position mix vs league
x = np.arange(len(ORDER)); w = 0.38
axes[1].bar(x - w/2, [overall.get(b, 0) for b in ORDER], w, label="whole league",
            color="#c9d6cc")
axes[1].bar(x + w/2, [bq.get(b, 0) for b in ORDER], w, label="bottom pay quartile",
            color=[BUCKET_COLOR[b] for b in ORDER])
axes[1].set_xticks(x); axes[1].set_xticklabels(ORDER)
axes[1].set_ylabel("Share of players")
axes[1].set_title("Who fills the minimum-wage tier?")
axes[1].legend(fontsize=8)
axes[1].yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))

fig.tight_layout()
fig.savefig(OUT / "position_pay_impact.png", dpi=130)
plt.close(fig)
print(f"\nSaved: {OUT/'top_earner_positions.csv'}")
print(f"Saved: {OUT/'position_pay_impact.png'}")
