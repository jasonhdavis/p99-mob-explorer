# P99 NPC Inventory Extractor + Analyzer

Goal: Build a local, repeatable dataset of P99 wiki NPC pages and extract structured stats (Level, HP, etc.)
to answer questions like "lowest HP for level" while keeping enough raw data to re-parse later.

We will:
- enumerate NPC pages via MediaWiki category listings (Category:NPCs and/or subcategories)
- fetch raw wikitext for each page
- parse templates into a wide "facts" table + keep the raw wikitext snapshot
- store everything in SQLite for fast querying
- provide a Streamlit UI to filter/search/sort and inspect raw/parsed fields
- export CSV slices for ad-hoc analysis

## Principles
- Avoid browser automation unless needed. Use MediaWiki API for speed + stability.
- Keep raw inputs (wikitext) so parsing rules can evolve without re-downloading everything.
- Separate "ingest" from "parse" from "analyze".
- Be gentle to the wiki (rate limit + caching).

## Data model (SQLite)
Tables:

1) pages
- title (PK)
- pageid
- revision_id
- touched / timestamp (if available)
- wikitext (raw snapshot)
- fetched_at

2) template_kv  (EAV-style, for "pull more structured data than we need")
- title
- template_name
- param_name
- param_value
- normalized_value (optional)
- fetched_at

3) npc_core  (a "best effort" derived view/table for common queries)
- title (PK)
- level_min
- level_max
- hp
- ac
- atk
- zone
- race
- class
- npc_id
- parsed_from_template (which template/strategy matched)
- parse_version
- parsed_at

We will store "template_kv" widely, then derive npc_core from it.

## Extraction strategy
Phase A: Index pages
- Use MediaWiki API list=categorymembers starting from Category:NPCs
- Capture title + pageid (if returned)
- Persist basic page list so we can resume

Phase B: Fetch raw content
- For each title, fetch revisions content:
  action=query&prop=revisions&rvslots=main&rvprop=content|ids|timestamp
- Store wikitext snapshot in pages table
- Respect a request delay (e.g., 150–300ms) and retry with backoff

Phase C: Parse templates
- Use mwparserfromhell to parse wikitext templates
- For every template:
  - store all params into template_kv (title, template_name, param_name, param_value)
- Build a "parser" module that tries multiple known patterns to populate npc_core:
  - template names containing 'npc', 'mob', 'infobox', etc.
  - param keys for level/hp variants (level, lvl, minlevel, maxlevel, hp, hitpoints, etc.)
  - normalize numeric strings (remove commas, handle "??", "270 (est)", etc.)

Phase D: Explore / sift
- Streamlit UI:
  - quick filters: min/max level, hp min/max, zone contains, template contains
  - text search by title
  - sort by computed metrics like hp_per_level (hp / level_min)
  - inspect a row and show:
    - npc_core fields
    - raw template_kv for that title (searchable)
    - raw wikitext snippet (collapsible)

## Deliverables
- /data/p99.sqlite (SQLite DB)
- /exports/npc_core.csv
- /exports/template_kv.csv (optional)
- Streamlit UI: `streamlit run app.py`
- CLI:
  - python -m p99wiki.cli ingest
  - python -m p99wiki.cli parse
  - python -m p99wiki.cli export
  - python -m p99wiki.cli stats (simple summaries)

## Setup
1) Create venv
- python3 -m venv .venv
- source .venv/bin/activate (mac/linux)
- .venv\Scripts\activate (windows)

2) Install deps
- pip install -r requirements.txt

3) Run ingest + parse
- python -m p99wiki.cli ingest --category "Category:NPCs" --limit 0
- python -m p99wiki.cli parse

4) Launch viewer
- streamlit run app.py

## Notes / Edge cases
- Some NPC pages may not include HP or may hide it in prose sections.
- Level ranges may appear (e.g. "12-14"). Store min/max.
- Multiple templates per page: we store all and pick a best match for npc_core.
- Parsing will improve over time; parse_version lets us rebuild npc_core quickly.

## "Lowest HP for level" query examples
- Lowest absolute HP per level:
  SELECT level_min, MIN(hp) FROM npc_core WHERE hp IS NOT NULL GROUP BY level_min;

- Best "squishiest" by hp_per_level:
  SELECT title, level_min, hp, (CAST(hp AS REAL)/level_min) AS hp_per_level
  FROM npc_core
  WHERE hp IS NOT NULL AND level_min IS NOT NULL AND level_min > 0
  ORDER BY hp_per_level ASC
  LIMIT 50;

## Future improvements
- Add zone crawling: link zone pages to find NPCs per zone
- Add wiki "Special:Export" option for faster bulk snapshots
- Add caching of HTTP responses (requests-cache) to speed dev cycles
- Add "diff parser": only re-parse changed revisions

## Project structure
p99-npc-inventory/
  planning.md
  README.md
  requirements.txt
  .gitignore

  data/
    p99.sqlite

  exports/
    npc_core.csv
    template_kv.csv

  p99wiki/
    __init__.py
    cli.py
    config.py
    db.py
    mediawiki.py
    ingest.py
    parse.py
    export.py
    normalize.py

  app.py
