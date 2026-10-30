
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from google import genai
from io import BytesIO
from datetime import datetime

# ==================================================
# 1. PAGE CONFIGURATION
# ==================================================

st.set_page_config(
    page_title="CredIntel 2.0 | Risk Intelligence",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================================================
# 2. PREMIUM DARK DESIGN
# ==================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    .stApp {
        background: #080F1D;
        color: #E2E8F0;
    }

    [data-testid="stSidebar"] {
        background: #101B2D;
        border-right: 1px solid #26364D;
    }

    h1, h2, h3 {
        color: #F8FAFC !important;
        font-weight: 700 !important;
    }

    p, label, .stMarkdown {
        color: #CBD5E1;
    }

    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #17263B, #111D30);
        border: 1px solid #293B54;
        padding: 19px;
        border-radius: 14px;
        box-shadow: 0 5px 18px rgba(0,0,0,0.15);
    }

    [data-testid="stMetricValue"] {
        color: #5EEAD4 !important;
        font-weight: 800;
    }

    [data-testid="stMetricLabel"] {
        color: #A8B7C9 !important;
    }

    .stButton > button {
        background: linear-gradient(90deg, #0D9488, #0F766E);
        color: white;
        border: none;
        border-radius: 9px;
        font-weight: 600;
        min-height: 42px;
    }

    .stButton > button:hover {
        background: #14B8A6;
        color: white;
        border: none;
    }

    [data-testid="stDownloadButton"] button {
        background: #172438;
        color: #5EEAD4;
        border: 1px solid #0D9488;
        border-radius: 9px;
    }

    div[data-baseweb="input"] input,
    div[data-baseweb="select"] > div {
        background: #172438;
        color: white;
    }

    [data-testid="stExpander"] {
        background: #111D30;
        border: 1px solid #293B54;
        border-radius: 12px;
    }

    hr {
        border-color: #293B54;
    }

    .hero {
        background: linear-gradient(115deg, #14243A, #0F766E);
        padding: 30px;
        border-radius: 17px;
        border: 1px solid #285B66;
        margin-bottom: 22px;
    }

    .hero-title {
        color: white;
        font-size: 35px;
        font-weight: 800;
        margin-bottom: 3px;
    }

    .hero-subtitle {
        color: #99F6E4;
        font-size: 15px;
        letter-spacing: 1px;
    }

    .insight-card {
        background: #172438;
        border: 1px solid #293B54;
        padding: 17px;
        border-radius: 12px;
        min-height: 110px;
    }

    .small-muted {
        color: #94A3B8;
        font-size: 12px;
    }
</style>
""", unsafe_allow_html=True)


# ==================================================
# 3. CONSTANTS AND DATA
# ==================================================

DATA_URL = (
    "https://archive.ics.uci.edu/ml/"
    "machine-learning-databases/00350/"
    "default%20of%20credit%20card%20clients.xls"
)

TARGET = "default payment next month"

PAYMENT_COLUMNS = [
    "PAY_0", "PAY_2", "PAY_3",
    "PAY_4", "PAY_5", "PAY_6"
]

PAYMENT_LABELS = {
    -2: "No consumption",
    -1: "Paid duly",
     0: "Revolving credit",
     1: "1 month delay",
     2: "2 months delay",
     3: "3 months delay",
     4: "4 months delay",
     5: "5 months delay",
     6: "6 months delay",
     7: "7 months delay",
     8: "8 months delay",
     9: "9+ months delay"
}


@st.cache_data
def load_data():
    data = pd.read_excel(DATA_URL, header=1)
    data.columns = data.columns.astype(str).str.strip()

    required = [
        TARGET, "LIMIT_BAL", "AGE", "SEX",
        "EDUCATION", "MARRIAGE", "PAY_0"
    ]

    missing = [c for c in required if c not in data.columns]

    if missing:
        raise ValueError(f"Missing expected columns: {missing}")

    return data


def add_segments(data):
    data = data.copy()

    bins = [0, 50000, 100000, 200000, 500000, float("inf")]

    labels = [
        "Under 50K",
        "50K–99K",
        "100K–199K",
        "200K–499K",
        "500K and above"
    ]

    data["Credit Limit Segment"] = pd.cut(
        data["LIMIT_BAL"],
        bins=bins,
        labels=labels,
        right=False
    )

    data["Repayment Description"] = (
        data["PAY_0"].map(PAYMENT_LABELS).fillna("Other")
    )

    return data


def default_rate(data):
    if len(data) == 0:
        return 0.0

    return float(data[TARGET].mean() * 100)


def aggregate_analysis(data, column):
    result = (
        data.groupby(column, observed=False)
        .agg(
            customers=(TARGET, "count"),
            defaults=(TARGET, "sum")
        )
        .reset_index()
    )

    result["default_rate"] = (
        result["defaults"] / result["customers"] * 100
    )

    return result


def plot_layout(fig, height=390):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#080F1D",
        plot_bgcolor="#111D30",
        font=dict(color="#E2E8F0"),
        height=height,
        margin=dict(l=20, r=20, t=55, b=20),
        legend_title_text=""
    )
    return fig


def create_pdf(data, rate, defaults, average_limit):
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    )
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm

    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm
    )

    styles = getSampleStyleSheet()
    story = []

    story.append(Paragraph(
        "CREDINTEL 2.0 — CREDIT RISK REPORT",
        styles["Title"]
    ))

    story.append(Spacer(1, 8))

    story.append(Paragraph(
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        styles["Normal"]
    ))

    story.append(Spacer(1, 15))

    table_data = [
        ["Metric", "Value"],
        ["Filtered customers", f"{len(data):,}"],
        ["Observed defaults", f"{defaults:,}"],
        ["Observed default rate", f"{rate:.2f}%"],
        ["Average credit limit", f"{average_limit:,.2f}"]
    ]

    table = Table(table_data, colWidths=[90 * mm, 65 * mm])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123B46")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#EDF4F5")),
        ("TEXTCOLOR", (0, 1), (-1, -1), colors.HexColor("#152536")),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 9)
    ]))

    story.append(table)
    story.append(Spacer(1, 18))

    story.append(Paragraph(
        "Responsible use and limitations",
        styles["Heading2"]
    ))

    story.append(Paragraph(
        "This report summarizes historical observations from the "
        "UCI Default of Credit Card Clients dataset. Historical "
        "associations do not establish causation or guarantee "
        "future outcomes. This report is not an individual lending "
        "recommendation or credit approval decision.",
        styles["BodyText"]
    ))

    doc.build(story)
    output.seek(0)

    return output.getvalue()


# ==================================================
# 4. HEADER
# ==================================================

st.markdown("""
<div class="hero">
    <div class="hero-title">🛡️ CREDINTEL 2.0</div>
    <div class="hero-subtitle">PREMIUM CREDIT RISK INTELLIGENCE</div>
    <p style="color:#E2E8F0; margin-top:16px;">
        Turn financial data into intelligence.
        Explore portfolio risk, discover patterns,
        and work with your AI analyst.
    </p>
</div>
""", unsafe_allow_html=True)


# ==================================================
# 5. LOAD APPLICATION
# ==================================================

try:
    original_df = load_data()
    df = add_segments(original_df)

    # --------------------------------------------------
    # SIDEBAR
    # --------------------------------------------------

    st.sidebar.markdown("# 🛡️ CREDINTEL")
    st.sidebar.caption("RISK INTELLIGENCE PLATFORM")
    st.sidebar.divider()

    st.sidebar.subheader("🎛️ Portfolio Filters")

    st.sidebar.caption("Credit limit")

    min_limit = int(df["LIMIT_BAL"].min())
    max_limit = int(df["LIMIT_BAL"].max())

    limit_range = st.sidebar.slider(
        "Credit limit range",
        min_value=min_limit,
        max_value=max_limit,
        value=(min_limit, max_limit),
        step=10000
    )

    age_range = st.sidebar.slider(
        "Customer age",
        min_value=int(df["AGE"].min()),
        max_value=int(df["AGE"].max()),
        value=(int(df["AGE"].min()), int(df["AGE"].max()))
    )

    sex_options = sorted(df["SEX"].dropna().unique().tolist())

    selected_sex = st.sidebar.multiselect(
        "Gender",
        options=sex_options,
        default=sex_options,
        format_func=lambda x: {
            1: "Male",
            2: "Female"
        }.get(x, str(x))
    )

    education_options = sorted(
        df["EDUCATION"].dropna().unique().tolist()
    )

    selected_education = st.sidebar.multiselect(
        "Education category",
        options=education_options,
        default=education_options
    )

    marriage_options = sorted(
        df["MARRIAGE"].dropna().unique().tolist()
    )

    selected_marriage = st.sidebar.multiselect(
        "Marital status category",
        options=marriage_options,
        default=marriage_options
    )

    repayment_options = sorted(
        df["PAY_0"].dropna().unique().tolist()
    )

    selected_repayment = st.sidebar.multiselect(
        "Most recent repayment status",
        options=repayment_options,
        default=repayment_options,
        format_func=lambda x: PAYMENT_LABELS.get(x, str(x))
    )

    st.sidebar.divider()

    if st.sidebar.button("↻ Reset all filters", use_container_width=True):
        st.rerun()

    st.sidebar.caption(
        "Dataset: UCI Default of Credit Card Clients"
    )

    # --------------------------------------------------
    # FILTER DATA
    # --------------------------------------------------

    filtered = df[
        df["LIMIT_BAL"].between(limit_range[0], limit_range[1])
        & df["AGE"].between(age_range[0], age_range[1])
        & df["SEX"].isin(selected_sex)
        & df["EDUCATION"].isin(selected_education)
        & df["MARRIAGE"].isin(selected_marriage)
        & df["PAY_0"].isin(selected_repayment)
    ].copy()

    n = len(filtered)
    defaults = int(filtered[TARGET].sum()) if n else 0
    rate = default_rate(filtered)

    avg_limit = (
        float(filtered["LIMIT_BAL"].mean()) if n else 0
    )

    # --------------------------------------------------
    # NAVIGATION
    # --------------------------------------------------

    page = st.radio(
        "Navigation",
        [
            "Executive Overview",
            "Risk Analytics",
            "AI Analyst",
            "SQL Explorer",
            "Report Center"
        ],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.divider()

    # ==================================================
    # PAGE 1: EXECUTIVE OVERVIEW
    # ==================================================

    if page == "Executive Overview":

        st.title("Executive Overview")
        st.caption(
            "A high-level view of your selected portfolio."
        )

        k1, k2, k3, k4 = st.columns(4)

        k1.metric("Customers", f"{n:,}")
        k2.metric("Observed Defaults", f"{defaults:,}")
        k3.metric("Default Rate", f"{rate:.2f}%")
        k4.metric("Average Credit Limit", f"{avg_limit:,.0f}")

        st.divider()

        left, right = st.columns(2)

        if n:
            repayment = aggregate_analysis(filtered, "PAY_0")
            repayment["Status"] = repayment["PAY_0"].map(
                PAYMENT_LABELS
            ).fillna(repayment["PAY_0"].astype(str))

            with left:
                st.subheader("Repayment Risk")

                fig = px.bar(
                    repayment,
                    x="Status",
                    y="default_rate",
                    color="default_rate",
                    color_continuous_scale=["#0D9488", "#5EEAD4"],
                    hover_data=["customers", "defaults"],
                    labels={
                        "Status": "Repayment status",
                        "default_rate": "Default rate (%)"
                    }
                )

                fig.update_layout(coloraxis_showscale=False)
                st.plotly_chart(
                    plot_layout(fig),
                    use_container_width=True
                )

            credit = aggregate_analysis(
                filtered, "Credit Limit Segment"
            )

            credit = credit[credit["customers"] > 0]

            with right:
                st.subheader("Credit Limit Risk")

                fig2 = px.bar(
                    credit,
                    x="Credit Limit Segment",
                    y="default_rate",
                    color="default_rate",
                    color_continuous_scale=["#0D9488", "#5EEAD4"],
                    hover_data=["customers", "defaults"]
                )

                fig2.update_layout(coloraxis_showscale=False)

                st.plotly_chart(
                    plot_layout(fig2),
                    use_container_width=True
                )

            st.subheader("Portfolio Distribution")

            donut_data = pd.DataFrame({
                "Outcome": ["No observed default", "Observed default"],
                "Customers": [n - defaults, defaults]
            })

            donut = px.pie(
                donut_data,
                names="Outcome",
                values="Customers",
                hole=0.68,
                color_discrete_sequence=["#0D9488", "#F59E0B"]
            )

            donut.update_traces(
                textposition="inside",
                textinfo="percent+label"
            )

            st.plotly_chart(
                plot_layout(donut, 350),
                use_container_width=True
            )

        else:
            st.warning("No records match your selected filters.")

    # ==================================================
    # PAGE 2: RISK ANALYTICS
    # ==================================================

    elif page == "Risk Analytics":

        st.title("Advanced Risk Analytics")
        st.caption(
            "Explore customer segments and repayment patterns."
        )

        if n == 0:
            st.warning("No data available for the selected filters.")

        else:
            tab1, tab2, tab3 = st.tabs([
                "Repayment Analysis",
                "Customer Segments",
                "Correlation"
            ])

            with tab1:
                st.subheader("Repayment Status Analysis")

                payment_data = filtered[PAYMENT_COLUMNS].copy()
                payment_data[TARGET] = filtered[TARGET].values

                long_payment = payment_data.melt(
                    id_vars=[TARGET],
                    value_vars=PAYMENT_COLUMNS,
                    var_name="Month",
                    value_name="Repayment Status"
                )

                heat_data = (
                    long_payment.groupby(
                        ["Month", "Repayment Status"]
                    )[TARGET]
                    .mean()
                    .reset_index()
                )

                heat_data["Default Rate (%)"] = (
                    heat_data[TARGET] * 100
                )

                heat = px.density_heatmap(
                    heat_data,
                    x="Month",
                    y="Repayment Status",
                    z="Default Rate (%)",
                    histfunc="avg",
                    color_continuous_scale="Teal"
                )

                st.plotly_chart(
                    plot_layout(heat, 440),
                    use_container_width=True
                )

                st.caption(
                    "Historical default rate by repayment status "
                    "across the recorded months."
                )

            with tab2:
                st.subheader("Customer Segment Comparison")

                segment_choice = st.selectbox(
                    "Choose a segment",
                    ["AGE", "SEX", "EDUCATION", "MARRIAGE",
                     "Credit Limit Segment"]
                )

                segment_data = aggregate_analysis(
                    filtered, segment_choice
                )

                segment_data[segment_choice] = (
                    segment_data[segment_choice].astype(str)
                )

                fig = px.bar(
                    segment_data,
                    x=segment_choice,
                    y="default_rate",
                    color="default_rate",
                    hover_data=["customers", "defaults"],
                    color_continuous_scale=["#0D9488", "#5EEAD4"]
                )

                fig.update_layout(coloraxis_showscale=False)

                st.plotly_chart(
                    plot_layout(fig),
                    use_container_width=True
                )

                st.dataframe(
                    segment_data,
                    use_container_width=True,
                    hide_index=True
                )

            with tab3:
                st.subheader("Feature Correlation")

                numeric = filtered.select_dtypes(
                    include="number"
                ).copy()

                corr = numeric.corr()

                fig = px.imshow(
                    corr,
                    color_continuous_scale="RdBu_r",
                    zmin=-1,
                    zmax=1,
                    aspect="auto"
                )

                st.plotly_chart(
                    plot_layout(fig, 650),
                    use_container_width=True
                )

                st.caption(
                    "Correlation describes association, not causation."
                )

    # ==================================================
    # PAGE 3: AI ANALYST
    # ==================================================

    elif page == "AI Analyst":

        st.title("🤖 CredIntel AI Analyst")
        st.caption(
            "Ask questions about your currently filtered portfolio."
        )

        if n == 0:
            st.warning("No filtered records are available.")

        else:
            repayment = aggregate_analysis(filtered, "PAY_0")

            credit = aggregate_analysis(
                filtered, "Credit Limit Segment"
            )

            context = f"""
PORTFOLIO SUMMARY
Customers: {n}
Observed defaults: {defaults}
Observed default rate: {rate:.2f}%
Average credit limit: {avg_limit:.2f}

REPAYMENT ANALYSIS:
{repayment.round(2).to_string(index=False)}

CREDIT LIMIT ANALYSIS:
{credit.round(2).to_string(index=False)}
"""

            if "credintel_chat" not in st.session_state:
                st.session_state.credintel_chat = []

            for message in st.session_state.credintel_chat:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            question = st.chat_input(
                "Ask about default patterns, repayment risk..."
            )

            if question:

                st.session_state.credintel_chat.append({
                    "role": "user",
                    "content": question
                })

                with st.chat_message("user"):
                    st.markdown(question)

                try:
                    api_key = st.secrets["GEMINI_API_KEY"]
                    client = genai.Client(api_key=api_key)

                    prompt = f"""
You are CredIntel AI, a professional and responsible
banking analytics assistant.

Use only the aggregate portfolio information below.

{context}

USER QUESTION:
{question}

Answer professionally and clearly.
Explain business implications.
Do not claim causation from correlation.
Do not make individual lending decisions.
Do not invent statistics.
Mention limitations where relevant.
"""

                    with st.chat_message("assistant"):
                        with st.spinner("Analyzing portfolio..."):
                            response = client.models.generate_content(
                                model="gemini-3.5-flash",
                                contents=prompt
                            )

                        answer = response.text or (
                            "The AI returned an empty response."
                        )

                        st.markdown(answer)

                    st.session_state.credintel_chat.append({
                        "role": "assistant",
                        "content": answer
                    })

                except Exception as e:
                    st.error(f"AI request failed: {e}")

            if st.button("Clear conversation"):
                st.session_state.credintel_chat = []
                st.rerun()

    # ==================================================
    # PAGE 4: SAFE SQL EXPLORER
    # ==================================================

    elif page == "SQL Explorer":

        st.title("🗄️ SQL Explorer")
        st.caption(
            "Explore the dataset using read-only SELECT queries."
        )

        conn = sqlite3.connect(":memory:")
        filtered.to_sql(
            "credit_clients",
            conn,
            index=False,
            if_exists="replace"
        )

        conn.execute("PRAGMA query_only = ON")

        example = """SELECT
    PAY_0,
    COUNT(*) AS customers,
    SUM("default payment next month") AS defaults,
    ROUND(
        100.0 * SUM("default payment next month") / COUNT(*), 2
    ) AS default_rate
FROM credit_clients
GROUP BY PAY_0
ORDER BY default_rate DESC;"""

        query = st.text_area(
            "SQL query",
            value=example,
            height=220
        )

        st.caption(
            "Only one read-only SELECT query is allowed. "
            "Queries run against the currently filtered data."
        )

        if st.button("▶ Run SQL query"):

            cleaned = query.strip().rstrip(";").strip()

            if not cleaned.lower().startswith("select "):
                st.error("Only SELECT queries are permitted.")

            elif ";" in cleaned:
                st.error("Multiple SQL statements are not permitted.")

            else:
                try:
                    result = pd.read_sql_query(cleaned, conn)

                    st.success(
                        f"Query completed: {len(result):,} rows returned."
                    )

                    st.dataframe(
                        result,
                        use_container_width=True,
                        hide_index=True
                    )

                    st.download_button(
                        "Download SQL results",
                        result.to_csv(index=False).encode("utf-8"),
                        "credintel_sql_results.csv",
                        "text/csv"
                    )

                except Exception as e:
                    st.error(f"SQL error: {e}")

        conn.close()

    # ==================================================
    # PAGE 5: REPORT CENTER
    # ==================================================

    elif page == "Report Center":

        st.title("📑 Report Center")
        st.caption(
            "Export the currently filtered portfolio analysis."
        )

        st.subheader("Report Summary")

        r1, r2, r3 = st.columns(3)

        r1.metric("Customers", f"{n:,}")
        r2.metric("Defaults", f"{defaults:,}")
        r3.metric("Default Rate", f"{rate:.2f}%")

        if n:

            st.subheader("Filtered Data Preview")

            st.dataframe(
                filtered.head(100),
                use_container_width=True
            )

            st.download_button(
                "⬇ Download filtered data (CSV)",
                filtered.to_csv(index=False).encode("utf-8"),
                "credintel_portfolio.csv",
                "text/csv",
                use_container_width=True
            )

            try:
                pdf = create_pdf(
                    filtered, rate, defaults, avg_limit
                )

                st.download_button(
                    "⬇ Download executive report (PDF)",
                    pdf,
                    "credintel_executive_report.pdf",
                    "application/pdf",
                    use_container_width=True
                )

            except ImportError:
                st.warning(
                    "PDF dependency missing. Add reportlab "
                    "to requirements.txt and redeploy."
                )

        else:
            st.info("No records are available to export.")

    # ==================================================
    # FOOTER AND RESPONSIBLE USE
    # ==================================================

    st.divider()

    with st.expander("About CredIntel and Responsible Use"):

        st.markdown("""
**Dataset:** UCI Default of Credit Card Clients.

**Purpose:** Educational credit risk analytics and portfolio exploration.

**Dataset limitations:**
- Historical Taiwan credit card data.
- Historical patterns do not guarantee future outcomes.
- Correlation does not establish causation.
- The data may not represent other countries or current customers.

**Responsible AI:**
- AI explanations are informational, not financial advice.
- This application is not an individual credit scoring system.
- Never use this dashboard as the sole basis for lending decisions.
""")

    st.caption(
        "CREDINTEL 2.0 | Python · SQL · Streamlit · Plotly · Gemini AI"
    )

except Exception as e:
    st.error("CredIntel could not load.")
    st.exception(e)
