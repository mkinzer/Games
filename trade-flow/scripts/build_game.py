#!/usr/bin/env python3
"""Inline data/countries.json into src/game.template.html to produce index.html.

The game is a single self-contained file on purpose: opening it straight off
the filesystem (file://) has to work, and a browser will not let a file:// page
fetch() a sibling JSON file. So the data is baked in at build time instead.

Usage:  python3 scripts/build_game.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "src" / "game.template.html"
DATA = ROOT / "data" / "countries.json"
OUT = ROOT / "index.html"
PLACEHOLDER = "__COUNTRY_DATA__"

REQUIRED_FIELDS = {"iso2", "iso3", "name", "lat", "lon", "gdpUsd", "gdpYear", "rank"}


def main():
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    countries = payload["countries"]

    if not countries:
        sys.exit("countries.json has no countries")
    for c in countries:
        missing = REQUIRED_FIELDS - c.keys()
        if missing:
            sys.exit(f"{c.get('iso3', '?')} is missing fields: {sorted(missing)}")
    codes = [c["iso3"] for c in countries]
    if len(set(codes)) != len(codes):
        sys.exit("duplicate ISO3 codes in countries.json")

    # Ship only what the game reads, so index.html stays small.
    slim = {
        "topN": payload["topN"],
        "gdpIndicator": payload["gdpIndicator"],
        "countries": [
            {
                "iso2": c["iso2"], "iso3": c["iso3"], "name": c["name"],
                "lat": round(c["lat"], 4), "lon": round(c["lon"], 4),
                "rank": c["rank"], "gdpUsd": round(c["gdpUsd"]),
                "gdpYear": c["gdpYear"],
            }
            for c in countries
        ],
    }

    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        sys.exit(f"{PLACEHOLDER} not found in {TEMPLATE}")

    # separators keep it compact; "</" is escaped so the JSON can never end
    # the <script> block early.
    blob = json.dumps(slim, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    OUT.write_text(template.replace(PLACEHOLDER, blob), encoding="utf-8")

    print(f"wrote {OUT.relative_to(ROOT)} "
          f"({len(slim['countries'])} countries, {OUT.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
