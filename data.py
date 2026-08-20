import requests
import pandas as pd
import streamlit as st


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

    rows = []
    monthly = []
    all_gws = set()

    for t in entries:
        hist = fetch(f"https://draft.premierleague.com/api/entry/{t['entry_id']}/history")
        if not hist:
            continue

        manager = f"{t['player_first_name']} {t['player_last_name']}"
        bacon = TEAM_MAP.get(manager, "Other")

        gw = {}
        m = {}

        for h in hist["history"]:
            gw[h["event"]] = h["points"]
            all_gws.add(h["event"])

            month = gw_to_month.get(h["event"])
            if month:
                m[month] = m.get(month, 0) + h["points"]

        # -----------------------
        # GAMEWEEK ROW
        # -----------------------
        row = {
            "Team": t["entry_name"],
            "Manager": manager,
            "Bacon": bacon
        }

        for g in sorted(all_gws):
            row[f"GW{g}"] = gw.get(g, 0)

        row["Total"] = sum(gw.values())
        rows.append(row)

        # -----------------------
        # MONTHLY ROW (FIXED)
        # -----------------------
        mrow = {
            "Team": t["entry_name"],
            "Manager": manager,
            "Bacon": bacon
        }

        for mm in sorted(m.keys()):
            mrow[mm.strftime("%b %Y")] = m[mm]

        mrow["Total"] = sum(m.values())
        monthly.append(mrow)

    # -----------------------
    # DATAFRAMES
    # -----------------------
    df = pd.DataFrame(rows).fillna(0)
    dfm = pd.DataFrame(monthly).fillna(0)

    df = df.sort_values("Total", ascending=False).reset_index(drop=True)
    dfm = dfm.sort_values("Total", ascending=False).reset_index(drop=True)

    return df, dfm
