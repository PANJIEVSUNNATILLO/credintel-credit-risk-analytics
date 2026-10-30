
import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO

# --------------------------------------------------
# PAGE CONFIGURATION
# --------------------------------------------------

st.set_page_config(
    page_title="CredIntel | Credit Risk Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --------------------------------------------------
# CORPORATE NAVY DESIGN
# --------------------------------------------------

st.markdown("""
<style>
.stApp {
    background: #0B1730;
    color: #F3F6FC;
}
[data-testid="stHeader"] {
    background: #0B1730;
}
[data-testid="stSidebar"] {
    background: #102344;
    border-right: 1px solid #263E65;
}
[data-testid="stSidebar"] * {
    color: #EAF1FC;
}
h1, h2, h3, h4 {
    color: #F4F7FD !important;
}
p, label, .stMarkdown {
    color: #D3DEEF;
}
[data-testid="stMetric"] {
    background: #142B50;
    border: 1px solid #29456F;
    padding: 18px;
    border-radius: 12px;
}
[data-testid="stMetricLabel"] {
    color: #AFC4E3 !important;
}
[data-testid="stMetricValue"] {
    color: #FFFFFF !important;
}
div.stButton > button {
    background: #2474D2;
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 600;
}
div.stButton > button:hover {
    background: #3689EB;
    color: white;
}
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div {
    background: #142B50;
    border-color: #34537E;
}
.stTextArea textarea, .stTextInput input {
    background: #142B50;
    color: white;
}
hr {
    border-color: #29456F;
}
div[data-testid="stTabs"] button {
    color: #C9D8ED;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    color: #69B2FF;
}
[data-testid="stDataFrame"] {
    border: 1px solid #29456F;
    border-radius: 10px;
}
.small-note {
    color: #AFC4E3;
    font-size: 13px;
}
.section-card {
    background: #142B50;
    border: 1px solid #29456F;
    border-radius: 12px;
    padding: 18px;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------
# DATA LOADING
# --------------------------------------------------

@st.cache_data
def load_data():
    url = (
        "https://archive.ics.uci.edu/ml/"
        "machine-learning-databases/00350/"
        "default%20of%20credit%20card%20clients.xls"
    )
    data = pd.read_excel(url, header=1)
    data.columns = data.columns.astype(str).str.strip()
    return data

try:
    df = load_data()
except Exception as e:
    st.error(f"Could not load the credit dataset: {e}")
    st.stop()

TARGET = "default payment next month"

if TARGET not in df.columns:
    st.error("The expected target column was not found in the dataset.")
    st.stop()

# --------------------------------------------------
# DATABASE
# --------------------------------------------------

@st.cache_resource
def create_database():
    database = sqlite3.connect(":memory:", check_same_thread=False)
    df.to_sql("credit_clients", database, if_exists="replace", index=False)
    database.execute("PRAGMA query_only = ON")
    return database

conn = create_database()

# --------------------------------------------------
# HELPERS
# --------------------------------------------------

def format_money(value):
    return f"${value:,.0f}"

def make_chart(fig, height=380):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#142B50",
        plot_bgcolor="#142B50",
        font=dict(color="#EAF1FC"),
        height=height,
        margin=dict(l=30, r=25, t=45, b=35),
        legend=dict(font=dict(color="#D3DEEF"))
    )
    fig.update_xaxes(gridcolor="#29456F", zerolinecolor="#29456F")
    fig.update_yaxes(gridcolor="#29456F", zerolinecolor="#29456F")
    st.plotly_chart(fig, use_container_width=True)

def calculate_default_rate(data):
    if len(data) == 0:
        return 0
    return data[TARGET].mean() * 100

def get_ai_answer(question, context):
    try:
        from google import genai

        api_key = st.secrets.get("GEMINI_API_KEY")
        if not api_key:
            return "Gemini API key not found. Add GEMINI_API_KEY in Streamlit Secrets."

        client = genai.Client(api_key=api_key)

        prompt = f"""
You are CredIntel, a professional banking credit-risk analyst.

Use only the supplied dataset context to support factual conclusions.
Explain insights clearly for banking management.
Do not invent statistics or claim that correlations prove causation.
Do not make individual lending decisions.

DATA CONTEXT:
{context}

USER QUESTION:
{question}
"""
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt
        )
        return response.text

    except Exception as e:
        return f"AI request failed: {str(e)}"

# --------------------------------------------------
# SIDEBAR
# --------------------------------------------------

with st.sidebar:
    st.markdown("## 🏦 CREDINTEL")
    st.caption("CREDIT RISK INTELLIGENCE")
    st.divider()

    page = st.radio(
        "NAVIGATION",
        [
            "Executive Overview",
            "Credit Risk Analytics",
            "AI Intelligence",
            "SQL Explorer",
            "Research & Reports"
        ]
    )

    st.divider()
    st.markdown("### DATA SOURCE")
    st.caption("UCI Default of Credit Card Clients")
    st.caption(f"{len(df):,} historical customer records")

    st.divider()
    st.markdown("### PROJECT STATUS")
    st.success("Dataset loaded")
    st.success("SQL database ready")

# --------------------------------------------------
# FILTERS
# --------------------------------------------------

st.sidebar.markdown("### PORTFOLIO FILTERS")

filtered = df.copy()

min_limit = int(df["LIMIT_BAL"].min())
max_limit = int(df["LIMIT_BAL"].max())

limit_range = st.sidebar.slider(
    "Credit limit",
    min_limit,
    max_limit,
    (min_limit, max_limit),
    step=10000
)

filtered = filtered[
    filtered["LIMIT_BAL"].between(limit_range[0], limit_range[1])
]

age_min = int(df["AGE"].min())
age_max = int(df["AGE"].max())

age_range = st.sidebar.slider(
    "Customer age",
    age_min,
    age_max,
    (age_min, age_max)
)

filtered = filtered[
    filtered["AGE"].between(age_range[0], age_range[1])
]

gender_options = sorted(df["SEX"].dropna().unique().tolist())
gender_selected = st.sidebar.multiselect(
    "Gender",
    gender_options,
    default=gender_options
)
filtered = filtered[filtered["SEX"].isin(gender_selected)]

education_options = sorted(df["EDUCATION"].dropna().unique().tolist())
education_selected = st.sidebar.multiselect(
    "Education",
    education_options,
    default=education_options
)
filtered = filtered[filtered["EDUCATION"].isin(education_selected)]

marriage_options = sorted(df["MARRIAGE"].dropna().unique().tolist())
marriage_selected = st.sidebar.multiselect(
    "Marital status",
    marriage_options,
    default=marriage_options
)
filtered = filtered[filtered["MARRIAGE"].isin(marriage_selected)]

st.sidebar.caption(f"Filtered records: {len(filtered):,}")

# --------------------------------------------------
# COMMON HEADER
# --------------------------------------------------

st.markdown("# CREDINTEL")
st.markdown("### Credit Risk Intelligence Platform")
st.caption(
    "Portfolio monitoring  |  Risk analytics  |  AI-powered insights"
)
st.divider()

# --------------------------------------------------
# EXECUTIVE OVERVIEW
# --------------------------------------------------

if page == "Executive Overview":

    st.subheader("Executive Overview")
    st.caption("A consolidated view of the selected credit portfolio.")

    total = len(filtered)
    defaults = int(filtered[TARGET].sum()) if total else 0
    default_rate = calculate_default_rate(filtered)
    avg_limit = filtered["LIMIT_BAL"].mean() if total else 0

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("CUSTOMERS", f"{total:,}")
    c2.metric("DEFAULTED CUSTOMERS", f"{defaults:,}")
    c3.metric("DEFAULT RATE", f"{default_rate:.2f}%")
    c4.metric("AVERAGE CREDIT LIMIT", format_money(avg_limit))

    st.divider()

    left, right = st.columns(2)

    with left:
        st.markdown("#### Default distribution")
        if total:
            distribution = (
                filtered[TARGET]
                .value_counts()
                .rename(index={0: "No default", 1: "Default"})
                .reset_index()
            )
            distribution.columns = ["Status", "Customers"]

            fig = px.pie(
                distribution,
                names="Status",
                values="Customers",
                hole=0.65,
                color="Status",
                color_discrete_map={
                    "No default": "#3689EB",
                    "Default": "#F0A34A"
                }
            )
            make_chart(fig)

    with right:
        st.markdown("#### Default rate by repayment status")
        if total:
            repayment = (
                filtered.groupby("PAY_0")[TARGET]
                .mean()
                .mul(100)
                .reset_index()
            )
            repayment.columns = ["Repayment status", "Default rate"]

            fig = px.bar(
                repayment,
                x="Repayment status",
                y="Default rate",
                color="Default rate",
                color_continuous_scale="Blues"
            )
            make_chart(fig)

    st.markdown("#### Portfolio snapshot")

    if total:
        summary = pd.DataFrame({
            "Metric": [
                "Total customers",
                "Defaulted customers",
                "Observed default rate",
                "Average credit limit",
                "Average customer age"
            ],
            "Value": [
                f"{total:,}",
                f"{defaults:,}",
                f"{default_rate:.2f}%",
                format_money(avg_limit),
                f"{filtered['AGE'].mean():.1f} years"
            ]
        })
        st.dataframe(summary, use_container_width=True, hide_index=True)
    else:
        st.warning("No customers match the selected filters.")

# --------------------------------------------------
# CREDIT RISK ANALYTICS
# --------------------------------------------------

elif page == "Credit Risk Analytics":

    st.subheader("Credit Risk Analytics")
    st.caption("Explore repayment behavior, customer groups and portfolio patterns.")

    tab1, tab2, tab3 = st.tabs([
        "Repayment Behavior",
        "Customer Segments",
        "Correlation Analysis"
    ])

    with tab1:
        st.markdown("#### Default rate by repayment status")

        repayment = (
            filtered.groupby("PAY_0")
            .agg(
                Customers=(TARGET, "count"),
                Defaults=(TARGET, "sum"),
                Default_Rate=(TARGET, "mean")
            )
            .reset_index()
        )
        repayment["Default_Rate"] *= 100

        fig = px.bar(
            repayment,
            x="PAY_0",
            y="Default_Rate",
            color="Default_Rate",
            color_continuous_scale="Blues",
            hover_data=["Customers", "Defaults"]
        )
        make_chart(fig)

        st.dataframe(repayment, use_container_width=True, hide_index=True)

    with tab2:
        st.markdown("#### Default rate by credit limit segment")

        bins = [0, 50000, 100000, 200000, 500000, float("inf")]
        labels = [
            "Under 50K",
            "50K–99K",
            "100K–199K",
            "200K–499K",
            "500K and above"
        ]

        segment_data = filtered.copy()
        segment_data["Credit Segment"] = pd.cut(
            segment_data["LIMIT_BAL"],
            bins=bins,
            labels=labels,
            right=False
        )

        segment = (
            segment_data.groupby("Credit Segment", observed=False)
            .agg(
                Customers=(TARGET, "count"),
                Defaults=(TARGET, "sum"),
                Default_Rate=(TARGET, "mean")
            )
            .reset_index()
        )
        segment["Default_Rate"] *= 100

        fig = px.bar(
            segment,
            x="Credit Segment",
            y="Default_Rate",
            color="Default_Rate",
            color_continuous_scale="Blues"
        )
        make_chart(fig)

        st.dataframe(segment, use_container_width=True, hide_index=True)

    with tab3:
        st.markdown("#### Selected variable correlations")

        numeric = filtered.select_dtypes(include="number")
        correlation = numeric.corr()

        fig = px.imshow(
            correlation,
            text_auto=".2f",
            color_continuous_scale="RdBu_r",
            aspect="auto"
        )
        make_chart(fig, height=600)

        st.caption(
            "Correlation indicates statistical association, not causation."
        )

# --------------------------------------------------
# AI INTELLIGENCE
# --------------------------------------------------

elif page == "AI Intelligence":

    st.subheader("CredIntel AI Intelligence")
    st.caption("Ask questions about portfolio performance and credit risk.")

    total = len(filtered)
    defaults = int(filtered[TARGET].sum()) if total else 0
    rate = calculate_default_rate(filtered)

    context = f"""
Number of customers: {total}
Number of defaults: {defaults}
Observed default rate: {rate:.2f}%
Average credit limit: {filtered['LIMIT_BAL'].mean() if total else 0:.2f}
Average age: {filtered['AGE'].mean() if total else 0:.2f}
"""

    st.markdown('<div class="section-card">', unsafe_allow_html=True)
    st.markdown("**AI Analyst**")
    st.write("Ask a question about the currently filtered portfolio.")
    st.markdown('</div>', unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    question = st.chat_input("Ask CredIntel about credit risk...")

    if question:
        st.session_state.chat_history.append({
            "role": "user",
            "content": question
        })

        with st.chat_message("user"):
            st.markdown(question)

        with st.chat_message("assistant"):
            with st.spinner("Analyzing portfolio data..."):
                answer = get_ai_answer(question, context)
                st.markdown(answer)

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": answer
        })

    if st.button("Clear conversation"):
        st.session_state.chat_history = []
        st.rerun()

# --------------------------------------------------
# SQL EXPLORER
# --------------------------------------------------

elif page == "SQL Explorer":

    st.subheader("SQL Explorer")
    st.caption("Run read-only SQL queries against the credit_clients table.")

    example_query = """SELECT
    PAY_0,
    COUNT(*) AS customers,
    SUM("default payment next month") AS defaults,
    ROUND(
        100.0 * SUM("default payment next month") / COUNT(*), 2
    ) AS default_rate
FROM credit_clients
GROUP BY PAY_0
ORDER BY default_rate DESC"""

    query = st.text_area(
        "SQL Query",
        value=example_query,
        height=220
    )

    if st.button("▶ Execute SQL", use_container_width=True):

        cleaned = query.strip().rstrip(";").strip()
        first_word = cleaned.split(maxsplit=1)[0].upper() if cleaned else ""

        if first_word != "SELECT":
            st.error("Only SELECT queries are permitted.")
        elif ";" in cleaned:
            st.error("Multiple SQL statements are not permitted.")
        else:
            try:
                result = pd.read_sql_query(cleaned, conn)
                st.success("Query executed successfully.")
                st.dataframe(result, use_container_width=True)
                st.download_button(
                    "Download query results",
                    result.to_csv(index=False),
                    "credintel_sql_results.csv",
                    "text/csv"
                )
            except Exception as e:
                st.error(f"SQL error: {e}")

    st.info(
        "Available table: credit_clients. "
        "Database writes are disabled."
    )

# --------------------------------------------------
# RESEARCH & REPORTS
# --------------------------------------------------

elif page == "Research & Reports":

    st.subheader("Research & Reports")
    st.caption("Export portfolio data and generate a management summary.")

    st.markdown("#### Customer data export")

    st.download_button(
        "Download filtered data (CSV)",
        filtered.to_csv(index=False),
        "credintel_filtered_customers.csv",
        "text/csv",
        use_container_width=True
    )

    st.divider()

    st.markdown("#### Executive PDF report")

    if st.button("Generate PDF Report", use_container_width=True):

        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle
            )
            from reportlab.lib import colors
            from reportlab.lib.styles import getSampleStyleSheet

            buffer = BytesIO()
            document = SimpleDocTemplate(buffer, pagesize=A4)
            styles = getSampleStyleSheet()

            total = len(filtered)
            defaults = int(filtered[TARGET].sum()) if total else 0
            rate = calculate_default_rate(filtered)

            story = [
                Paragraph("CredIntel Credit Risk Report", styles["Title"]),
                Spacer(1, 20),
                Paragraph("Executive Portfolio Summary", styles["Heading2"]),
                Spacer(1, 10)
            ]

            report_data = [
                ["Metric", "Value"],
                ["Customers", f"{total:,}"],
                ["Defaulted customers", f"{defaults:,}"],
                ["Observed default rate", f"{rate:.2f}%"],
                [
                    "Average credit limit",
                    format_money(filtered["LIMIT_BAL"].mean() if total else 0)
                ],
                [
                    "Average age",
                    f"{filtered['AGE'].mean():.1f}" if total else "N/A"
                ]
            ]

            table = Table(report_data, colWidths=[250, 180])
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#17365D")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("PADDING", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke)
            ]))

            story.extend([
                table,
                Spacer(1, 20),
                Paragraph("Responsible Use and Limitations", styles["Heading2"]),
                Paragraph(
                    "This report analyzes historical credit card data from Taiwan. "
                    "Observed statistical relationships do not establish causation. "
                    "This analysis is for educational and research purposes and "
                    "must not be used as the sole basis for individual lending decisions.",
                    styles["BodyText"]
                )
            ])

            document.build(story)
            buffer.seek(0)

            st.download_button(
                "Download PDF Report",
                buffer.getvalue(),
                "credintel_executive_report.pdf",
                "application/pdf",
                use_container_width=True
            )

        except Exception as e:
            st.error(f"Could not generate PDF: {e}")

    st.divider()
    st.markdown("#### Dataset information")
    st.write("Source: UCI Machine Learning Repository")
    st.write("Dataset: Default of Credit Card Clients")
    st.write("Records: 30,000 historical customers")
    st.write("Target: Default payment next month")

# --------------------------------------------------
# FOOTER
# --------------------------------------------------

st.divider()

st.caption(
    "CREDINTEL | Credit Risk Intelligence Platform"
)

st.caption(
    "Educational and analytical use only. Historical dataset; "
    "not a lending recommendation or an individual credit decision."
)
