import streamlit as st
from data import load_data
import pandas as pd
import altair as alt

# -----------------------
# STATE
# -----------------------
if "league_id" not in st.session_state:
    st.session_state.league_id = 9292

# -----------------------
# LOAD DATA
# -----------------------
df, _ = load_data(st.session_state.league_id)
df = df.copy()

st.title("📊 Gameweeks")

# -----------------------
# IDENTIFY GW COLUMNS
# -----------------------
gw_cols = [c for c in df.columns if c.startswith("GW")]
gw_cols = sorted(gw_cols, key=lambda x: int(x.replace("GW", "")))

if not gw_cols:
    st.info("Gameweek standings will appear after the first scored gameweek.")
    st.stop()

# -----------------------
# GLOBAL RANGE STATE
# -----------------------
if "gw_range" not in st.session_state:
    st.session_state.gw_range = (1, len(gw_cols))

# -----------------------
# CONTROLS (ALWAYS VISIBLE)
# -----------------------
st.markdown("### 🎚️ Controls")

start, end = st.slider(
    "Gameweek Range",
    1,
    len(gw_cols),
    st.session_state.gw_range,
    key="gw_slider"
)

# Persist state
st.session_state.gw_range = (start, end)

selected_gws = gw_cols[start - 1:end]

# -----------------------
# CALCULATE TOTAL
# -----------------------
df["Total"] = df[selected_gws].sum(axis=1)

# Sort
df = df.sort_values("Total", ascending=False).reset_index(drop=True)

# Position column
df.insert(0, "Position", range(1, len(df) + 1))

# -----------------------
# TABLE
# -----------------------
display_cols = ["Position", "Team", "Manager", "Bacon", "Total"] + selected_gws
display_df = df[display_cols].copy()

# Bold total
styled_df = display_df.style.set_properties(
    subset=["Total"],
    **{"font-weight": "bold"}
)

# -----------------------
# CHART (CUMULATIVE)
# -----------------------
base_df = df.set_index("Team")[selected_gws]

cum_df = base_df.cumsum(axis=1)

chart_df = cum_df.T.reset_index()
chart_df = chart_df.rename(columns={"index": "GW"})

chart_df["GW"] = chart_df["GW"].str.replace("GW", "").astype(int)

chart_df = chart_df.melt(
    id_vars="GW",
    var_name="Team",
    value_name="Points"
)

chart = alt.Chart(chart_df).mark_line().encode(
    x=alt.X("GW:O", title="Gameweek"),
    y=alt.Y("Points:Q", title="Cumulative Points"),
    color="Team:N"
).properties(height=400)

# -----------------------
# VIEW MODE
# -----------------------
st.markdown("### 🔍 View Mode")

focus = st.toggle("Enable Focus Mode (expand view)")

# -----------------------
# DEFAULT (STACKED — MOBILE FRIENDLY)
# -----------------------
if not focus:
    st.subheader("📊 Table")
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📈 Chart")
    st.altair_chart(chart, use_container_width=True)

# -----------------------
# FOCUS MODE (FULL VIEW WITH CONTROLS)
# -----------------------
else:
    view = st.radio("Select View", ["Table", "Chart"], horizontal=True)

    if view == "Table":
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True
        )
    else:
        st.altair_chart(chart, use_container_width=True)
