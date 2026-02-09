from mediawiki import iter_category_members, fetch_wikitext

def ingest_category(conn, category: str, max_pages: int = 0):
    """
    max_pages=0 means no limit.
    """
    cur = conn.cursor()
    count = 0

    for m in iter_category_members(category):
        title = m["title"]
        
        # Check if we already have this page with a wikitext
        cur.execute("SELECT revision_id FROM pages WHERE title = ? AND wikitext IS NOT NULL AND wikitext != ''", (title,))
        if cur.fetchone():
            count += 1
            if count % 250 == 0:
                print(f"[ingest] skipping {title} (already have it)")
            continue

        payload = fetch_wikitext(title)

        cur.execute("""
            INSERT INTO pages (title, pageid, revision_id, revision_ts, wikitext)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(title) DO UPDATE SET
                pageid=excluded.pageid,
                revision_id=excluded.revision_id,
                revision_ts=excluded.revision_ts,
                wikitext=excluded.wikitext,
                fetched_at=datetime('now')
        """, (payload["title"], payload["pageid"], payload["revision_id"], payload["revision_ts"], payload["wikitext"]))
        conn.commit()

        count += 1
        if count % 250 == 0:
            print(f"[ingest] {count} pages… latest={title}")

        if max_pages and count >= max_pages:
            break

    print(f"[ingest] done: {count} pages")
