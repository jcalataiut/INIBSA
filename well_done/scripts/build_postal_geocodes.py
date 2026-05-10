import argparse
from pathlib import Path

import pandas as pd
import pgeocode


def normalize_postal_code(value) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return f"{int(float(text)):05d}"
    except (TypeError, ValueError):
        digits = "".join(ch for ch in text if ch.isdigit())
        if not digits:
            return None
        return digits[:5].zfill(5)


def main():
    parser = argparse.ArgumentParser(description="Genera un lookup local de codis postals d'Espanya.")
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="Arrel del projecte",
    )
    args = parser.parse_args()

    root = args.root
    source_files = [
        root / "data" / "master_commodities.csv",
        root / "data" / "master_technicals.csv",
    ]
    out_path = root / "data" / "postal_geocodes_es.csv"

    postal_codes: set[str] = set()
    for source in source_files:
        if not source.exists():
            continue
        df = pd.read_csv(source, usecols=["Cod_Postal"], low_memory=False)
        for value in df["Cod_Postal"]:
            code = normalize_postal_code(value)
            if code and code != "00000":
                postal_codes.add(code)

    nomi = pgeocode.Nominatim("es")
    rows = []
    for code in sorted(postal_codes):
        result = nomi.query_postal_code(code)
        if result is None or pd.isna(result.latitude) or pd.isna(result.longitude):
            continue
        rows.append(
            {
                "cod_postal": code,
                "city": str(result.place_name).strip() if not pd.isna(result.place_name) else "",
                "latitude": float(result.latitude),
                "longitude": float(result.longitude),
            }
        )

    out_df = pd.DataFrame(rows).drop_duplicates(subset=["cod_postal"]).sort_values("cod_postal")
    out_df.to_csv(out_path, index=False)
    print(f"Lookup generat: {out_path} ({len(out_df):,} codis postals)")


if __name__ == "__main__":
    main()
