"""Shared position bucketing for the whole project (pipeline + experiments).

One canonical mapping so the site and the experiments can never diverge. If a
position string is encountered that matches no rule, a loud alert is printed to
the terminal (stderr) once per distinct unknown value, so a human notices and
adds a rule instead of it being silently mis-bucketed.
"""
import sys

POS_ORDER = ["Attack", "Midfield", "Defense", "Goalkeeper"]
_UNKNOWN_SEEN = set()


def _alert_unknown(pos):
    key = str(pos).strip()
    if key in _UNKNOWN_SEEN:      # only shout once per distinct value
        return
    _UNKNOWN_SEEN.add(key)
    bar = "!" * 72
    print(f"\n{bar}\n"
          f"!!  ALERT: unrecognized player position {key!r}.\n"
          f"!!  It was bucketed as 'Midfield' by default and may be wrong.\n"
          f"!!  Add a rule for it in code/positions.py (pos_bucket).\n"
          f"{bar}\n", file=sys.stderr, flush=True)


def pos_bucket(pos):
    """Map a granular position to Attack / Midfield / Defense / Goalkeeper."""
    p = str(pos).split("/")[0].strip().lower()
    if "goalkeeper" in p:
        return "Goalkeeper"
    if "back" in p:                                   # center/left/right-back
        return "Defense"
    if "wing" in p or "forward" in p or "attacking mid" in p:
        return "Attack"
    if "midfield" in p:                               # central/defensive/L/R mid
        return "Midfield"
    _alert_unknown(pos)                               # nothing matched -> alert
    return "Midfield"
