"""Run the full MLS compensation pipeline end to end.

Executes each stage in order, from the source PDF to the website's data file.
Every script resolves its own paths from the project root, so this works no
matter what directory you launch it from:

    python main.py

Pipeline:
  1. extract_salaries.py  PDF  -> data/mls_salaries_2026.csv
  2. fetch_standings.py   ESPN API (live) -> data/standings_2026.csv
  3. analysis.py          csv  -> console summary + data/charts/01-04
  4. efficiency.py        csv + data/standings_2026.csv
                               -> data/efficiency_2026.csv + data/charts/05-07
  5. export_web_data.py        -> web/site_data.js  (consumed by web/index.html)

Stage 2 pulls the latest 2026 wins/losses from ESPN each run, so re-running
this refreshes the season-to-date performance. It falls back to the existing
standings file if the network is unavailable.
"""
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent / "code"
STAGES = [
    "extract_salaries.py",
    "fetch_standings.py",
    "analysis.py",
    "efficiency.py",
    "export_web_data.py",
]


def main():
    failed = None
    try:
        for i, script in enumerate(STAGES, 1):
            print(f"\n{'#' * 70}\n#  [{i}/{len(STAGES)}]  {script}\n{'#' * 70}")
            subprocess.run([sys.executable, str(CODE / script)], check=True)
        print("\nPipeline complete. Open web/index.html to view the site.")
    except subprocess.CalledProcessError as e:
        failed = e
        print(f"\n!!! Stage failed: {Path(e.cmd[-1]).name} "
              f"(exit code {e.returncode}). See the output above.")
    finally:
        # Keep the window open so the status can be reviewed (e.g. when the
        # script is double-clicked). Skipped in non-interactive/CI runs, and a
        # closed/redirected stdin (EOF) just proceeds instead of crashing.
        if sys.stdin and sys.stdin.isatty():
            try:
                input("\nPress Enter to exit...")
            except (EOFError, KeyboardInterrupt):
                pass
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
