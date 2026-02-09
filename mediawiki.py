import time
import requests
from config import API_URL, USER_AGENT, REQUEST_DELAY_SECS

SESSION = requests.Session()
SESSION.headers.update({"User-Agent": USER_AGENT})

def api_get(params: dict) -> dict:
    params = dict(params)
    params["format"] = "json"
    r = SESSION.get(API_URL, params=params, timeout=30)
    r.raise_for_status()
    time.sleep(REQUEST_DELAY_SECS)
    return r.json()

def iter_category_members(category_title: str, namespace: int = 0, limit: int = 500):
    cmcontinue = None
    print(f"[mediawiki] iter_category_members: {category_title}")
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

        data = api_get(params)
        members = data.get("query", {}).get("categorymembers", [])
        for m in members:
            yield {
                "title": m.get("title"),
                "pageid": m.get("pageid"),
            }

        cmcontinue = data.get("query-continue", {}).get("categorymembers", {}).get("cmcontinue")
        if not cmcontinue:
            break

def fetch_wikitext(title: str) -> dict:
    data = api_get({
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvprop": "content|ids|timestamp",
    })
    pages = data.get("query", {}).get("pages", {})
    page = next(iter(pages.values()))
    revs = page.get("revisions") or []
    if not revs:
        return {"title": title, "pageid": page.get("pageid"), "revision_id": None, "revision_ts": None, "wikitext": None}

    rev = revs[0]
    wt = rev.get("*")
    return {
        "title": title,
        "pageid": page.get("pageid"),
        "revision_id": rev.get("revid"),
        "revision_ts": rev.get("timestamp"),
        "wikitext": wt,
    }
