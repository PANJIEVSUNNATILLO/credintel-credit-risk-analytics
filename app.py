
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

    st.divider()
    st.header("Credit Risk Analysis")

    repayment = pd.read_sql_query("""
        SELECT
            PAY_0 AS repayment_status,
            COUNT(*) AS total_customers,
            SUM("default payment next month") AS customers_defaulted,
            ROUND(
                100.0 * SUM("default payment next month") / COUNT(*),
                2
            ) AS default_rate_percent
        FROM credit_clients
        GROUP BY PAY_0
        ORDER BY PAY_0
    """, conn)

    credit_limits = pd.read_sql_query("""
        SELECT
            CASE
                WHEN LIMIT_BAL < 50000 THEN 'Under 50K'
                WHEN LIMIT_BAL < 100000 THEN '50K–99K'
                WHEN LIMIT_BAL < 200000 THEN '100K–199K'
                WHEN LIMIT_BAL < 500000 THEN '200K–499K'
                ELSE '500K and above'
            END AS credit_limit_segment,
            COUNT(*) AS total_customers,
            SUM("default payment next month") AS customers_defaulted,
            ROUND(
                100.0 * SUM("default payment next month") / COUNT(*),
                2
            ) AS default_rate_percent
        FROM credit_clients
        GROUP BY credit_limit_segment
        ORDER BY MIN(LIMIT_BAL)
    """, conn)

    left, right = st.columns(2)

    with left:
        st.subheader("By Repayment Status")
        fig1 = px.bar(
            repayment,
            x="repayment_status",
            y="default_rate_percent",
            labels={
                "repayment_status": "Repayment Status",
                "default_rate_percent": "Observed Default Rate (%)"
            },
            hover_data=["total_customers", "customers_defaulted"]
        )
        st.plotly_chart(fig1, use_container_width=True)

    with right:
        st.subheader("By Credit Limit")
        fig2 = px.bar(
            credit_limits,
            x="credit_limit_segment",
            y="default_rate_percent",
            labels={
                "credit_limit_segment": "Credit Limit Segment (NTD)",
                "default_rate_percent": "Observed Default Rate (%)"
            },
            hover_data=["total_customers", "customers_defaulted"]
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        "These are historical associations, not proof of causation or "
        "a basis for individual lending decisions."
    )

except Exception:
    st.error(
        "The dataset could not be loaded or analyzed. "
        "Check your internet connection and try again."
    )
