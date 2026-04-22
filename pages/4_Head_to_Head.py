import streamlit as st
from data import load_data

st.title("⚔️ Head to Head")

df, _ = load_data(st.session_state.league_id)

teams = df["Team"].tolist()

t1 = st.selectbox("Team 1", teams)
t2 = st.selectbox("Team 2", teams, index=1)

row1 = df[df["Team"] == t1].iloc[0]
row2 = df[df["Team"] == t2].iloc[0]

col1, col2 = st.columns(2)

col1.metric(t1, row1["Total"])
col2.metric(t2, row2["Total"])