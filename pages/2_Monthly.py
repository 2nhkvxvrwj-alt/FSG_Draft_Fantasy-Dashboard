import streamlit as st
from data import load_data
import pandas as pd
import altair as alt

# -----------------------
# SAFETY
# -----------------------
if "league_id" not in st.session_state:
    st.session_state.league_id = 21020

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
    # expects labels like "Jan 2026"
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

# -----------------------
# RANGE SELECTOR
# -----------------------
st.subheader("Month Range")

start, end = st.slider(
    "Select Month Range",
    1,
    len(month_cols),
    (1, len(month_cols))
)

selected_months = month_cols[start - 1:end]
selected_months = sort_months(selected_months)

# -----------------------
# CALCULATE TOTAL
# -----------------------
dfm["Total"] = dfm[selected_months].sum(axis=1)

# Sort by selected total
dfm = dfm.sort_values("Total", ascending=False).reset_index(drop=True)

# Position column
dfm.insert(0, "Position", range(1, len(dfm) + 1))

# -----------------------
# TABLE (MATCHES GAMEWEEKS)
# -----------------------
st.subheader("📊 Monthly Performance")

display_cols = ["Position", "Team", "Manager", "Bacon", "Total"] + selected_months
display_df = dfm[display_cols].copy()

# Bold Total
styled_df = display_df.style.set_properties(
    subset=["Total"],
    **{"font-weight": "bold"}
)

st.dataframe(
    styled_df,
    use_container_width=True,
    hide_index=True
)

# -----------------------
# CHART (CUMULATIVE)
# -----------------------
st.subheader("📈 Trend")

# Base data
base_df = dfm.set_index("Team")[selected_months]

# Cumulative
cum_df = base_df.cumsum(axis=1)

# Prepare for Altair
chart_df = cum_df.T.reset_index()
chart_df = chart_df.rename(columns={"index": "Month"})

chart_df = chart_df.melt(
    id_vars="Month",
    var_name="Team",
    value_name="Points"
)

# -----------------------
# ALTAIR CHART
# -----------------------
chart = alt.Chart(chart_df).mark_line().encode(
    x=alt.X(
    "Month:O",
    sort=selected_months,   # 🔥 THIS FIXES ORDER
    title="Month"
),
    y=alt.Y("Points:Q", title="Cumulative Points"),
    color="Team:N"
).properties(height=400)

st.altair_chart(chart, use_container_width=True)