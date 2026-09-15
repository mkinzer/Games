# Trade Flow

A [Tradle](https://oec.world/tradle)-inspired daily guessing game. You are shown a
treemap of one country's trade composition and have six guesses to name it. Each
wrong guess tells you how far away you are, which direction to head, and how close
you got.

**What is different from Tradle:** Tradle only ever shows one chart, exports by
product. Trade Flow draws on **four**, and a banner above the treemap always says
which one you are looking at. The puzzle pool is **every economy with more than a
million people** — 154 of them — rather than every country in the world.

```
┌───────────────────────────────────────────────────────────────┐
│  EXPORTS  BY DESTINATION   Where this country's exports go.   │
└───────────────────────────────────────────────────────────────┘
```

| Chart | Reads as |
| --- | --- |
| Exports by product | What it sells |
| Imports by product | What it buys |
| Exports by destination | Who it sells to |
| Imports by origin | Who it buys from |

The four are genuinely different puzzles. Export treemaps are dominated by whatever
a country is unusually good at or happens to sit on top of — Chilean copper,
Bangladeshi garments, Saudi crude. Import treemaps look far more alike across
countries, because most places buy the same things (machines, cars, refined
petroleum, pharmaceuticals) in proportions set mainly by how rich and how large
they are; the tell is usually in what is *missing* or oddly large.

The partner charts swap industry for geography. Trade is overwhelmingly regional, so
a destination treemap is mostly a map of who a country is next to — which makes it
easy to place a continent and hard to pick the country within it. The interesting
cases are the ones that break the gravity model: a former colony still shipping to
its old metropole, a landlocked country routed through one neighbour, a sanctioned
economy with a conspicuously short partner list.

## Playing

Open `index.html` in a browser. That is the whole thing — no server, no build step,
no dependencies. The file is self-contained and works over `file://`.

- A new puzzle appears each day, the same for any copy of the file on that date.
- Over any 616-day span each of the 154 countries appears exactly four times, once
  per chart. Nothing repeats inside that window — about twenty months.
- Guesses accept country names, ISO codes (`JPN`, `DE`), and common alternates
  (`UK`, `Turkey`, `Holland`, `Ivory Coast`).
- Click any distance to switch between kilometres and miles.
- Progress, statistics, and your settings are kept in `localStorage`, so they stay
  on your machine and nowhere else.

The gear icon opens **Settings**: theme, distance unit, and **practice mode**.

Practice mode is a switch rather than a one-off button. With it on you get random
puzzles and a *New puzzle* button, and a banner keeps it obvious you are off the
daily. Nothing played in practice touches your statistics, and today's puzzle is
held exactly where you left it — turn practice off and your daily game comes back
with its guesses intact. The setting persists across reloads.

Statistics are broken out by chart, so you can see which of the four you actually
read well. (In my experience: products yes, partners no.)

## Where the data comes from

Nothing in this game is hand-entered or estimated. Every number traces to a public
dataset.

**The treemaps** are live embeds from the
[Observatory of Economic Complexity](https://oec.world/), the same source Tradle
uses, under the HS92 classification for 2023. The game builds an OEC URL of the form
`.../tree_map/hs92/{export|import}/{iso3}/{partner}/{product}/2023/` and shows it in
an iframe. OEC breaks out whichever of the partner and product slots reads `show`,
which is what gives the four charts:

```
/export/can/all/show/2023/   what Canada exports    (by product)
/export/can/show/all/2023/   where Canada exports   (by destination)
/import/can/all/show/2023/   what Canada imports    (by product)
/import/can/show/all/2023/   where Canada imports   (by origin)
```

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
| Dependency vs. state (`is_independent`) | [datasets/country-codes](https://github.com/datasets/country-codes) |
| Population (`SP.POP.TOTL`) | World Bank, packaged by [datasets/population](https://github.com/datasets/population) |

Countries are ranked by nominal GDP in current US$, preferring 2023 and falling back
to the most recent year since 2018 where 2023 is missing. The cutoff at #160 is
Guinea-Bissau (~$2.0B). Four countries are ranked on a pre-2023 figure because the
World Bank has nothing newer: Qatar (2022), Cuba (2020), Yemen (2018), Lebanon
(2022). Each country's GDP year is shown in the reveal panel.

### The population floor

`POPULATION_FLOOR` in `scripts/build_data.py` admits only economies with more than a
million people. Below that line the game stops being a puzzle: the small island
economies — Barbados, Maldives, Fiji, the Bahamas, Guyana — have interchangeable
treemaps of tourism and re-exported fuel, and sit close enough together that the
distance and direction hints cannot separate them. The European microstates are the
same problem in miniature.

The floor costs some real economies that happen to be small. **Luxembourg**
(0.68M, $86B), **Macao** (0.69M), **Iceland** (0.39M), **Malta** (0.57M) and
**Brunei** (0.46M) all fall below it. Lower `POPULATION_FLOOR` to get them back.

A population rule alone does not settle difficulty, though. It removes the island
cluster but leaves — and, by ranking deeper, extends — a tail of small African
economies: Guinea-Bissau, Lesotho, The Gambia, the Central African Republic,
Burundi, Sierra Leone, Timor-Leste. Those read much alike too. If those days grate,
set `TOP_N` to a number and the poorest tail is trimmed as well; it is `None` by
default, so the population floor alone defines the pool.

### Dependencies are filtered out

A plain GDP ranking is not a list of countries. Ranked deep enough, the World Bank's
figures pull in Puerto Rico, Guam, Bermuda, the Cayman Islands, the Isle of Man and
New Caledonia — none of which are countries, and none of which have their own OEC
treemap, because their trade is reported through the parent state. They would be
blank puzzles. This filter runs independently of the population floor.

The filter that matters for a trade game is not sovereignty but whether a place is a
**separate customs territory with its own trade reporting**. That is
`is_independent == "Yes"` from the ISO dataset, plus three exceptions listed in
`SEPARATE_CUSTOMS_TERRITORIES`: Hong Kong, Macao and the Palestinian Territories,
which report to UN Comtrade in their own right and have their own OEC profiles. Hong
Kong alone justifies drawing the distinction — it is the world's 39th largest economy
and one of its great entrepôts, and a sovereignty test would throw it out.

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

104 assertions driven through a real headless Chromium against `index.html` as a
player would see it: the distance and bearing maths against known reference values,
proximity and share-square parity with Tradle's formulas, the four OEC chart URLs,
the 616-day rotation covering every country-and-chart pair exactly once, input
parsing, a full winning and
losing game, persistence across reload, statistics, settings (theme, units, and
practice mode round-tripping without losing the daily game), and layout at a 380px
viewport. OEC is stubbed out — the suite tests this game, not their CDN.

Set `CHROMIUM_PATH` if Playwright cannot find a browser.

## Credit and licence

Mechanics follow [Tradle](https://github.com/alexandersimoes/tradle) by Alexander
Simoes, itself built on [Worldle](https://github.com/teuteuf/worldle) by teuteuf,
both MIT-licensed. The proximity percentage and the emoji share squares deliberately
use their formulas so results are comparable. The code here is a fresh
implementation; no Tradle source is copied.

Trade data © the Observatory of Economic Complexity. GDP data © World Bank
(CC BY 4.0).
