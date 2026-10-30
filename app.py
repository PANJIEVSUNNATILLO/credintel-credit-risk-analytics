
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from google import genai

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CredIntel | Credit Risk Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# DARK FINTECH DESIGN
# --------------------------------------------------

st.markdown("""
<style>
    .stApp {
        background: #0B1220;
        color: #F1F5F9;
    }

    [data-testid="stSidebar"] {
        background: #111C2E;
        border-right: 1px solid #26364D;
    }

    h1, h2, h3 {
        color: #F1F5F9 !important;
    }

    p, label {
        color: #CBD5E1;
    }

    [data-testid="stMetric"] {
        background: #172438;
        border: 1px solid #293B54;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricValue"] {
        color: #5EEAD4;
    }

    [data-testid="stMetricLabel"] {
        color: #CBD5E1;
    }

    .stButton > button {
        background: #0D9488;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    .stButton > button:hover {
        background: #14B8A6;
        color: white;
    }

    div[data-baseweb="input"] input {
        background: #172438;
        color: white;
    }

    div[data-baseweb="select"] > div {
        background: #172438;
        color: white;
    }

    [data-testid="stDownloadButton"] button {
        background: #172438;
        color: #5EEAD4;
        border: 1px solid #0D9488;
        border-radius: 8px;
    }

    hr {
        border-color: #293B54;
    }
</style>
""", unsafe_allow_html=True)


# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

DATA_URL = (
    "https://archive.ics.uci.edu/ml/"
    "machine-learning-databases/00350/"
    "default%20of%20credit%20card%20clients.xls"
)

@st.cache_data
def load_data():
    data = pd.read_excel(DATA_URL, header=1)
    data.columns = data.columns.astype(str).str.strip()
    return data


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def make_credit_segments(data):
    bins = [0, 50000, 100000, 200000, 500000, float("inf")]
    labels = [
        "Under 50K",
        "50K–99K",
        "100K–199K",
        "200K–499K",
        "500K and above"
    ]

    data = data.copy()
    data["Credit Limit Segment"] = pd.cut(
        data["LIMIT_BAL"],
        bins=bins,
        labels=labels,
        right=False
    )
    return data


def calculate_default_rate(data):
    if len(data) == 0:
        return 0

    return (
        data["default payment next month"].sum()
        / len(data)
        * 100
    )


# --------------------------------------------------
# HEADER
# --------------------------------------------------

st.markdown("""
<div style="
    background: linear-gradient(120deg, #14243A, #0F766E);
    padding: 28px;
    border-radius: 16px;
    margin-bottom: 22px;
">
    <h1 style="color: white; margin-bottom: 5px;">
        🛡️ CREDINTEL
    </h1>
    <h3 style="color: #99F6E4 !important; margin-top: 0;">
        Credit Risk Intelligence Platform
    </h3>
    <p style="color: #E2E8F0;">
        Turn financial data into intelligence.
        Explore repayment behavior, analyze portfolio risk,
        and ask your AI analyst.
    </p>
</div>
""", unsafe_allow_html=True)


# --------------------------------------------------
# LOAD DATA AND BUILD DASHBOARD
# --------------------------------------------------

try:
    df = load_data()

    target = "default payment next month"

    if target not in df.columns:
        st.error("The expected target column was not found.")
        st.stop()

    # Create SQLite database for SQL-based analysis
    conn = sqlite3.connect(":memory:")
    df.to_sql("credit_clients", conn, index=False, if_exists="replace")

    # --------------------------------------------------
    # SIDEBAR FILTERS
    # --------------------------------------------------

    st.sidebar.markdown("# 🛡️ CredIntel")
    st.sidebar.caption("PORTFOLIO ANALYTICS")

    st.sidebar.divider()

    st.sidebar.subheader("🎛️ Dashboard Filters")

    min_balance = int(df["LIMIT_BAL"].min())
    max_balance = int(df["LIMIT_BAL"].max())

    selected_balance = st.sidebar.slider(
        "Credit limit range",
        min_value=min_balance,
        max_value=max_balance,
        value=(min_balance, max_balance),
        step=10000
    )

    repayment_options = sorted(
        df["PAY_0"].dropna().unique().tolist()
    )

    selected_statuses = st.sidebar.multiselect(
        "Repayment status (PAY_0)",
        options=repayment_options,
        default=repayment_options
    )

    st.sidebar.divider()

    st.sidebar.caption(
        "Historical Taiwan credit card dataset · UCI"
    )

    # --------------------------------------------------
    # FILTER DATA
    # --------------------------------------------------

    filtered_df = df[
        (df["LIMIT_BAL"] >= selected_balance[0]) &
        (df["LIMIT_BAL"] <= selected_balance[1]) &
        (df["PAY_0"].isin(selected_statuses))
    ].copy()

    filtered_df = make_credit_segments(filtered_df)

    # --------------------------------------------------
    # KPI METRICS
    # --------------------------------------------------

    st.subheader("📊 Portfolio Overview")

    total_customers = len(filtered_df)

    total_defaults = int(
        filtered_df[target].sum()
    ) if total_customers else 0

    default_rate = calculate_default_rate(filtered_df)

    average_limit = (
        filtered_df["LIMIT_BAL"].mean()
        if total_customers else 0
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Customers",
        f"{total_customers:,}"
    )

    col2.metric(
        "Observed Defaults",
        f"{total_defaults:,}"
    )

    col3.metric(
        "Default Rate",
        f"{default_rate:.2f}%"
    )

    col4.metric(
        "Average Credit Limit",
        f"{average_limit:,.0f}"
    )

    st.caption(
        "KPIs update automatically when you change the sidebar filters."
    )

    st.divider()

    # --------------------------------------------------
    # CHART 1: REPAYMENT STATUS
    # --------------------------------------------------

    st.subheader("📉 Default Risk by Repayment Status")

    if total_customers > 0:

        repayment_analysis = (
            filtered_df.groupby("PAY_0", observed=False)
            .agg(
                customers=(target, "count"),
                defaults=(target, "sum")
            )
            .reset_index()
        )

        repayment_analysis["default_rate"] = (
            repayment_analysis["defaults"]
            / repayment_analysis["customers"]
            * 100
        )

        repayment_analysis["PAY_0"] = (
            repayment_analysis["PAY_0"].astype(str)
        )

        fig1 = px.bar(
            repayment_analysis,
            x="PAY_0",
            y="default_rate",
            color="default_rate",
            color_continuous_scale=["#0D9488", "#5EEAD4"],
            text=repayment_analysis["default_rate"].round(1),
            hover_data=["customers", "defaults"],
            labels={
                "PAY_0": "Repayment Status",
                "default_rate": "Default Rate (%)",
                "customers": "Customers",
                "defaults": "Defaults"
            },
            title="Default Rate by Repayment Status"
        )

        fig1.update_traces(
            texttemplate="%{text}%",
            textposition="outside"
        )

        fig1.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1220",
            plot_bgcolor="#111C2E",
            font_color="#E2E8F0",
            coloraxis_showscale=False
        )

        st.plotly_chart(fig1, use_container_width=True)

    else:
        st.info("No customers match the selected filters.")

    st.divider()

    # --------------------------------------------------
    # CHART 2: CREDIT LIMIT SEGMENTS
    # --------------------------------------------------

    st.subheader("💳 Default Risk by Credit Limit")

    if total_customers > 0:

        credit_analysis = (
            filtered_df.groupby(
                "Credit Limit Segment",
                observed=False
            )
            .agg(
                customers=(target, "count"),
                defaults=(target, "sum")
            )
            .reset_index()
        )

        credit_analysis = credit_analysis[
            credit_analysis["customers"] > 0
        ]

        credit_analysis["default_rate"] = (
            credit_analysis["defaults"]
            / credit_analysis["customers"]
            * 100
        )

        credit_analysis["Credit Limit Segment"] = (
            credit_analysis["Credit Limit Segment"].astype(str)
        )

        fig2 = px.bar(
            credit_analysis,
            x="Credit Limit Segment",
            y="default_rate",
            color="default_rate",
            color_continuous_scale=["#0D9488", "#5EEAD4"],
            text=credit_analysis["default_rate"].round(1),
            hover_data=["customers", "defaults"],
            labels={
                "Credit Limit Segment": "Credit Limit",
                "default_rate": "Default Rate (%)",
                "customers": "Customers",
                "defaults": "Defaults"
            },
            title="Default Rate Across Credit Limit Segments"
        )

        fig2.update_traces(
            texttemplate="%{text}%",
            textposition="outside"
        )

        fig2.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0B1220",
            plot_bgcolor="#111C2E",
            font_color="#E2E8F0",
            coloraxis_showscale=False
        )

        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.info("No credit limit data is available for these filters.")

    st.divider()

    # --------------------------------------------------
    # SQL ANALYSIS
    # --------------------------------------------------

    st.subheader("🗄️ SQL Intelligence")

    sql_query = f"""
        SELECT
            COUNT(*) AS total_customers,
            SUM("{target}") AS total_defaults,
            ROUND(
                100.0 * SUM("{target}") / COUNT(*), 2
            ) AS default_rate_percent
        FROM credit_clients
        WHERE LIMIT_BAL >= {selected_balance[0]}
          AND LIMIT_BAL <= {selected_balance[1]}
    """

    # The SQL query above provides an overall credit-limit
    # comparison. The filtered dashboard KPIs also include PAY_0.
    sql_result = pd.read_sql_query(sql_query, conn)

    with st.expander("View SQL query result"):
        st.code(sql_query, language="sql")
        st.dataframe(sql_result, use_container_width=True)

    st.divider()

    # --------------------------------------------------
    # CSV DOWNLOAD
    # --------------------------------------------------

    st.subheader("📥 Export Filtered Data")

    csv_data = filtered_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="Download filtered data as CSV",
        data=csv_data,
        file_name="credintel_filtered_data.csv",
        mime="text/csv"
    )

    st.caption(
        f"Your export contains {len(filtered_df):,} filtered records."
    )

    st.divider()

    # --------------------------------------------------
    # GEMINI AI ANALYST
    # --------------------------------------------------

    st.subheader("🤖 Ask CredIntel AI")
    st.write(
        "Ask questions about the filtered portfolio and receive "
        "AI-generated explanations."
    )

    question = st.text_input(
        "Your question",
        placeholder="Example: What does the default rate tell us?"
    )

    if st.button("Ask CredIntel AI"):

        if not question.strip():
            st.warning("Please enter a question first.")

        elif total_customers == 0:
            st.warning("There is no filtered data to analyze.")

        else:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]

                client = genai.Client(api_key=api_key)

                repayment_summary = (
                    filtered_df.groupby("PAY_0")
                    .agg(
                        customers=(target, "count"),
                        defaults=(target, "sum")
                    )
                )

                repayment_summary["default_rate"] = (
                    repayment_summary["defaults"]
                    / repayment_summary["customers"]
                    * 100
                )

                repayment_context = (
                    repayment_summary.round(2).to_string()
                )

                credit_summary = (
                    credit_analysis.round(2).to_string()
                    if total_customers > 0
                    else "No credit limit data"
                )

                prompt = f"""
You are CredIntel AI, a responsible credit risk analytics assistant.

Analyze only the aggregate information supplied below.

USER QUESTION:
{question}

FILTERED PORTFOLIO:
Total customers: {total_customers}
Observed defaults: {total_defaults}
Observed default rate: {default_rate:.2f}%
Average credit limit: {average_limit:.2f}

REPAYMENT STATUS SUMMARY:
{repayment_context}

CREDIT LIMIT SUMMARY:
{credit_summary}

Instructions:
1. Answer the user's question clearly.
2. Use the supplied numbers where relevant.
3. Explain business implications in plain language.
4. Do not claim correlation proves causation.
5. Do not make lending decisions about individuals.
6. Mention limitations when appropriate.
7. Keep the answer concise and professional.
"""

                with st.spinner("CredIntel AI is analyzing the portfolio..."):

                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=prompt
                    )

                st.markdown("### 💡 AI Analysis")
                st.markdown(response.text)

            except KeyError:
                st.error(
                    "Gemini API key not found. "
                    "Please add GEMINI_API_KEY in Streamlit Secrets."
                )

            except Exception as e:
                st.error(f"AI request failed: {e}")

    st.divider()

    # --------------------------------------------------
    # RESPONSIBLE USE
    # --------------------------------------------------

    with st.expander("ℹ️ About this project and responsible use"):

        st.markdown("""
**Dataset:** UCI Default of Credit Card Clients.

**Purpose:** Educational credit risk analytics and portfolio exploration.

**Important limitations:**

- This dataset contains historical Taiwan credit card data.
- Historical patterns do not guarantee future outcomes.
- Associations do not establish causation.
- Results should not be used as the sole basis for lending decisions.
- This dashboard is not an individual credit scoring or approval system.
""")

    st.caption(
        "CredIntel | Credit Risk Intelligence · Built with Python, "
        "SQL, Streamlit, Plotly and Gemini AI"
    )

except Exception as e:
    st.error("The dashboard could not load successfully.")
    st.exception(e)
