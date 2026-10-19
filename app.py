
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px

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

@st.cache_data
def load_data():
    url = (
        "https://archive.ics.uci.edu/"
        "ml/machine-learning-databases/00350/"
        "default%20of%20credit%20card%20clients.xls"
    )
    return pd.read_excel(url, header=1)

try:
    df = load_data()

    conn = sqlite3.connect(":memory:")
    df.to_sql("credit_clients", conn, if_exists="replace", index=False)

    st.success(f"Dataset loaded: {len(df):,} customer records")

    kpi = pd.read_sql_query("""
        SELECT
            COUNT(*) AS total_customers,
            SUM("default payment next month") AS defaults,
            ROUND(
                100.0 * SUM("default payment next month") / COUNT(*),
                2
            ) AS default_rate
        FROM credit_clients
    """, conn).iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Customers analyzed", f"{int(kpi['total_customers']):,}")
    col2.metric("Recorded defaults", f"{int(kpi['defaults']):,}")
    col3.metric("Observed default rate", f"{kpi['default_rate']:.2f}%")

    st.caption(
        "Historical Taiwan credit-card data. Observed patterns are not "
        "proof of causation or a basis for individual lending decisions."
    )

except Exception as e:
    st.error("The dataset could not be loaded. Check your internet connection.")
    st.exception(e)
