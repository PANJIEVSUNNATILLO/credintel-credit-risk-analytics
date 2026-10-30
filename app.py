
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from google import genai

# -----------------------------------
# PAGE CONFIGURATION
# -----------------------------------

st.set_page_config(
    page_title="CredIntel | Credit Risk Analytics",
    page_icon="📊",
    layout="wide"
)

st.title("📊 CredIntel")
st.subheader("Turn Financial Data Into Intelligence")

st.markdown("""
Explore historical credit card data using SQL,
interactive charts, and AI-powered explanations.
""")

st.info(
    "Educational analytics prototype. Results describe historical "
    "data and are not individual lending recommendations."
)

# -----------------------------------
# LOAD DATASET
# -----------------------------------

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

    df.to_sql(
        "credit_clients",
        conn,
        if_exists="replace",
        index=False
    )

    st.success(f"Dataset loaded: {len(df):,} customer records")

    # -----------------------------------
    # KEY PERFORMANCE INDICATORS
    # -----------------------------------

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

    col1.metric(
        "Customers analyzed",
        f"{int(kpi['total_customers']):,}"
    )

    col2.metric(
        "Recorded defaults",
        f"{int(kpi['defaults']):,}"
    )

    col3.metric(
        "Observed default rate",
        f"{kpi['default_rate']:.2f}%"
    )

    st.caption(
        "Historical Taiwan credit-card data. "
        "Observed patterns are not proof of causation."
    )

    # -----------------------------------
    # REPAYMENT STATUS ANALYSIS
    # -----------------------------------

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

    # -----------------------------------
    # CREDIT LIMIT ANALYSIS
    # -----------------------------------

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

    # -----------------------------------
    # INTERACTIVE CHARTS
    # -----------------------------------

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
            hover_data=[
                "total_customers",
                "customers_defaulted"
            ]
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
            hover_data=[
                "total_customers",
                "customers_defaulted"
            ]
        )

        st.plotly_chart(fig2, use_container_width=True)

    st.caption(
        "These are historical associations, not proof of causation "
        "or a basis for individual lending decisions."
    )

    # -----------------------------------
    # GEMINI AI ASSISTANT
    # -----------------------------------

    st.divider()
    st.header("🤖 Ask CredIntel AI")

    st.write(
        "Ask questions about the historical credit-risk "
        "results in this dataset."
    )

    question = st.text_input(
        "Your question",
        placeholder="Why might repayment status matter for default risk?"
    )

    if st.button("Ask CredIntel AI"):

        if not question.strip():
            st.warning("Please enter a question first.")

        else:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(api_key=api_key)

                analysis_context = f"""
                Historical credit card dataset analysis:

                Total customers: {int(kpi['total_customers'])}
                Recorded defaults: {int(kpi['defaults'])}
                Observed default rate: {kpi['default_rate']}%

                Repayment status analysis:
                {repayment.to_string(index=False)}

                Credit limit analysis:
                {credit_limits.to_string(index=False)}
                """

                prompt = f"""
                You are CredIntel, a financial data analysis assistant.

                Answer using only the supplied historical analysis.

                Explain findings clearly.
                Do not claim causation.
                Do not make individual lending recommendations.
                If the data cannot answer the question, say so.

                DATA:
                {analysis_context}

                USER QUESTION:
                {question}
                """

                response = client.models.generate_content(
                    model="gemini-3.5-flash",
                    contents=prompt
                )

                st.markdown("### CredIntel AI Answer")
                st.write(response.text)

            except Exception:
                st.error(
                    "The AI assistant could not generate an answer. "
                    "Check your Streamlit Secrets and Gemini model access."
                )

except Exception:
    st.error(
        "The dataset could not be loaded or analyzed. "
        "Check the app logs for details."
    )
