"""Extract the MLSPA salary table from the PDF into a clean CSV.

The PDF (Spring-2026-MLSPA-Salary-Guide) has one table repeated across pages
with columns: First Name, Last Name, Club, Position, Base Salary, Guaranteed Comp.
"""
import re
from pathlib import Path
import pandas as pd
import pdfplumber

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
PDF = DATA / "Spring-2026-MLSPA-Salary-Guide.pdf"
OUT = DATA / "mls_salaries_2026.csv"

COLUMNS = [
    "first_name", "last_name", "club", "position",
    "base_salary", "guaranteed_comp",
]


def money_to_float(s):
    """'$1,234.56' -> 1234.56 ; blanks/dashes -> NaN."""
    if s is None:
        return None
    s = s.strip()
    if s in ("", "-", "N/A", "TBD"):
        return None
    return float(re.sub(r"[^0-9.]", "", s))


def is_header(row):
    return (row[0] or "").strip().lower() == "first name"


def main():
    records = []
    with pdfplumber.open(PDF) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table:
                continue
            for row in table:
                if row is None or is_header(row) or not any(row):
                    continue
                # pad/trim to 6 cells
                row = (row + [None] * 6)[:6]
                records.append(row)

    df = pd.DataFrame(records, columns=COLUMNS)

    # clean text: strip, drop the U+FFFD replacement char left by bad glyph maps
    for c in ["first_name", "last_name", "club", "position"]:
        df[c] = df[c].astype(str).str.replace("�", "", regex=False).str.strip()

    df["base_salary"] = df["base_salary"].map(money_to_float)
    df["guaranteed_comp"] = df["guaranteed_comp"].map(money_to_float)

    df = df.dropna(subset=["guaranteed_comp"]).reset_index(drop=True)
    df.to_csv(OUT, index=False, encoding="utf-8-sig")
    print(f"Wrote {len(df)} players across {df['club'].nunique()} clubs -> {OUT}")
    return df


if __name__ == "__main__":
    main()
