import sqlite3
import pandas as pd
import streamlit as st
import numpy as np
import plotly.express as px

DB_PATH = "data/p99.sqlite"

st.set_page_config(page_title="P99 NPC Strength Analysis", layout="wide")
st.title("P99 NPC Strength Analysis")

# Navigation
st.sidebar.title("Navigation")
if st.sidebar.button("Back to Inventory Explorer"):
    st.switch_page("viewer")

@st.cache_data
def load_core():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM npc_core", conn)
    conn.close()
    # Clean up zone names (remove [[ ]])
    df["zone_clean"] = df["zone"].str.replace(r"\[\[|\]\]", "", regex=True)
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

df_raw = load_core()

# --- Sidebar Filters & Outlier Removal ---
st.sidebar.header("Global Filters & Outlier Removal")

# Filter out NPCs with very low HP (likely data entry errors or special cases)
hp_outlier_threshold = st.sidebar.number_input("Min HP Threshold (Filter Outliers)", value=10, min_value=0)
df = df_raw[df_raw["hp"] >= hp_outlier_threshold].copy()

# Filter by Level Range
min_lvl, max_lvl = int(df["level_min"].min() or 1), int(df["level_min"].max() or 60)
level_range = st.sidebar.slider("Level Range", min_lvl, max_lvl, (min_lvl, max_lvl))
df = df[(df["level_min"] >= level_range[0]) & (df["level_min"] <= level_range[1])]

# --- RSI Calculation ---
def calculate_rsi(group):
    if len(group) < 2:
        group["rsi"] = 50.0 # Neutral if alone
        group["hp_zscore"] = 0.0
        return group
    
    # Percentile rank (0 to 100)
    group["rsi"] = group["hp"].rank(pct=True) * 100
    
    # Z-score on log(HP) to handle exponential scaling better
    log_hp = np.log1p(group["hp"])
    std = log_hp.std()
    if std > 0:
        group["hp_zscore"] = (log_hp - log_hp.mean()) / std
    else:
        group["hp_zscore"] = 0.0
        
    return group

df = df.groupby("level_min", group_keys=False).apply(calculate_rsi)

# --- About RSI ---
with st.expander("ℹ️ About Relative Strength Index (RSI)"):
    st.markdown("""
    ### How RSI is Calculated
    The **Relative Strength Index (RSI)** is a measure of how "tough" an NPC is compared to other NPCs of the **same level**.
    
    1.  **Percentile Rank (0-100)**: This is the primary RSI value shown in the table. An RSI of 90 means the NPC has more HP than 90% of other NPCs at that level.
    2.  **Log-Z-Score**: Because NPC HP scales exponentially with level, we calculate a Z-score (standard deviations from the mean) using the *natural log* of HP. This helps normalize the distribution and makes it easier to compare "strength" across different level brackets.
    
    ### Why use RSI?
    *   **Identify Outliers**: NPCs with an RSI near 100 are often "named" mobs, bosses, or raid targets.
    *   **Zone Difficulty**: By averaging the RSI of all NPCs in a zone, we can determine if a zone is generally "harder" or "easier" than its level range suggests.
    *   **Data Quality**: Extremely low RSI values often point to data entry errors or special quest NPCs that aren't meant for combat.
    """)

# --- Zone Analysis ---
st.sidebar.header("Zone Analysis")
zone_metrics = df.groupby("zone_clean").agg({
    "hp_zscore": "mean",
    "title": "count",
    "level_min": "mean"
}).rename(columns={"hp_zscore": "Avg RSI (Z-Score)", "title": "NPC Count", "level_min": "Avg Level"})

st.sidebar.dataframe(zone_metrics.sort_values("Avg RSI (Z-Score)", ascending=False).head(10))

# --- Visualization ---
st.header("HP Distribution by Level")

all_zones = sorted(df["zone_clean"].dropna().unique())
selected_zones = st.multiselect("Filter by Zones", all_zones)

plot_df = df.copy()
if selected_zones:
    plot_df = plot_df[plot_df["zone_clean"].isin(selected_zones)]

fig_type = st.radio("Visualization Type", ["Scatter (HP vs Level)", "Stacked Bar (Count by Level)"])

if fig_type == "Scatter (HP vs Level)":
    fig = px.scatter(
        plot_df, 
        x="level_min", 
        y="hp", 
        color="zone_clean",
        hover_data=["title", "rsi"],
        log_y=True,
        title="NPC HP by Level (Log Scale)",
        labels={"level_min": "Level", "hp": "HP", "zone_clean": "Zone", "rsi": "RSI"}
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    fig = px.bar(
        plot_df.groupby(["level_min", "zone_clean"]).size().reset_index(name="count"),
        x="level_min",
        y="count",
        color="zone_clean",
        title="NPC Count by Level and Zone",
        labels={"level_min": "Level", "count": "NPC Count", "zone_clean": "Zone"}
    )
    st.plotly_chart(fig, use_container_width=True)

# --- Data Table ---
st.subheader(f"NPC Data (Filtered: {len(plot_df)})")

plot_df["hp_per_level"] = plot_df["hp"] / plot_df["level_min"]

cols_to_show = ["title", "level_min", "hp", "rsi", "hp_per_level", "zone_clean", "class"]
st.dataframe(
    plot_df[cols_to_show].sort_values("rsi", ascending=False),
    use_container_width=True,
    column_config={
        "rsi": st.column_config.NumberColumn("RSI (Percentile)", format="%.1f"),
        "hp_per_level": st.column_config.NumberColumn("HP/Lvl", format="%.1f")
    }
)

st.divider()

# --- Inspector ---
st.subheader("Inspect an NPC")
selected_title = st.selectbox("Select NPC to inspect", plot_df["title"].unique())
if selected_title:
    kv, wikitext = load_kv_for_title(selected_title)
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(kv, use_container_width=True)
    with col2:
        st.text_area("Wikitext", wikitext, height=400)
