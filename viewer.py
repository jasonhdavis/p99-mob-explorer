import sqlite3
import pandas as pd
import streamlit as st
import numpy as np

from config import DB_PATH

st.set_page_config(page_title="P99 NPC Inventory", layout="wide")
st.title("P99 NPC Explorer")

@st.cache_data
def load_core():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM npc_core", conn)
    conn.close()

    def normalize_classes(c):
        if pd.isna(c): return ["Unknown"]
        c = str(c).strip()
        # Remove wiki links [[...]]
        import re
        c = re.sub(r'\[\[(?:[^|\]]*\|)?([^\]]+)\]\]', r'\1', c)
        # Remove other brackets and quotes
        c = c.replace("''", "").replace("[", "").replace("]", "")
        
        # Split by common delimiters
        parts = re.split(r',|<br>|/| or | OR | and | AND ', c)
        
        normalized = []
        mapping = {
            "Shadowknight": "Shadow Knight",
            "shadow Knight": "Shadow Knight",
            "Mage": "Magician",
            "Necro": "Necromancer",
            "warrior": "Warrior",
            "summoned": "Summoned",
            "Shopkeepr": "Shopkeeper",
            "Shopkeeper": "Merchant",
        }
        
        for p in parts:
            p = p.replace("?", "").strip()
            if not p: continue
            # Handle GM prefix
            if p.startswith("GM "):
                p = p[3:].strip()
            
            p = mapping.get(p, p)
            if p and p not in normalized:
                normalized.append(p)
        
        return normalized if normalized else ["Unknown"]

    df["classes_norm"] = df["class"].apply(normalize_classes)
    
    # Calculate RSI (Relative Strength Index) based on HP within each level
    def calculate_rsi(group):
        if len(group) < 2:
            group["rsi"] = 50.0
            return group
        group["rsi"] = group["hp"].rank(pct=True) * 100
        return group
    
    # Apply RSI calculation grouped by level
    df = df.groupby("level_min", group_keys=False).apply(calculate_rsi)
    
    return df

@st.cache_data
def load_kv_for_title(title: str):
    conn = sqlite3.connect(DB_PATH)
    kv = pd.read_sql_query(
        "SELECT template_name, param_name, param_value FROM template_kv WHERE title = ? ORDER BY template_name, param_name",
        conn,
        params=(title,)
    )
    wt = pd.read_sql_query("SELECT wikitext FROM pages WHERE title = ?", conn, params=(title,))
    conn.close()
    wikitext = wt["wikitext"].iloc[0] if len(wt) else ""
    return kv, wikitext

df = load_core()

# Sidebar filters
st.sidebar.header("Filters")

q = st.sidebar.text_input("Title contains", "")
min_level = st.sidebar.number_input("Min level >=", value=0, min_value=0, step=1)
max_level = st.sidebar.number_input("Max level <=", value=60, min_value=0, step=1)
hp_min = st.sidebar.number_input("HP >=", value=0, min_value=0, step=50)
hp_max = st.sidebar.number_input("HP <=", value=20000, min_value=0, step=100)

rsi_min, rsi_max = st.sidebar.slider("RSI Range", 0.0, 100.0, (0.0, 100.0))

zone_contains = st.sidebar.text_input("Zone contains", "")

# Class filter
all_classes_set = set()
for clist in df["classes_norm"]:
    all_classes_set.update(clist)
all_classes = sorted(list(all_classes_set))

if "Unknown" in all_classes:
    all_classes.remove("Unknown")
    all_classes.append("Unknown")

class_filter = st.sidebar.selectbox("Class", ["All"] + all_classes)

filtered = df.copy()

if q:
    filtered = filtered[filtered["title"].str.contains(q, case=False, na=False)]

filtered = filtered[
    (filtered["level_min"].fillna(-1) >= min_level) &
    (filtered["level_min"].fillna(10**9) <= max_level)
]

filtered = filtered[
    (filtered["hp"].fillna(-1) >= hp_min) &
    (filtered["hp"].fillna(10**9) <= hp_max)
]

filtered = filtered[
    (filtered["rsi"] >= rsi_min) &
    (filtered["rsi"] <= rsi_max)
]

if zone_contains:
    filtered = filtered[filtered["zone"].fillna("").str.contains(zone_contains, case=False, na=False)]

if class_filter != "All":
    filtered = filtered[filtered["classes_norm"].apply(lambda x: class_filter in x)]

# Computed metric
filtered["hp_per_level"] = filtered.apply(
    lambda r: (float(r["hp"]) / float(r["level_min"])) if pd.notna(r["hp"]) and pd.notna(r["level_min"]) and r["level_min"] else None,
    axis=1
)

sort_col = st.sidebar.selectbox("Sort by", ["rsi", "hp_per_level", "hp", "level_min", "title"])
sort_asc = st.sidebar.checkbox("Ascending", value=False if sort_col in ["rsi", "hp", "hp_per_level"] else True)

# Group By functionality
group_by = st.sidebar.selectbox("Group By", ["None", "Level", "Zone"])

if group_by == "Level":
    filtered = filtered.sort_values(by=["level_min", sort_col], ascending=[True, sort_asc], na_position="last")
elif group_by == "Zone":
    filtered = filtered.sort_values(by=["zone", sort_col], ascending=[True, sort_asc], na_position="last")
else:
    filtered = filtered.sort_values(by=sort_col, ascending=sort_asc, na_position="last")

st.subheader(f"Results ({len(filtered)})")

with st.expander("ℹ️ About RSI"):
    st.markdown("""
    **Relative Strength Index (RSI)** is a measure of how "tough" an NPC is compared to other NPCs of the **same level**.
    It represents the **percentile rank** of the NPC's HP. 
    *   **RSI 100**: Highest HP for that level.
    *   **RSI 50**: Median HP for that level.
    *   **RSI 0**: Lowest HP for that level.
    """)

WIKI_BASE_URL = "https://wiki.project1999.com/"
def make_wiki_link(title):
    if pd.isna(title):
        return ""
    url = WIKI_BASE_URL + title.replace(" ", "_")
    return url

filtered["Wiki Link"] = filtered["title"].apply(make_wiki_link)

st.dataframe(
    filtered[["Wiki Link", "title", "level_min", "level_max", "hp", "rsi", "hp_per_level", "ac", "atk", "zone", "race", "class"]],
    use_container_width=True,
    height=520,
    column_config={
        "Wiki Link": st.column_config.LinkColumn("View", display_text="View"),
        "rsi": st.column_config.NumberColumn("RSI", format="%.1f", help="Relative Strength Index: Percentile rank of HP within the same level.")
    }
)

st.divider()

st.subheader("Inspect an NPC")
selected = st.selectbox("Select title", filtered["title"].dropna().head(5000).tolist() if len(filtered) else df["title"].dropna().head(5000).tolist())

if selected:
    kv, wikitext = load_kv_for_title(selected)
    left, right = st.columns([1,1])

    with left:
        st.markdown("### Template parameters")
        st.dataframe(kv, use_container_width=True, height=500)

    with right:
        st.markdown("### Raw wikitext")
        st.text_area("wikitext", wikitext or "", height=500)
