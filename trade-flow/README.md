# Trade Flow

A [Tradle](https://oec.world/tradle)-inspired daily guessing game. You are shown a
treemap of one country's trade composition and have six guesses to name it. Each
wrong guess tells you how far away you are, which direction to head, and how close
you got.

**What is different from Tradle:** Tradle only ever shows exports. Trade Flow shows
**both imports and exports**, and a banner above the treemap always tells you which
one you are looking at. The puzzle pool is the **120 largest economies** rather than
every country in the world.

```
┌──────────────────────────────────────────────┐
│   IMPORTS    What this country buys, 2023.   │
└──────────────────────────────────────────────┘
```

Reading a country's imports is a genuinely different exercise from reading its
exports. Export treemaps are dominated by whatever a country is unusually good at
or happens to sit on top of — Chilean copper, Bangladeshi garments, Saudi crude.
Import treemaps look far more alike across countries, because most places buy the
same things (machines, cars, refined petroleum, pharmaceuticals) in proportions set
mainly by how rich and how large they are. The tell is usually in what is *missing*
or oddly large: an oil producer importing refined petroleum, a country importing
almost no food, an entrepôt whose imports mirror its exports.

## Playing

Open `index.html` in a browser. That is the whole thing — no server, no build step,
no dependencies. The file is self-contained and works over `file://`.

- A new puzzle appears each day, the same for any copy of the file on that date.
- Over any 240-day span each of the 120 countries appears exactly twice: once with
  its exports, once with its imports. Nothing repeats inside that window.
- Guesses accept country names, ISO codes (`JPN`, `DE`), and common alternates
  (`UK`, `Turkey`, `Holland`, `Ivory Coast`).
- Click any distance to switch between kilometres and miles.
- Progress, statistics, and your theme and distance-unit preference are kept in
  `localStorage`, so they stay on your machine and nowhere else.
- **Practice** plays an off-schedule random puzzle. Practice rounds are never
  counted in your statistics.

Statistics are broken out by flow, so you can see whether you read imports as well
as you read exports. (In my experience: no.)

## Where the data comes from

Nothing in this game is hand-entered or estimated. Every number traces to a public
dataset.

**The treemaps** are live embeds from the
[Observatory of Economic Complexity](https://oec.world/), the same source Tradle
uses, under the HS92 classification for 2023. The game builds an OEC URL of the form
`.../tree_map/hs92/{export|import}/{iso3}/all/show/2023/` and shows it in an iframe.
This means the treemap always reflects OEC's current data rather than a snapshot
that silently goes stale — but it also means **the treemap needs an internet
connection**, and if OEC changes its embed URLs the picture will stop loading. A
link under the treemap opens the same view directly on OEC if the embed fails.

**The country list** is built by `scripts/build_data.py` from three public sources:

| Field | Source |
| --- | --- |
| GDP, current US$ (`NY.GDP.MKTP.CD`) | World Bank, packaged by [datasets/gdp](https://github.com/datasets/gdp) |
| ISO 3166-1 alpha-2 / alpha-3 codes | [datasets/country-codes](https://github.com/datasets/country-codes) |
| Country centroids (lat/lon) | [Google Public Data canonical country list](https://github.com/google/dspl) |

Countries are ranked by nominal GDP in current US$, preferring 2023 and falling back
to the most recent year since 2018 where 2023 is missing. The cutoff at #120 is Mali
(~$21B). Four countries in the list are ranked on a pre-2023 figure because the World
Bank has nothing newer: Qatar (2022), Cuba (2020), Lebanon (2022), Yemen (2018). Each
country's GDP year is shown in the reveal panel.

### Known coverage gaps

**Taiwan is not in the list.** It is a top-25 economy and one of the world's most
important traders, but it is not a World Bank member and the World Bank publishes no
GDP figure for it, so the ranking cannot see it. Cuba, Venezuela, Syria and North
Korea are similarly under- or un-covered.

`build_data.py` has an `EXTRA_COUNTRIES` list for exactly this case. It ships empty
on purpose — adding an entry means sourcing the GDP figure yourself (IMF World
Economic Outlook, or Taiwan's DGBAS) so the provenance stays honest. The comment
above it has a ready-to-fill Taiwan entry with the correct coordinates. Use nominal
GDP in current US$ or it will sort against the World Bank figures incorrectly.

Ranking by nominal GDP rather than PPP is itself a choice, and it is the one that
matters here: trade is invoiced at market exchange rates, so nominal GDP is the
right scale for a trade game. A PPP ranking would pull in a noticeably different
set of countries at the margin.

## Rebuilding

```sh
python3 scripts/build_data.py     # refresh data/countries.json from source
python3 scripts/build_game.py     # inline that data into index.html
```

`index.html` is generated. Edit `src/game.template.html` and re-run
`build_game.py` — edits made directly to `index.html` are overwritten. The data is
baked into the HTML rather than fetched at runtime because browsers will not let a
`file://` page `fetch()` a sibling JSON file, and playing by double-clicking the
file was the point.

Both scripts need only Python 3 and network access to `raw.githubusercontent.com`.

## Tests

```sh
cd tests && npm install && npm test
```

72 assertions driven through a real headless Chromium against `index.html` as a
player would see it: the distance and bearing maths against known reference values,
proximity and share-square parity with Tradle's formulas, the 240-day rotation
covering every country-and-flow pair exactly once, input parsing, a full winning and
losing game, persistence across reload, statistics, practice mode, unit switching,
and layout at a 380px viewport. OEC is stubbed out — the suite tests this game, not their CDN.

Set `CHROMIUM_PATH` if Playwright cannot find a browser.

## Credit and licence

Mechanics follow [Tradle](https://github.com/alexandersimoes/tradle) by Alexander
Simoes, itself built on [Worldle](https://github.com/teuteuf/worldle) by teuteuf,
both MIT-licensed. The proximity percentage and the emoji share squares deliberately
use their formulas so results are comparable. The code here is a fresh
implementation; no Tradle source is copied.

Trade data © the Observatory of Economic Complexity. GDP data © World Bank
(CC BY 4.0).
