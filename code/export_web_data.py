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

# Fallback conference map, only used if the standings file lacks a 'conf'
# column (older data). The live fetcher writes conf directly.
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

has_conf = "conf" in df.columns
clubs = [{
    "club": row.club,
    "conf": (row.conf if has_conf else ("East" if row.club in EAST else "West")),
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

# ---- roster construction: pay concentration + position of spend ----
POS_ORDER = ["Attack", "Midfield", "Defense", "Goalkeeper"]


def pos_bucket(pos):
    p = str(pos).split("/")[0].strip().lower()
    if "goalkeeper" in p:
        return "Goalkeeper"
    if "back" in p:
        return "Defense"
    if "wing" in p or "forward" in p or "attacking mid" in p:
        return "Attack"
    if "midfield" in p:
        return "Midfield"
    return "Midfield"


players["bucket"] = players["position"].map(pos_bucket)
ppg_by_club = (df.set_index("club")["ppg"]).to_dict()

# per-club Gini + PPG (for the scatter)
def gini(x):
    x = np.sort(np.asarray(x, float))
    n = len(x)
    return (2 * np.sum(np.arange(1, n + 1) * x) / (n * x.sum())) - (n + 1) / n

gini_by_club = []
for club_name, s in players.groupby("club")[PAY]:
    gini_by_club.append({
        "club": club_name, "gini": float(gini(s.values)),
        "ppg": float(ppg_by_club.get(club_name, float("nan"))),
        "payroll": float(s.sum()),
        "conf": "East" if club_name in EAST else "West",
    })
gvals = np.array([g["gini"] for g in gini_by_club])
pvals = np.array([g["ppg"] for g in gini_by_club])
gini_r, gini_p = stats.pearsonr(gvals, pvals)
# partial correlation of gini vs ppg controlling for log payroll
lp = np.log10([g["payroll"] for g in gini_by_club])
rg = gvals - np.poly1d(np.polyfit(lp, gvals, 1))(lp)
rp = pvals - np.poly1d(np.polyfit(lp, pvals, 1))(lp)
gini_partial_r, gini_partial_p = stats.pearsonr(rg, rp)

# position of each club's top earner + PPG by that bucket
top_idx = players.groupby("club")[PAY].idxmax()
top = players.loc[top_idx, ["club", "bucket", PAY]].copy()
top["ppg"] = top["club"].map(ppg_by_club)
top_bucket_counts = {b: int((top["bucket"] == b).sum()) for b in POS_ORDER}
ppg_by_top_bucket = {b: (float(top.loc[top["bucket"] == b, "ppg"].mean())
                         if (top["bucket"] == b).any() else None)
                     for b in POS_ORDER}

# payroll share by position bucket, per club + league average
sums = (players.groupby(["club", "bucket"])[PAY].sum().unstack(fill_value=0)
        .reindex(columns=POS_ORDER, fill_value=0))
share = sums.div(sums.sum(axis=1), axis=0)
league_share = {b: float(share[b].mean()) for b in POS_ORDER}
share_by_club = {c: {b: float(share.loc[c, b]) for b in POS_ORDER} for c in share.index}

# minimum-wage tier: position mix of bottom quartile vs whole league
q25 = players[PAY].quantile(0.25)
league_mix = players["bucket"].value_counts(normalize=True)
botq_mix = players[players[PAY] <= q25]["bucket"].value_counts(normalize=True)
league_mix = {b: float(league_mix.get(b, 0)) for b in POS_ORDER}
botq_mix = {b: float(botq_mix.get(b, 0)) for b in POS_ORDER}

SPOTLIGHT = "Atlanta United"
roster = {
    "posOrder": POS_ORDER,
    "giniByClub": sorted(gini_by_club, key=lambda d: -d["gini"]),
    "giniR": float(gini_r), "giniP": float(gini_p),
    "giniPartialR": float(gini_partial_r), "giniPartialP": float(gini_partial_p),
    "topBucketCounts": top_bucket_counts,
    "ppgByTopBucket": ppg_by_top_bucket,
    "leagueAvgTopPPG": float(top["ppg"].mean()),
    "leagueShare": league_share,
    "shareByClub": share_by_club,
    "leagueMix": league_mix, "bottomQuartileMix": botq_mix,
    "minWageShare": {
        b: float((players[players["bucket"] == b][PAY] <= players[PAY].min() * 1.0001).mean())
        for b in POS_ORDER},
    "spotlight": SPOTLIGHT,
}

# ---- deeper analyses: marketability gap, goal efficiency, stars vs middle ----
BASE = "base_salary"


def _pear(a, b):
    r, pv = stats.pearsonr(a, b)
    return round(float(r), 3), round(float(pv), 3)


# 1) marketability gap: guaranteed comp above base salary
pg = players.copy()
pg["gap"] = pg[PAY] - pg[BASE]
pg["name"] = (pg["first_name"].fillna("") + " " + pg["last_name"].fillna("")).str.strip()
base_total, guar_total = float(pg[BASE].sum()), float(pg[PAY].sum())
mkt_total = guar_total - base_total
top_gap = pg.nlargest(15, "gap")
club_mkt = pg.groupby("club").agg(marketing=("gap", "sum"), payroll=(PAY, "sum"))
club_mkt["mpct"] = club_mkt["marketing"] / club_mkt["payroll"]
club_mkt["ppg"] = club_mkt.index.map(ppg_by_club)
mkt_r, mkt_p = _pear(club_mkt["mpct"].values, club_mkt["ppg"].values)
gap = {
    "baseTotal": base_total, "guarTotal": guar_total,
    "marketingTotal": mkt_total, "marketingPct": mkt_total / guar_total,
    "nWithGap": int((pg["gap"] > 1).sum()), "nPlayers": int(len(pg)),
    "topGap": [{"name": r["name"], "club": r.club, "bucket": r.bucket,
                "base": float(r[BASE]), "guar": float(r[PAY]), "gap": float(r.gap)}
               for _, r in top_gap.iterrows()],
    "byPosition": [{"bucket": b, "marketing": float(pg.loc[pg.bucket == b, "gap"].sum()),
                    "shareWithGap": float((pg.loc[pg.bucket == b, "gap"] > 1).mean())}
                   for b in POS_ORDER],
    "marketingPpgR": mkt_r, "marketingPpgP": mkt_p,
}

# 2) goal difference / position-spending efficiency
gcl = pd.DataFrame({
    "attackPay": sums["Attack"],
    "defPay": sums["Defense"] + sums["Goalkeeper"],
    "payroll": sums.sum(axis=1),
}).join(st[["gf", "ga", "gd", "conf"]])
gcl["ppg"] = gcl.index.map(ppg_by_club)
gcl["goalsPer10mAtk"] = gcl["gf"] / (gcl["attackPay"] / 1e7)
gcl = gcl.reset_index()
atk_gf = _pear(gcl["attackPay"].values, gcl["gf"].values)
def_ga = _pear(gcl["defPay"].values, gcl["ga"].values)
pay_gd = _pear(np.log10(gcl["payroll"].values), gcl["gd"].values)
goals = {
    "clubs": [{"club": r.club, "conf": r.conf, "attackPay": float(r.attackPay),
               "defPay": float(r.defPay), "payroll": float(r.payroll),
               "gf": int(r.gf), "ga": int(r.ga), "gd": int(r.gd),
               "ppg": float(r.ppg), "goalsPer10mAtk": float(r.goalsPer10mAtk)}
              for _, r in gcl.iterrows()],
    "attackGfR": atk_gf[0], "attackGfP": atk_gf[1],
    "defGaR": def_ga[0], "defGaP": def_ga[1],
    "payrollGdR": pay_gd[0], "payrollGdP": pay_gd[1],
}


# 3) stars (top-3 pay) vs the roster's "middle class"
def _club_stats(d):
    d = d.sort_values(PAY, ascending=False)
    rest = d[PAY].iloc[3:]
    return pd.Series({"payroll": float(d[PAY].sum()), "top3": float(d[PAY].iloc[:3].sum()),
                      "restMedian": float(rest.median()), "floor": float(d[PAY].min())})


mc = players.groupby("club").apply(_club_stats, include_groups=False)
mc["top3Share"] = mc["top3"] / mc["payroll"]
mc = mc.join(st[["gf", "ga", "gd"]])
mc["ppg"] = mc.index.map(ppg_by_club)
_lt = {"Top-3 stars": np.log10(mc["top3"].values),
       "Middle class": np.log10(mc["restMedian"].values),
       "Roster floor": np.log10(mc["floor"].values)}
_out = {"ppg": mc["ppg"].values, "gf": mc["gf"].values, "ga": mc["ga"].values}
corrgrid = {name: {mk: _pear(x, col)[0] for mk, col in _out.items()} for name, x in _lt.items()}
top3_ppg = _pear(_lt["Top-3 stars"], mc["ppg"].values)
rest_ppg = _pear(_lt["Middle class"], mc["ppg"].values)
floor_ppg = _pear(_lt["Roster floor"], mc["ppg"].values)
middle = {
    "clubs": [{"club": c, "payroll": float(r.payroll), "top3": float(r.top3),
               "top3Share": float(r.top3Share), "restMedian": float(r.restMedian),
               "floor": float(r.floor), "ppg": float(r.ppg), "gd": int(r.gd)}
              for c, r in mc.iterrows()],
    "top3PpgR": top3_ppg[0], "top3PpgP": top3_ppg[1],
    "restMedianPpgR": rest_ppg[0], "restMedianPpgP": rest_ppg[1],
    "floorPpgR": floor_ppg[0], "floorPpgP": floor_ppg[1],
    "corr": {
        "tiers": list(_lt.keys()),
        "metrics": [
            {"key": "ppg", "label": "Points per game", "values": [corrgrid[t]["ppg"] for t in _lt]},
            {"key": "gf", "label": "Goals scored", "values": [corrgrid[t]["gf"] for t in _lt]},
            {"key": "ga", "label": "Goals Conceded (negative bar is better)",
             "values": [corrgrid[t]["ga"] for t in _lt]},
        ],
    },
}

data = {
    "league": league, "hist": hist, "topEarners": topEarners,
    "positions": positions, "clubs": clubs, "regression": regression,
    "roster": roster, "gap": gap, "goals": goals, "middle": middle,
}

out = ROOT / "web" / "site_data.js"
with open(out, "w", encoding="utf-8") as f:
    f.write("window.MLS_DATA = ")
    json.dump(data, f, indent=1)
    f.write(";\n")

print(f"Wrote {out.name}  ({len(clubs)} clubs, {len(topEarners)} earners)")
