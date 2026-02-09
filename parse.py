import mwparserfromhell
from normalize import normalize_int, parse_level_range
from config import PARSE_VERSION

NPCISH_TEMPLATE_HINTS = ("npc", "mob", "infobox", "creature")

LEVEL_KEYS = ("level", "lvl", "minlevel", "maxlevel", "level_range")
HP_KEYS = ("hp", "hitpoints", "hit_points")
AC_KEYS = ("ac", "armorclass", "armor_class")
ATK_KEYS = ("atk", "attack", "attackrating")
ZONE_KEYS = ("zone", "location", "loc", "region")
RACE_KEYS = ("race",)
CLASS_KEYS = ("class",)
ID_KEYS = ("npc_id", "id")

def parse_all_templates(wikitext: str):
    code = mwparserfromhell.parse(wikitext or "")
    for t in code.filter_templates(recursive=True):
        name = str(t.name).strip()
        for p in t.params:
            yield (name, str(p.name).strip(), str(p.value).strip())

def pick_npc_core_from_templates(template_rows):
    """
    template_rows: iterable of (template_name, param_name, param_value)
    Returns dict suitable for npc_core.
    We scan for the most npc-ish template first; fall back to anything containing level/hp.
    """
    # Group by template
    by_t = {}
    for tn, pn, pv in template_rows:
        by_t.setdefault(tn, []).append((pn, pv))

    # Rank templates
    ranked = sorted(
        by_t.items(),
        key=lambda kv: (
            0 if any(h in kv[0].lower() for h in NPCISH_TEMPLATE_HINTS) else 1,
            -sum(1 for (pn, _) in kv[1] if pn.strip().lower() in LEVEL_KEYS + HP_KEYS),
        )
    )

    best = None
    best_name = None
    for tn, params in ranked:
        lower_map = {pn.strip().lower(): pv for pn, pv in params}
        has_level = any(k in lower_map for k in LEVEL_KEYS)
        has_hp = any(k in lower_map for k in HP_KEYS)
        if has_level or has_hp:
            best = lower_map
            best_name = tn
            break

    if not best:
        return {}

    # Level
    lvl_min = lvl_max = None
    for k in LEVEL_KEYS:
        if k in best:
            if k in ("minlevel", "maxlevel"):
                # if both exist, use them; otherwise set one
                if k == "minlevel":
                    lvl_min = normalize_int(best[k])
                else:
                    lvl_max = normalize_int(best[k])
            else:
                a, b = parse_level_range(best[k])
                lvl_min, lvl_max = a, b
            break

    if lvl_min is not None and lvl_max is None:
        lvl_max = lvl_min
    if lvl_max is not None and lvl_min is None:
        lvl_min = lvl_max

    # HP
    hp = None
    for k in HP_KEYS:
        if k in best:
            hp = normalize_int(best[k])
            break

    ac = None
    for k in AC_KEYS:
        if k in best:
            ac = normalize_int(best[k])
            break

    atk = None
    for k in ATK_KEYS:
        if k in best:
            atk = normalize_int(best[k])
            break

    zone = None
    for k in ZONE_KEYS:
        if k in best:
            zone = str(best[k]).strip()
            break

    race = None
    for k in RACE_KEYS:
        if k in best:
            race = str(best[k]).strip()
            break

    cls = None
    for k in CLASS_KEYS:
        if k in best:
            cls = str(best[k]).strip()
            break

    npc_id = None
    for k in ID_KEYS:
        if k in best:
            npc_id = normalize_int(best[k])
            break

    return {
        "level_min": lvl_min,
        "level_max": lvl_max,
        "hp": hp,
        "ac": ac,
        "atk": atk,
        "zone": zone,
        "race": race,
        "class": cls,
        "npc_id": npc_id,
        "parsed_from_template": best_name,
        "parse_version": PARSE_VERSION,
    }

def parse_pages(conn):
    cur = conn.cursor()

    rows = cur.execute("SELECT title, wikitext FROM pages WHERE wikitext IS NOT NULL AND wikitext != ''").fetchall()
    print(f"[parse] parsing {len(rows)} pages")

    for i, (title, wikitext) in enumerate(rows, start=1):
        # wipe old kv rows for title
        cur.execute("DELETE FROM template_kv WHERE title = ?", (title,))

        template_rows = list(parse_all_templates(wikitext))
        cur.executemany(
            "INSERT INTO template_kv (title, template_name, param_name, param_value) VALUES (?, ?, ?, ?)",
            [(title, tn, pn, pv) for (tn, pn, pv) in template_rows]
        )

        core = pick_npc_core_from_templates(template_rows)

        cur.execute("""
            INSERT INTO npc_core (title, level_min, level_max, hp, ac, atk, zone, race, class, npc_id, parsed_from_template, parse_version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                level_min=excluded.level_min,
                level_max=excluded.level_max,
                hp=excluded.hp,
                ac=excluded.ac,
                atk=excluded.atk,
                zone=excluded.zone,
                race=excluded.race,
                class=excluded.class,
                npc_id=excluded.npc_id,
                parsed_from_template=excluded.parsed_from_template,
                parse_version=excluded.parse_version,
                parsed_at=datetime('now')
        """, (
            title,
            core.get("level_min"),
            core.get("level_max"),
            core.get("hp"),
            core.get("ac"),
            core.get("atk"),
            core.get("zone"),
            core.get("race"),
            core.get("class"),
            core.get("npc_id"),
            core.get("parsed_from_template"),
            core.get("parse_version"),
        ))

        if i % 500 == 0:
            conn.commit()
            print(f"[parse] {i}/{len(rows)}… latest={title}")

    conn.commit()
    print("[parse] done")
