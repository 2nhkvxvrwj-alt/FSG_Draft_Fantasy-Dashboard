import streamlit as st
from data import load_data

# -----------------------
# SAFETY
# -----------------------
if "league_id" not in st.session_state:
    st.session_state.league_id = 21020

st.title("📅 Gameweeks")

# -----------------------
# LOAD DATA
# -----------------------
df, _ = load_data(st.session_state.league_id)
df = df.copy()

# -----------------------
# HELPER: SORT GWs PROPERLY
# -----------------------
def sort_gws(gw_list):
    return sorted(gw_list, key=lambda x: int(x.replace("GW", "")))

# -----------------------
# GET ACTIVE GWs ONLY
# -----------------------
gw_cols = [c for c in df.columns if c.startswith("GW")]

active_gws = [g for g in gw_cols if df[g].sum() > 0]
active_gws = sort_gws(active_gws)

# -----------------------
# RANGE SELECTOR
# -----------------------
st.subheader("Gameweek Range")

start, end = st.slider(
    "Select Gameweek Range",
    1,
    len(active_gws),
    (1, len(active_gws))
)

selected_gws = active_gws[start - 1:end]
selected_gws = sort_gws(selected_gws)

# -----------------------
# CALCULATE TOTAL
# -----------------------
df["Total"] = df[selected_gws].sum(axis=1)

# Sort by selected total
df = df.sort_values("Total", ascending=False).reset_index(drop=True)

# Add Position column
df.insert(0, "Position", range(1, len(df) + 1))

# -----------------------
# TABLE (MERGED + CLEAN)
# -----------------------
st.subheader("📊 Gameweek Performance")

display_cols = ["Position", "Team", "Manager", "Bacon", "Total"] + selected_gws
display_df = df[display_cols].copy()

styled_df = display_df.style.set_properties(
    subset=["Total"],
    **{"font-weight": "bold"}
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)

import pandas as pd
import altair as alt

# -----------------------
# CHART (CUMULATIVE + CLEAN AXIS)
# -----------------------
st.subheader("📈 Trend")

selected_gws_sorted = sort_gws(selected_gws)

# Convert GW labels → numeric
gw_numbers = [int(g.replace("GW", "")) for g in selected_gws_sorted]

# Build base dataframe
base_df = df.set_index("Team")[selected_gws_sorted]

# 🔥 CUMULATIVE SUM (this fixes main requirement)
cum_df = base_df.cumsum(axis=1)

# Transpose for chart
chart_df = cum_df.T
chart_df["GW"] = gw_numbers

# Melt for Altair
chart_df = chart_df.reset_index(drop=True).melt(
    id_vars="GW",
    var_name="Team",
    value_name="Points"
)

# -----------------------
# ALTAIR CHART
# -----------------------
chart = alt.Chart(chart_df).mark_line().encode(
    x=alt.X(
        "GW:O",
        title="Gameweek",
        axis=alt.Axis(labelExpr="'GW' + datum.label")
    ),
    y=alt.Y("Points:Q", title="Cumulative Points"),
    color="Team:N"
).properties(height=400)

st.altair_chart(chart, use_container_width=True)