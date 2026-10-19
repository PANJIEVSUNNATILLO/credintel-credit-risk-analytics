
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import os

st.set_page_config(
    page_title="CredIntel | Credit Risk Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CredIntel")
st.subheader("Turn Financial Data Into Intelligence")

st.markdown("""
Explore historical credit card data using SQL, interactive charts,
and AI-powered explanations.
""")

st.info(
    "Educational analytics prototype. Results describe historical "
    "data and are not individual lending recommendations."
)

