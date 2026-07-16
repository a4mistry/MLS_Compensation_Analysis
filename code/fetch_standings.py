"""Fetch live MLS standings (2026 YTD) from ESPN's public API.

Writes data/standings_2026.csv with each club's games played, wins, losses,
draws, points, goals for/against, goal difference, and conference — mapped to
the same club names used in the salary CSV so the rest of the pipeline joins
cleanly.

Source: ESPN's public sports API (no key required):
  https://site.api.espn.com/apis/v2/sports/soccer/usa.1/standings

Teams are matched by ESPN's stable numeric team id, so the mapping does not
break if display names or abbreviations change. If the network call fails and
a standings file already exists, we keep the existing file rather than wiping
it, so the pipeline can still run offline with the last-known data.
"""
import csv
import json
import os
import ssl
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
OUT = DATA / "standings_2026.csv"

# MLS season = calendar year; override with MLS_SEASON if needed.
SEASON = int(os.environ.get("MLS_SEASON", datetime.now().year))
URL = ("https://site.api.espn.com/apis/v2/sports/soccer/usa.1/"
       f"standings?season={SEASON}")

# ESPN team id -> club name as it appears in mls_salaries_2026.csv
ESPN_ID_TO_CLUB = {
    182: "Chicago Fire", 183: "Columbus Crew", 189: "New England Revolution",
    190: "New York Red Bulls", 193: "DC United", 7318: "Toronto FC",
    9720: "CF Montreal", 10739: "Philadelphia Union", 12011: "Orlando City SC",
    17606: "New York City FC", 18267: "FC Cincinnati", 18418: "Atlanta United",
    18986: "Nashville SC", 20232: "Inter Miami", 21300: "Charlotte FC",
    184: "Colorado Rapids", 185: "FC Dallas", 186: "Sporting Kansas City",
    187: "LA Galaxy", 191: "San Jose Earthquakes", 4771: "Real Salt Lake",
    6077: "Houston Dynamo", 9723: "Portland Timbers", 9726: "Seattle Sounders FC",
    9727: "Vancouver Whitecaps", 17362: "Minnesota United", 18966: "LAFC",
    20906: "Austin FC", 21812: "St. Louis City SC", 22529: "San Diego FC",
}

COLUMNS = ["club", "gp", "w", "l", "d", "pts", "gf", "ga", "gd", "conf"]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    ctx = ssl.create_default_context()
    with urllib.request.urlopen(req, timeout=30, context=ctx) as r:
        return json.load(r)


def parse(data):
    rows = []
    for child in data.get("children", []):
        conf = "East" if "East" in child.get("name", "") else "West"
        for e in child["standings"]["entries"]:
            team = e["team"]
            tid = int(team["id"])
            club = ESPN_ID_TO_CLUB.get(tid)
            if club is None:
                raise KeyError(f"Unmapped ESPN team id {tid} "
                               f"({team.get('displayName')}) — update ESPN_ID_TO_CLUB")
            s = {st["name"]: st.get("value") for st in e["stats"]}
            rows.append({
                "club": club,
                "gp": int(s["gamesPlayed"]), "w": int(s["wins"]),
                "l": int(s["losses"]), "d": int(s["ties"]),
                "pts": int(s["points"]), "gf": int(s["pointsFor"]),
                "ga": int(s["pointsAgainst"]), "gd": int(s["pointDifferential"]),
                "conf": conf,
            })
    return rows


def main():
    try:
        data = fetch_json(URL)
        rows = parse(data)
        if len(rows) < 25:  # partial/empty response — treat as a failed fetch
            raise ValueError(f"only {len(rows)} teams returned (expected 30)")
    except Exception as e:  # network / API / parse failure
        if OUT.exists():
            print(f"WARNING: could not fetch live standings ({e}).")
            print(f"Keeping existing {OUT.name} (last-known data).")
            return
        print(f"ERROR: could not fetch standings and no cached file exists: {e}")
        sys.exit(1)

    if len(rows) != 30:
        print(f"WARNING: expected 30 teams, got {len(rows)}. Writing anyway.")

    rows.sort(key=lambda r: (r["conf"], -r["pts"], -r["gd"]))
    with open(OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        w.writerows(rows)

    now = datetime.now()
    gp = max(r["gp"] for r in rows) if rows else 0
    mn = min(r["gp"] for r in rows) if rows else 0
    # sidecar meta so the site can show an accurate standings "as of" date
    (DATA / "standings_meta.json").write_text(json.dumps({
        "season": SEASON, "minGp": mn, "maxGp": gp,
        "fetched": f"{now.strftime('%B')} {now.day}, {now.year}",
    }, indent=1), encoding="utf-8")
    print(f"Wrote {len(rows)} teams to {OUT.name}  "
          f"(season {SEASON}, up to {gp} games played, fetched {now:%Y-%m-%d %H:%M})")


if __name__ == "__main__":
    main()
