#!/usr/bin/env python3
"""Build the country dataset for Trade Routes (the 120 largest economies).

Every field is sourced from a public dataset; nothing is hand-entered.

Sources (all fetched at build time, all public):
  * GDP, current US$        - World Bank indicator NY.GDP.MKTP.CD, packaged by
                              https://github.com/datasets/gdp
  * ISO 3166-1 alpha-2/3    - https://github.com/datasets/country-codes
  * Country centroids       - Google Public Data canonical country list,
                              https://github.com/google/dspl

Usage:  python3 scripts/build_data.py [--out data/countries.json]
"""

import argparse
import csv
import io
import json
import sys
import urllib.request

GDP_URL = "https://raw.githubusercontent.com/datasets/gdp/main/data/gdp.csv"
ISO_URL = "https://raw.githubusercontent.com/datasets/country-codes/main/data/country-codes.csv"
LATLON_URL = "https://raw.githubusercontent.com/google/dspl/master/samples/google/canonical/countries.csv"

TOP_N = 160

# The World Bank publishes GDP for dependencies as well as states, and a plain
# GDP ranking pulls in Guam, Bermuda, the Isle of Man and friends. They are not
# countries, and their trade is reported through the parent state, so OEC has no
# separate treemap for them - they would be blank puzzles.
#
# The filter that matters for a trade game is not sovereignty but whether the
# place is a separate customs territory with its own trade reporting. That is
# `is_independent == "Yes"` plus these three, which report to UN Comtrade in
# their own right and have their own OEC profiles. Hong Kong alone makes the
# distinction worth drawing: it is a top-40 economy and one of the world's great
# entrepots, and a sovereignty test would throw it out.
SEPARATE_CUSTOMS_TERRITORIES = {"HKG", "MAC", "PSE"}
PREFERRED_YEAR = 2023
EARLIEST_FALLBACK_YEAR = 2018

# Display names that read better on a game board than the World Bank's
# official long forms. Only ever cosmetic - codes and numbers are untouched.
DISPLAY_NAMES = {
    "KOR": "South Korea",
    "PRK": "North Korea",
    "RUS": "Russia",
    "IRN": "Iran",
    "VEN": "Venezuela",
    "SYR": "Syria",
    "EGY": "Egypt",
    "VNM": "Vietnam",
    "LAO": "Laos",
    "BRN": "Brunei",
    "CIV": "Cote d'Ivoire",
    "COD": "DR Congo",
    "COG": "Republic of the Congo",
    "HKG": "Hong Kong",
    "MAC": "Macao",
    "SVK": "Slovakia",
    "CZE": "Czechia",
    "MDA": "Moldova",
    "TZA": "Tanzania",
    "BOL": "Bolivia",
    "GMB": "The Gambia",
    "BHS": "The Bahamas",
    "KGZ": "Kyrgyzstan",
    "MKD": "North Macedonia",
    "TUR": "Turkiye",
    "USA": "United States",
    "GBR": "United Kingdom",
    "ARE": "United Arab Emirates",
    "SAU": "Saudi Arabia",
    "CAF": "Central African Republic",
    "DOM": "Dominican Republic",
    "STP": "Sao Tome and Principe",
    "SSD": "South Sudan",
    "TLS": "Timor-Leste",
    "FSM": "Micronesia",
    "YEM": "Yemen",
}


# Economies the World Bank does not publish GDP for, so they can never appear in
# the ranking above no matter how large they are. Taiwan is the big one: it is a
# top-25 economy and a major trader, but it is not a World Bank member.
#
# Nothing is invented here. To include one, look the figure up yourself (IMF World
# Economic Outlook, or Taiwan's own DGBAS) and add an entry, e.g.:
#
#     {"iso2": "TW", "iso3": "TWN", "name": "Taiwan",
#      "lat": 23.697810, "lon": 120.960515,
#      "region": "Asia", "subregion": "Eastern Asia",
#      "gdpUsd": 0, "gdpYear": 2023, "source": "IMF WEO April 2025"},
#
# It is ranked alongside the World Bank figures, so use nominal GDP in current
# US$ or the ordering will be wrong.
EXTRA_COUNTRIES: list = []


def fetch(url):
    sys.stderr.write(f"fetching {url}\n")
    with urllib.request.urlopen(url, timeout=120) as resp:
        return resp.read().decode("utf-8-sig")


def load_iso_map(text):
    """alpha-3 -> {alpha2, region, subregion, official name}."""
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        a3 = (row.get("ISO3166-1-Alpha-3") or "").strip()
        a2 = (row.get("ISO3166-1-Alpha-2") or "").strip()
        if not a3 or not a2:
            continue
        out[a3] = {
            "alpha2": a2,
            "region": (row.get("Region Name") or "").strip(),
            "subregion": (row.get("Sub-region Name") or "").strip(),
            "independent": (row.get("is_independent") or "").strip() == "Yes",
        }
    return out


def load_latlon(text):
    """alpha-2 -> (lat, lon, name)."""
    out = {}
    for row in csv.DictReader(io.StringIO(text)):
        code = (row.get("country") or "").strip()
        try:
            lat = float(row["latitude"])
            lon = float(row["longitude"])
        except (KeyError, TypeError, ValueError):
            continue
        out[code] = (lat, lon, (row.get("name") or "").strip())
    return out


def load_gdp(text):
    """alpha-3 -> (year, value, world-bank name), preferring PREFERRED_YEAR.

    The World Bank file mixes countries with aggregates ("World", "Euro area",
    ...). Aggregates are dropped later by requiring a real ISO 3166-1 code.
    """
    by_country = {}
    for row in csv.DictReader(io.StringIO(text)):
        code = (row.get("Country Code") or "").strip()
        raw = (row.get("Value") or "").strip()
        try:
            year = int(row["Year"])
            value = float(raw)
        except (KeyError, TypeError, ValueError):
            continue
        if value <= 0 or year < EARLIEST_FALLBACK_YEAR:
            continue
        by_country.setdefault(code, {})[year] = (value, (row.get("Country Name") or "").strip())

    out = {}
    for code, years in by_country.items():
        year = PREFERRED_YEAR if PREFERRED_YEAR in years else max(years)
        value, name = years[year]
        out[code] = (year, value, name)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/countries.json")
    args = ap.parse_args()

    iso = load_iso_map(fetch(ISO_URL))
    latlon = load_latlon(fetch(LATLON_URL))
    gdp = load_gdp(fetch(GDP_URL))

    candidates = []
    skipped = []
    dropped_dependencies = []
    for a3, (year, value, wb_name) in gdp.items():
        meta = iso.get(a3)
        if meta is None:
            continue  # an aggregate such as "World" or "Euro area"
        if not meta["independent"] and a3 not in SEPARATE_CUSTOMS_TERRITORIES:
            dropped_dependencies.append((a3, wb_name))
            continue
        coords = latlon.get(meta["alpha2"])
        if coords is None:
            skipped.append((a3, wb_name, "no centroid"))
            continue
        lat, lon, canonical_name = coords
        candidates.append(
            {
                "iso2": meta["alpha2"],
                "iso3": a3,
                "name": DISPLAY_NAMES.get(a3, canonical_name or wb_name),
                "lat": lat,
                "lon": lon,
                "region": meta["region"],
                "subregion": meta["subregion"],
                "gdpUsd": value,
                "gdpYear": year,
            }
        )

    for extra in EXTRA_COUNTRIES:
        if not extra.get("gdpUsd"):
            sys.exit(f"EXTRA_COUNTRIES entry {extra.get('iso3')} needs a real gdpUsd")
        candidates.append(dict(extra))

    candidates.sort(key=lambda c: c["gdpUsd"], reverse=True)
    top = candidates[:TOP_N]
    for rank, c in enumerate(top, start=1):
        c["rank"] = rank

    payload = {
        "generatedBy": "scripts/build_data.py",
        "topN": TOP_N,
        "gdpIndicator": "NY.GDP.MKTP.CD (GDP, current US$)",
        "gdpPreferredYear": PREFERRED_YEAR,
        "sources": {
            "gdp": GDP_URL,
            "isoCodes": ISO_URL,
            "centroids": LATLON_URL,
        },
        "countries": top,
    }

    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.write("\n")

    sys.stderr.write(f"\nwrote {args.out}: {len(top)} countries\n")
    sys.stderr.write(f"cutoff: #{TOP_N} {top[-1]['name']} "
                     f"(${top[-1]['gdpUsd']/1e9:,.1f}B, {top[-1]['gdpYear']})\n")
    stale = sorted({c["gdpYear"] for c in top})
    sys.stderr.write(f"gdp years present: {stale}\n")
    if skipped:
        sys.stderr.write(f"skipped for missing centroid: {skipped}\n")
    kept = sorted(SEPARATE_CUSTOMS_TERRITORIES & {c["iso3"] for c in top})
    sys.stderr.write(f"kept as separate customs territories: {kept}\n")
    big = [n for c, n in dropped_dependencies if c in
           {"PRI", "NCL", "IMN", "BMU", "GUM", "CYM", "ABW", "GRL", "FRO"}]
    sys.stderr.write(f"dropped as dependencies (sample): {big}\n")


if __name__ == "__main__":
    main()
