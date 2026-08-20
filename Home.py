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
    st.session_state.league_id = 9292

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
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as error:
        raise RuntimeError(f"Could not load Fantasy Premier League data from {url}: {error}") from error

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
        "Steve Dickenson": "Gall Stones",
        "Robert Gall": "Gall Stones",
        "Alvar Chambers": "The Beastie Boys",
        "Guy Robinson": "The Beastie Boys",
        "Emanuele Ciampa": "JaniDaniMani",
        "Adrian Pogson": "Gall Stones",
        "Luke Smith": "The Beastie Boys",
        "Dan Curtis": "JaniDaniMani",
        "Jani H": "JaniDaniMani",
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

        for g in sorted(gw.keys()):
            row[f"GW{g}"] = gw.get(g, 0)

        row["Total"] = sum(gw.values())
        rows.append(row)

        for mm, val in m.items():
            monthly.setdefault(mm, {}).setdefault(bacon, 0)
            monthly[mm][bacon] += val

    df = pd.DataFrame(rows).fillna(0).sort_values("Total", ascending=False).reset_index(drop=True)

    # ---- Build monthly DF
    months_sorted = sorted(all_months)
    data = []

    for b in set(TEAM_MAP.values()):
        row = {"Bacon": b}
        for m in months_sorted:
            row[m.strftime("%b %Y")] = monthly.get(m, {}).get(b, 0)
        data.append(row)

    dfm = pd.DataFrame(data)

    return df, dfm, gw_to_month

try:
    df, dfm, gw_to_month = load_data(LEAGUE_ID)
except Exception as e:
    st.write(f"Error in load_data: {e}")
    import traceback
    st.write(traceback.format_exc())
    st.stop()


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

if current_month is None:
    st.info("Monthly standings will appear after the first scored gameweek.")
else:
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
if current_month is None:
    table = df.groupby("Bacon", as_index=False)["Total"].sum()
else:
    table = dfm.copy()
    table["Total"] = table[month_cols].sum(axis=1)
    table = table[["Bacon", current_month, "Total"]]

# 🔥 SORT DESCENDING
table = table.sort_values("Total", ascending=False).reset_index(drop=True)

st.dataframe(table, use_container_width=False, hide_index=True)

# =====================================================
# 🏆 TEAMS SECTION (BOTTOM)
# =====================================================
st.subheader("🏆 Teams")

gw_cols = [c for c in df.columns if c.startswith("GW")]
sorted_gw_cols = sorted(gw_cols, key=lambda x: int(x.replace("GW", "")))

last_week = None
for col in reversed(sorted_gw_cols):
    if df[col].sum() > 0:
        last_week = col
        break
if last_week is None and sorted_gw_cols:
    last_week = sorted_gw_cols[-1]

if last_week:
    df["Weekly"] = df[last_week]
else:
    df["Weekly"] = 0

monthly_gw_cols = []
if current_month is not None:
    current_month_period = pd.to_datetime(current_month, format="%b %Y").to_period("M")
    monthly_gw_cols = [
        c for c in sorted_gw_cols
        if gw_to_month.get(int(c.replace("GW", ""))) == current_month_period
    ]

if monthly_gw_cols:
    df["Monthly"] = df[monthly_gw_cols].sum(axis=1)
else:
    df["Monthly"] = 0

# Keep ordering by Total descending by default
df["Position"] = range(1, len(df) + 1)

st.dataframe(
    df[["Position", "Team", "Manager", "Total", "Weekly", "Monthly"]],
    use_container_width=False,
    hide_index=True
)
