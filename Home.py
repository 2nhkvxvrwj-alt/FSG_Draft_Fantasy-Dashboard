import streamlit as st
import requests
import pandas as pd
from style import apply_style

st.set_page_config(page_title="Home", layout="wide")
apply_style()

# =====================================================
# 🔒 SIDEBAR — LEAGUE CONTROL
# =====================================================
if "league_id" not in st.session_state:
    st.session_state.league_id = 21020

if "locked" not in st.session_state:
    st.session_state.locked = True

st.sidebar.title("⚙️ Settings")

col1, col2 = st.sidebar.columns([3,1])

with col1:
    if st.session_state.locked:
        st.text_input("League ID", value=st.session_state.league_id, disabled=True)
    else:
        new_id = st.text_input("League ID", value=st.session_state.league_id)
        if new_id:
            st.session_state.league_id = int(new_id)

with col2:
    if st.button("🔒" if st.session_state.locked else "🔓"):
        st.session_state.locked = not st.session_state.locked

LEAGUE_ID = st.session_state.league_id

# =====================================================
# 📡 DATA LOAD (dynamic league)
# =====================================================
@st.cache_data(ttl=300)
def fetch(url):
    try:
        return requests.get(url).json()
    except:
        return None

@st.cache_data(ttl=300)
def load_data(league_id):
    league = fetch(f"https://draft.premierleague.com/api/league/{league_id}/details")
    bootstrap = fetch("https://fantasy.premierleague.com/api/bootstrap-static/")

    entries = league["league_entries"]
    events = bootstrap["events"]

    gw_to_month = {
        e["id"]: pd.to_datetime(e["deadline_time"]).to_period("M")
        for e in events if e.get("deadline_time")
    }

    # ---- SAFE TEAM MAP (empty fallback)
    TEAM_MAP = {
        "Steve Dickenson": "Beast FC",
        "Robert Gall": "Gall and the Gang",
        "Alvar Chambers": "Beast FC",
        "Guy Robinson": "Pogos Pilgrims",
        "Emanuele Ciampa": "Gall and the Gang",
        "Adrian Pogson": "Pogos Pilgrims",
        "Luke Smith": "Beast FC",
        "Dan Curtis": "Pogos Pilgrims",
        "Jani H": "Gall and the Gang",
    }

    rows = []
    monthly = {}
    all_months = set()

    for t in entries:
        hist = fetch(f"https://draft.premierleague.com/api/entry/{t['entry_id']}/history")
        if not hist:
            continue

        manager = f"{t['player_first_name']} {t['player_last_name']}"
        bacon = TEAM_MAP.get(manager, None)

        gw = {}
        m = {}

        for h in hist["history"]:
            gw[h["event"]] = h["points"]

            month = gw_to_month.get(h["event"])
            if month:
                m[month] = m.get(month, 0) + h["points"]
                all_months.add(month)

        row = {
            "Team": t["entry_name"],
            "Manager": manager,
            "Bacon": bacon
        }

        row["Total"] = sum(gw.values())
        rows.append(row)

        for mm, val in m.items():
            monthly.setdefault(mm, {}).setdefault(bacon, 0)
            monthly[mm][bacon] += val

    df = pd.DataFrame(rows).sort_values("Total", ascending=False).reset_index(drop=True)

    # ---- Build monthly DF
    months_sorted = sorted(all_months)
    data = []

    for b in set(TEAM_MAP.values()):
        row = {"Bacon": b}
        for m in months_sorted:
            row[m.strftime("%b %Y")] = monthly.get(m, {}).get(b, 0)
        data.append(row)

    dfm = pd.DataFrame(data)

    return df, dfm

df, dfm = load_data(LEAGUE_ID)

# =====================================================
# 🐷 HEADER
# =====================================================
st.markdown("# 🐷 FSG Fantasy Draft")

# =====================================================
# 🥓 BACON SECTION (TOP)
# =====================================================
st.subheader("🥓 Bacon League")

month_cols = [c for c in dfm.columns if c != "Bacon"]

# ---- find latest month with data
current_month = None

for m in reversed(month_cols):
    if dfm[m].sum() > 0:
        current_month = m
        break

# fallback if no data
if current_month is None and month_cols:
    current_month = month_cols[-1]

bacon_month = dfm.set_index("Bacon")[current_month].sort_values()

loser, second, third = bacon_month.index[:3]

gap1 = bacon_month[second] - bacon_month[loser]
gap2 = bacon_month[third] - bacon_month[loser]

st.markdown(f"<div style='font-size:20px; font-weight:600;'>🥪 Bacon Buyer ({current_month}) - {loser} </div>",
    unsafe_allow_html=True)
st.markdown(f"<span style='color:red'>↓ {int(gap1)} pts from {second}</span>", unsafe_allow_html=True)
st.markdown(f"<span style='color:red'>↓ {int(gap2)} pts from {third}</span>", unsafe_allow_html=True)
# ---- Dinner (season)
bacon_total = df.groupby("Bacon")["Total"].sum().sort_values()

loser_s, second_s, third_s = bacon_total.index[:3]

gap1_s = bacon_total[second_s] - bacon_total[loser_s]
gap2_s = bacon_total[third_s] - bacon_total[loser_s]

st.markdown(
    f"<div style='font-size:20px; font-weight:600;'>🍽️ Dinner Buyer (Season) - {loser_s}</div>",
    unsafe_allow_html=True
)
st.markdown(f"<span style='color:red'>↓ {int(gap1_s)} pts from {second_s}</span>", unsafe_allow_html=True)
st.markdown(f"<span style='color:red'>↓ {int(gap2_s)} pts from {third_s}</span>", unsafe_allow_html=True)

# ---- Bacon table (monthly + total)
table = dfm.copy()

# Create Total FIRST
table["Total"] = table[month_cols].sum(axis=1)

# THEN select columns
table = table[["Bacon", current_month, "Total"]]

# 🔥 SORT DESCENDING
table = table.sort_values("Total", ascending=False).reset_index(drop=True)

st.dataframe(table, use_container_width=False, hide_index=True)

# =====================================================
# 🏆 TEAMS SECTION (BOTTOM)
# =====================================================
st.subheader("🏆 Teams")

df["Position"] = range(1, len(df) + 1)

st.dataframe(
    df[["Position", "Team", "Manager", "Total"]],
    use_container_width=False,
    hide_index=True
)