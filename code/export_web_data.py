"""Export all analysis results to web/site_data.js for the narrative website.

Writes a single JS file (in web/, next to index.html) that sets
window.MLS_DATA = {...} so the site works when opened directly from disk
(file://) with no server / fetch / CORS issues.
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PAY = "guaranteed_comp"

EAST = {
    "Nashville SC", "Inter Miami", "Chicago Fire", "New England Revolution",
    "New York Red Bulls", "Charlotte FC", "FC Cincinnati", "New York City FC",
    "DC United", "Columbus Crew", "CF Montreal", "Orlando City SC",
    "Toronto FC", "Atlanta United", "Philadelphia Union",
}

sal = pd.read_csv(DATA / "mls_salaries_2026.csv")
players = sal[sal["club"] != "MLS Pool"].copy()
s = players[PAY]


def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return (2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum())) - (n + 1) / n


# ---- league-wide ----
league = {
    "asOf": "April 14, 2026",
    "players": int(len(players)),
    "clubs": int(players["club"].nunique()),
    "totalPayroll": float(s.sum()),
    "mean": float(s.mean()),
    "median": float(s.median()),
    "min": float(s.min()),
    "max": float(s.max()),
    "p90": float(np.percentile(s, 90)),
    "p95": float(np.percentile(s, 95)),
    "p99": float(np.percentile(s, 99)),
    "gini": float(gini(s)),
    "top1Share": float(s.nlargest(max(1, len(s) // 100)).sum() / s.sum()),
    "top10Share": float(s.nlargest(len(s) // 10).sum() / s.sum()),
    "leagueMin": float(s.min()),
}

# ---- pay distribution histogram (log bins) ----
edges = np.logspace(np.log10(s.min()), np.log10(s.max()), 32)
counts, _ = np.histogram(s, bins=edges)
hist = [{"lo": float(edges[i]), "hi": float(edges[i + 1]), "n": int(counts[i])}
        for i in range(len(counts))]

# ---- top earners ----
top = players.nlargest(20, PAY)
topEarners = [{
    "name": f"{r.first_name} {r.last_name}".strip(),
    "club": r.club, "position": r.position, "comp": float(r[PAY]),
} for _, r in top.iterrows()]

# ---- position medians ----
pos = (players.groupby("position")[PAY].agg(median="median", mean="mean", n="count")
       .query("n >= 5").sort_values("median", ascending=False))
positions = [{"position": p, "median": float(r["median"]),
              "mean": float(r["mean"]), "n": int(r.n)} for p, r in pos.iterrows()]

# ---- clubs: payroll + standings + efficiency ----
pay = players.groupby("club")[PAY].agg(payroll="sum", roster="count",
                                       medianPay="median", topPay="max")
st = pd.read_csv(DATA / "standings_2026.csv").set_index("club")
df = st.join(pay).reset_index()

df["ppg"] = df["pts"] / df["gp"]
df["cost_per_point"] = df["payroll"] / df["pts"]
df["pts_per_10m"] = df["pts"] / (df["payroll"] / 1e7)

x = np.log10(df["payroll"]); y = df["ppg"]
slope, intercept, r, p, se = stats.linregress(x, y)
df["ppg_pred"] = intercept + slope * x
df["residual"] = df["ppg"] - df["ppg_pred"]

clubs = [{
    "club": row.club,
    "conf": "East" if row.club in EAST else "West",
    "payroll": float(row.payroll),
    "roster": int(row.roster),
    "medianPay": float(row.medianPay),
    "topPay": float(row.topPay),
    "gp": int(row.gp), "w": int(row.w), "l": int(row.l), "d": int(row.d),
    "pts": int(row.pts), "gf": int(row.gf), "ga": int(row.ga), "gd": int(row.gd),
    "ppg": float(row.ppg),
    "costPerPoint": float(row.cost_per_point),
    "ptsPer10m": float(row.pts_per_10m),
    "residual": float(row.residual),
    "ppgPred": float(row.ppg_pred),
} for _, row in df.iterrows()]

regression = {
    "slope": float(slope), "intercept": float(intercept),
    "r": float(r), "r2": float(r ** 2), "p": float(p),
    "xmin": float(df["payroll"].min()), "xmax": float(df["payroll"].max()),
}

data = {
    "league": league, "hist": hist, "topEarners": topEarners,
    "positions": positions, "clubs": clubs, "regression": regression,
}

out = ROOT / "web" / "site_data.js"
with open(out, "w", encoding="utf-8") as f:
    f.write("window.MLS_DATA = ")
    json.dump(data, f, indent=1)
    f.write(";\n")

print(f"Wrote {out.name}  ({len(clubs)} clubs, {len(topEarners)} earners)")
