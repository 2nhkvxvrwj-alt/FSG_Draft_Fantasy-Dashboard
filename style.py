import streamlit as st

def apply_style():
    st.markdown("""
    <style>
    .title {
        font-size: 32px;
        font-weight: 700;
        color: #ffffff;
    }
    .metric-card {
        background: #161a40;
        padding: 12px;
        border-radius: 10px;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)