import streamlit as st
from data import load_data
import pandas as pd
import altair as alt

# -----------------------
# SAFETY
# -----------------------
if "league_id" not in st.session_state:
    st.session_state.league_id = 9292

st.title("📊 Monthly")

# -----------------------
# LOAD DATA
# -----------------------
_, dfm = load_data(st.session_state.league_id)
dfm = dfm.copy()

# -----------------------
# HELPER: SORT MONTHS PROPERLY
# -----------------------
def sort_months(month_list):
    return sorted(month_list, key=lambda x: pd.to_datetime(x, format="%b %Y"))

# -----------------------
# IDENTIFY MONTH COLUMNS
# -----------------------
def is_month(col):
    try:
        pd.to_datetime(col, format="%b %Y")
        return True
    except:
        return False

month_cols = [c for c in dfm.columns if is_month(c)]
month_cols = sort_months(month_cols)

if not month_cols:
    st.info("Monthly standings will appear after the first scored gameweek.")
    st.stop()

# -----------------------
# GLOBAL RANGE STATE
# -----------------------
if "month_range" not in st.session_state:
    st.session_state.month_range = (1, len(month_cols))

# -----------------------
# CONTROLS (PERSISTENT)
# -----------------------
st.markdown("### 🎚️ Controls")

start, end = st.slider(
    "Select Month Range",
    1,
    len(month_cols),
    st.session_state.month_range,
    key="month_slider"
)

# Persist state
st.session_state.month_range = (start, end)

selected_months = month_cols[start - 1:end]
selected_months = sort_months(selected_months)

# -----------------------
# CALCULATE TOTAL
# -----------------------
dfm["Total"] = dfm[selected_months].sum(axis=1)

# Sort
dfm = dfm.sort_values("Total", ascending=False).reset_index(drop=True)

# Position
dfm.insert(0, "Position", range(1, len(dfm) + 1))

# -----------------------
# TABLE
# -----------------------
st.subheader("📊 Monthly Performance")

display_cols = ["Position", "Team", "Manager", "Bacon", "Total"] + selected_months
display_df = dfm[display_cols].copy()

styled_df = display_df.style.set_properties(
    subset=["Total"],
    **{"font-weight": "bold"}
)

# -----------------------
# CHART (CUMULATIVE)
# -----------------------
base_df = dfm.set_index("Team")[selected_months]
cum_df = base_df.cumsum(axis=1)

chart_df = cum_df.T.reset_index()
chart_df = chart_df.rename(columns={"index": "Month"})

chart_df = chart_df.melt(
    id_vars="Month",
    var_name="Team",
    value_name="Points"
)

chart = alt.Chart(chart_df).mark_line().encode(
    x=alt.X(
        "Month:O",
        sort=selected_months,
        title="Month"
    ),
    y=alt.Y("Points:Q", title="Cumulative Points"),
    color="Team:N"
).properties(height=400)

# -----------------------
# VIEW MODE (FOCUS)
# -----------------------
st.markdown("### 🔍 View Mode")

focus = st.toggle("Enable Focus Mode (expand view)")

# -----------------------
# DEFAULT (STACKED)
# -----------------------
if not focus:
    st.dataframe(
        styled_df,
        use_container_width=True,
        hide_index=True
    )

    st.subheader("📈 Trend")
    st.altair_chart(chart, use_container_width=True)

# -----------------------
# FOCUS MODE
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
