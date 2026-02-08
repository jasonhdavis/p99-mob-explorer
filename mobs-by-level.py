import time
import re
import csv
import sqlite3
import requests
import mwparserfromhell

API = "https://wiki.project1999.com/api.php"
CATEGORY = "Category:NPCs"   # big list; you can swap to narrower categories later
SLEEP_SECS = 0.2             # be nice to the wiki

def mediawiki_get(params):
    params = dict(params)
    params["format"] = "json"
    r = requests.get(API, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def iter_category_members(category_title, namespace=0, limit=500):
    cmcontinue = None
    while True:
        params = {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": category_title,
            "cmnamespace": namespace,
            "cmlimit": limit,
        }
        if cmcontinue:
            params["cmcontinue"] = cmcontinue

        data = mediawiki_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            yield m["title"]

        cmcontinue = data.get("continue", {}).get("cmcontinue")
        if not cmcontinue:
            break

def fetch_wikitext(title):
    data = mediawiki_get({
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content",
        "rvslots": "main",
    })
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    revs = page.get("revisions")
    if not revs:
        return None
    return revs[0]["slots"]["main"]["*"]

def normalize_int(value):
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # handle things like "1,234", "270 (est)", "??"
    s = s.replace(",", "")
    m = re.search(r"-?\d+", s)
    return int(m.group(0)) if m else None

def extract_fields(wikitext):
    """
    Tries to extract Level / HP from common NPC templates.
    This is heuristic because wiki templates vary.
    """
    if not wikitext:
        return {}

    code = mwparserfromhell.parse(wikitext)
    templates = code.filter_templates(recursive=True)

    # Common template names you might see; we’ll scan all anyway.
    # You can print template names to tune this.
    level = None
    hp = None
    npc_id = None
    zone = None
    npc_type = None

    for t in templates:
        name = str(t.name).strip().lower()

        # Broadly: any template that looks like an npc/mob infobox
        if any(k in name for k in ["npc", "mob", "infobox", "creature"]):
            # Try common param keys
            for key in ["level", "lvl", "lvl1", "minlevel", "level_range"]:
                if t.has(key) and level is None:
                    level = normalize_int(t.get(key).value)
            for key in ["hp", "hitpoints", "hit_points"]:
                if t.has(key) and hp is None:
                    hp = normalize_int(t.get(key).value)
            for key in ["npc_id", "id"]:
                if t.has(key) and npc_id is None:
                    npc_id = normalize_int(t.get(key).value)
            for key in ["zone", "location", "loc", "region"]:
                if t.has(key) and zone is None:
                    zone = str(t.get(key).value).strip()
            for key in ["race", "class", "type"]:
                if t.has(key) and npc_type is None:
                    npc_type = str(t.get(key).value).strip()

        # Some pages don’t use obvious template names but still have params
        # If we’ve already got level+hp, bail early.
        if level is not None and hp is not None:
            break

    return {
        "level": level,
        "hp": hp,
        "npc_id": npc_id,
        "zone": zone,
        "npc_type": npc_type,
    }

def init_db(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS npc_stats (
            title TEXT PRIMARY KEY,
            level INTEGER,
            hp INTEGER,
            npc_id INTEGER,
            zone TEXT,
            npc_type TEXT,
            fetched_at TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()

def upsert(conn, title, fields):
    conn.execute("""
        INSERT INTO npc_stats (title, level, hp, npc_id, zone, npc_type)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(title) DO UPDATE SET
            level=excluded.level,
            hp=excluded.hp,
            npc_id=excluded.npc_id,
            zone=excluded.zone,
            npc_type=excluded.npc_type,
            fetched_at=datetime('now')
    """, (
        title,
        fields.get("level"),
        fields.get("hp"),
        fields.get("npc_id"),
        fields.get("zone"),
        fields.get("npc_type"),
    ))
    conn.commit()

def export_csv(conn, path="npc_stats.csv"):
    cur = conn.execute("SELECT title, level, hp, npc_id, zone, npc_type FROM npc_stats")
    cols = [d[0] for d in cur.description]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(cols)
        w.writerows(cur.fetchall())

def main(db_path="p99_npcs.sqlite"):
    conn = sqlite3.connect(db_path)
    init_db(conn)

    count = 0
    for title in iter_category_members(CATEGORY):
        # skip category pages, talk pages, etc. (namespace filter should already help)
        wikitext = fetch_wikitext(title)
        fields = extract_fields(wikitext)

        upsert(conn, title, fields)
        count += 1

        if count % 250 == 0:
            print(f"Processed {count} pages... (latest: {title})")

        time.sleep(SLEEP_SECS)

    export_csv(conn)
    print(f"Done. SQLite: {db_path}  CSV: npc_stats.csv")

if __name__ == "__main__":
    main()
