
import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import re
from io import BytesIO
from datetime import datetime
from xml.sax.saxutils import escape

# =========================================================
# PAGE CONFIGURATION
# =========================================================
def make_chart(fig, height=400):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0B1730",
        plot_bgcolor="#0B1730",
        font=dict(color="white"),
        height=height,
        margin=dict(l=20, r=20, t=50, b=20)
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={"displayModeBar": True}
    )


st.set_page_config(
    page_title="CredIntel | Credit Risk Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# CORPORATE DARK BLUE DESIGN
# =========================================================

st.markdown("""
<style>
    .stApp {
        background-color: #0B1730;
        color: #FFFFFF;
    }

    [data-testid="stSidebar"] {
        background-color: #102344;
    }

    [data-testid="stMetric"] {
        background-color: #142B50;
        border: 1px solid #29466F;
        padding: 18px;
        border-radius: 12px;
    }

    [data-testid="stMetricLabel"] {
        color: #B8C9E2;
    }

    [data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    h1, h2, h3 {
        color: #FFFFFF !important;
    }

    p, label, span {
        color: #DCE6F4;
    }

    .credintel-card {
        background: #142B50;
        border: 1px solid #29466F;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 12px;
    }

    .credintel-caption {
        color: #9DB5D5;
        font-size: 13px;
    }

    div.stButton > button {
        background-color: #2474D2;
        color: white;
        border: none;
        border-radius: 8px;
        font-weight: 600;
    }

    div.stButton > button:hover {
        background-color: #3989E8;
        color: white;
        border: none;
    }

    div[data-testid="stDownloadButton"] button {
        background-color: #2474D2;
        color: white;
        border-radius: 8px;
        border: none;
    }

    hr {
        border-color: #29466F;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# CONSTANTS
# =========================================================

DATA_URL = (
    "https://archive.ics.uci.edu/ml/"
    "machine-learning-databases/00350/"
    "default%20of%20credit%20card%20clients.xls"
)

TARGET = "default payment next month"
GEMINI_MODEL = "gemini-3.5-flash"

# =========================================================
# DATA LOADING
# =========================================================

@st.cache_data
def load_data():
    data = pd.read_excel(DATA_URL, header=1)

    data.columns = data.columns.astype(str).str.strip()

    if TARGET not in data.columns:
        raise ValueError(
            f"Target column '{TARGET}' was not found."
        )

    return data


try:
    df = load_data()

except Exception as e:
    st.error("CredIntel could not load the dataset.")
    st.exception(e)
    st.stop()


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def calculate_default_rate(data):
    if len(data) == 0:
        return 0.0

    return float(data[TARGET].mean() * 100)


def format_money(value):
    if pd.isna(value):
        return "N/A"

    return f"{value:,.0f}"


def get_gemini_client():
    try:
        api_key = st.secrets.get("GEMINI_API_KEY", "")

        if not api_key:
            return None

        from google import genai

        return genai.Client(api_key=api_key)

    except Exception:
        return None


def ask_gemini(prompt):
    client = get_gemini_client()

    if client is None:
        return (
            "Gemini is not configured. Add GEMINI_API_KEY "
            "to Streamlit Community Cloud Secrets."
        )

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt
    )

    return response.text or "No response was returned."


def make_portfolio_context(data):
    total = len(data)
    defaults = int(data[TARGET].sum()) if total else 0

    rate = calculate_default_rate(data)

    average_limit = (
        data["LIMIT_BAL"].mean() if total else 0
    )

    median_limit = (
        data["LIMIT_BAL"].median() if total else 0
    )

    average_age = (
        data["AGE"].mean() if total else 0
    )

    return {
        "total": total,
        "defaults": defaults,
        "non_defaults": total - defaults,
        "rate": rate,
        "average_limit": average_limit,
        "median_limit": median_limit,
        "average_age": average_age
    }


# =========================================================
# SIDEBAR
# =========================================================

st.sidebar.markdown("# CREDINTEL")
st.sidebar.caption("CREDIT RISK INTELLIGENCE")
st.sidebar.divider()

pages = [
    "Executive Overview",
    "Credit Risk Analytics",
    "AI Intelligence",
    "SQL Explorer",
    "Research & Reports"
]

page = st.sidebar.radio(
    "NAVIGATION",
    pages
)

st.sidebar.divider()
st.sidebar.markdown("### Portfolio Filters")

limit_min = int(df["LIMIT_BAL"].min())
limit_max = int(df["LIMIT_BAL"].max())

selected_limit = st.sidebar.slider(
    "Credit limit",
    min_value=limit_min,
    max_value=limit_max,
    value=(limit_min, limit_max),
    step=10000
)

age_min = int(df["AGE"].min())
age_max = int(df["AGE"].max())

selected_age = st.sidebar.slider(
    "Customer age",
    min_value=age_min,
    max_value=age_max,
    value=(age_min, age_max)
)

gender_options = sorted(df["SEX"].dropna().unique().tolist())

selected_gender = st.sidebar.multiselect(
    "Gender",
    gender_options,
    default=gender_options
)

education_options = sorted(
    df["EDUCATION"].dropna().unique().tolist()
)

selected_education = st.sidebar.multiselect(
    "Education",
    education_options,
    default=education_options
)

marriage_options = sorted(
    df["MARRIAGE"].dropna().unique().tolist()
)

selected_marriage = st.sidebar.multiselect(
    "Marital status",
    marriage_options,
    default=marriage_options
)

# =========================================================
# APPLY FILTERS
# =========================================================

filtered = df[
    (df["LIMIT_BAL"] >= selected_limit[0]) &
    (df["LIMIT_BAL"] <= selected_limit[1]) &
    (df["AGE"] >= selected_age[0]) &
    (df["AGE"] <= selected_age[1]) &
    (df["SEX"].isin(selected_gender)) &
    (df["EDUCATION"].isin(selected_education)) &
    (df["MARRIAGE"].isin(selected_marriage))
].copy()

context = make_portfolio_context(filtered)

total = context["total"]
defaults = context["defaults"]
rate = context["rate"]

st.sidebar.divider()
st.sidebar.caption(
    f"Showing {total:,} of {len(df):,} customers"
)

# =========================================================
# HEADER
# =========================================================

st.markdown(
    "<h1 style='color:#FFFFFF;'>CREDINTEL</h1>",
    unsafe_allow_html=True
)

st.markdown(
    "<p style='color:#8FAED5;'>"
    "TURN FINANCIAL DATA INTO INTELLIGENCE"
    "</p>",
    unsafe_allow_html=True
)

st.divider()


# =========================================================
# EXECUTIVE OVERVIEW
# =========================================================

if page == "Executive Overview":

    st.subheader("Executive Overview")

    st.caption(
        "Portfolio performance and key credit risk indicators."
    )

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Total Customers",
        f"{total:,}"
    )

    col2.metric(
        "Recorded Defaults",
        f"{defaults:,}"
    )

    col3.metric(
        "Observed Default Rate",
        f"{rate:.2f}%"
    )

    col4.metric(
        "Average Credit Limit",
        format_money(context["average_limit"])
    )

    st.divider()

    if total == 0:
        st.warning("No records match the selected filters.")

    else:

        left, right = st.columns(2)

        with left:

            default_data = pd.DataFrame({
                "Status": [
                    "No recorded default",
                    "Recorded default"
                ],
                "Customers": [
                    context["non_defaults"],
                    context["defaults"]
                ]
            })

            fig = px.pie(
                default_data,
                names="Status",
                values="Customers",
                hole=0.58,
                title="Customer Default Distribution",
                color_discrete_sequence=[
                    "#2474D2",
                    "#E58A45"
                ]
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1730",
                plot_bgcolor="#0B1730",
                font_color="white"
            )

            st.plotly_chart(fig, use_container_width=True)

        with right:

            repayment = (
                filtered.groupby("PAY_0")[TARGET]
                .agg(["count", "sum"])
                .reset_index()
            )

            repayment["Default Rate"] = (
                repayment["sum"] /
                repayment["count"] * 100
            )

            fig = px.bar(
                repayment,
                x="PAY_0",
                y="Default Rate",
                title="Default Rate by Repayment Status",
                labels={
                    "PAY_0": "Repayment status",
                    "Default Rate": "Default rate (%)"
                },
                color_discrete_sequence=["#2474D2"]
            )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0B1730",
                plot_bgcolor="#0B1730",
                font_color="white"
            )

            st.plotly_chart(fig, use_container_width=True)

        st.divider()

        st.markdown("### Portfolio Interpretation")

        st.write(
            f"The selected portfolio contains {total:,} customers, "
            f"with {defaults:,} recorded defaults. "
            f"The observed default rate is {rate:.2f}%."
        )

        st.write(
            f"The average credit limit is "
            f"{context['average_limit']:,.0f}, and the average "
            f"customer age is {context['average_age']:.1f} years."
        )

        st.caption(
            "These are descriptive statistics from historical data, "
            "not forecasts or individual credit recommendations."
        )


# =========================================================
# CREDIT RISK ANALYTICS
# =========================================================
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
# =========================================================
# AI INTELLIGENCE
# =========================================================

elif page == "AI Intelligence":

    st.subheader("CredIntel AI Intelligence")

    st.caption(
        "Ask questions about the selected credit portfolio."
    )

    if total == 0:

        st.warning("No customer records match the current filters.")

    else:

        question = st.text_area(
            "Ask CredIntel",
            placeholder=(
                "Example: What are the main credit risk "
                "observations in this portfolio?"
            )
        )

        if st.button("Analyze Portfolio", use_container_width=True):

            if not question.strip():

                st.warning("Please enter a question.")

            else:

                prompt = f"""
You are CredIntel, a professional banking analytics assistant.

Analyze this historical credit portfolio.

Portfolio statistics:
- Customers: {total}
- Recorded defaults: {defaults}
- Observed default rate: {rate:.2f}%
- Average credit limit: {context['average_limit']:.2f}
- Median credit limit: {context['median_limit']:.2f}
- Average age: {context['average_age']:.1f}

User question:
{question}

Instructions:
- Use professional banking language.
- Use only the supplied statistics.
- Do not invent numbers.
- Do not claim causation from descriptive statistics.
- Do not make individual lending decisions.
- Mention limitations when relevant.
"""

                with st.spinner("CredIntel AI is analyzing..."):

                    try:

                        answer = ask_gemini(prompt)

                        st.markdown("### AI Analysis")
                        st.write(answer)

                    except Exception as e:

                        st.error(
                            "The AI request could not be completed."
                        )
                        st.exception(e)

        st.divider()

        st.markdown("### Portfolio Snapshot")

        st.metric(
            "Observed Default Rate",
            f"{rate:.2f}%"
        )

        st.metric(
            "Customers Analyzed",
            f"{total:,}"
        )


# =========================================================
# SQL EXPLORER
# =========================================================

elif page == "SQL Explorer":

    st.subheader("SQL Explorer")

    st.caption(
        "Explore the filtered customer dataset using read-only SQL."
    )

    example_query = """SELECT
    COUNT(*) AS total_customers,
    SUM("default payment next month") AS defaults,
    ROUND(
        100.0 * SUM("default payment next month") / COUNT(*),
        2
    ) AS default_rate_percent
FROM credit_clients;"""

    sql_query = st.text_area(
        "Enter SQL query",
        value=example_query,
        height=180
    )

    st.info(
        "Only a single SELECT or WITH query is allowed. "
        "Data modification commands are blocked."
    )

    if st.button("Run SQL Query", use_container_width=True):

        query = sql_query.strip()

        # Remove one optional trailing semicolon.
        query = query[:-1].strip() if query.endswith(";") else query

        valid_start = re.match(
            r"^(SELECT|WITH)\b",
            query,
            flags=re.IGNORECASE
        )

        if not valid_start:

            st.error("Only SELECT or WITH queries are allowed.")

        elif ";" in query:

            st.error("Multiple SQL statements are not allowed.")

        else:

            try:

                connection = sqlite3.connect(":memory:")

                filtered.to_sql(
                    "credit_clients",
                    connection,
                    index=False,
                    if_exists="replace"
                )

                connection.execute("PRAGMA query_only = ON")

                result = pd.read_sql_query(
                    query,
                    connection
                )

                connection.close()

                st.success("Query executed successfully.")

                st.dataframe(
                    result,
                    use_container_width=True,
                    hide_index=True
                )

            except Exception as e:

                st.error(f"SQL error: {e}")


# =========================================================
# RESEARCH & REPORTS
# =========================================================

elif page == "Research & Reports":

    st.subheader("Research & Reports")

    st.caption(
        "Export portfolio data and generate a professional "
        "CredIntel management report."
    )

    # -----------------------------------------------------
    # CSV EXPORT
    # -----------------------------------------------------

    st.markdown("### Customer Data Export")

    st.download_button(
        "Download Filtered Data (CSV)",
        data=filtered.to_csv(index=False).encode("utf-8"),
        file_name="credintel_filtered_customers.csv",
        mime="text/csv",
        use_container_width=True
    )

    st.divider()

    # -----------------------------------------------------
    # PDF REPORT GENERATOR
    # -----------------------------------------------------

    st.markdown("### Executive PDF Report")

    st.info(
        "The report uses the current sidebar filters and includes "
        "portfolio KPIs, charts, segment analysis, methodology, "
        "and AI-generated executive commentary."
    )

    if st.button(
        "Generate Executive PDF Report",
        use_container_width=True
    ):

        if total == 0:

            st.warning(
                "No customer records match the selected filters."
            )

        else:

            try:

                from reportlab.lib import colors
                from reportlab.lib.enums import TA_CENTER
                from reportlab.lib.pagesizes import A4
                from reportlab.lib.styles import (
                    getSampleStyleSheet,
                    ParagraphStyle
                )
                from reportlab.lib.units import mm
                from reportlab.platypus import (
                    SimpleDocTemplate,
                    Paragraph,
                    Spacer,
                    Table,
                    TableStyle,
                    Image,
                    PageBreak
                )
                from reportlab.lib.utils import ImageReader

                NAVY = colors.HexColor("#0B1730")
                BLUE = colors.HexColor("#2474D2")
                PALE = colors.HexColor("#EAF2FC")
                GREY = colors.HexColor("#667085")
                DARK = colors.HexColor("#182B49")
                WHITE = colors.white

                buffer = BytesIO()

                document = SimpleDocTemplate(
                    buffer,
                    pagesize=A4,
                    rightMargin=18 * mm,
                    leftMargin=18 * mm,
                    topMargin=23 * mm,
                    bottomMargin=22 * mm,
                    title="CredIntel Executive Credit Risk Report",
                    author="CredIntel Analytics"
                )

                styles = getSampleStyleSheet()

                styles.add(ParagraphStyle(
                    name="CredTitle",
                    parent=styles["Title"],
                    fontName="Helvetica-Bold",
                    fontSize=25,
                    leading=31,
                    textColor=NAVY,
                    alignment=TA_CENTER,
                    spaceAfter=12
                ))

                styles.add(ParagraphStyle(
                    name="CredSection",
                    parent=styles["Heading2"],
                    fontName="Helvetica-Bold",
                    fontSize=16,
                    leading=20,
                    textColor=NAVY,
                    spaceBefore=8,
                    spaceAfter=10
                ))

                styles.add(ParagraphStyle(
                    name="CredSubsection",
                    parent=styles["Heading3"],
                    fontName="Helvetica-Bold",
                    fontSize=11,
                    leading=15,
                    textColor=BLUE,
                    spaceBefore=8,
                    spaceAfter=6
                ))

                styles.add(ParagraphStyle(
                    name="CredBody",
                    parent=styles["BodyText"],
                    fontName="Helvetica",
                    fontSize=9,
                    leading=14,
                    textColor=DARK,
                    spaceAfter=8
                ))

                styles.add(ParagraphStyle(
                    name="CredSmall",
                    parent=styles["Normal"],
                    fontSize=8,
                    leading=11,
                    textColor=GREY
                ))

                # -------------------------------------------------
                # PAGE HEADER AND FOOTER
                # -------------------------------------------------

                def draw_page(canvas, doc):

                    canvas.saveState()

                    page_width, page_height = A4

                    canvas.setFillColor(NAVY)

                    canvas.rect(
                        0,
                        page_height - 13 * mm,
                        page_width,
                        13 * mm,
                        fill=1,
                        stroke=0
                    )

                    canvas.setFillColor(WHITE)
                    canvas.setFont("Helvetica-Bold", 9)

                    canvas.drawString(
                        18 * mm,
                        page_height - 8.5 * mm,
                        "CREDINTEL"
                    )

                    canvas.setFont("Helvetica", 8)

                    canvas.drawRightString(
                        page_width - 18 * mm,
                        page_height - 8.5 * mm,
                        "CREDIT RISK INTELLIGENCE"
                    )

                    canvas.setStrokeColor(
                        colors.HexColor("#D9E1EC")
                    )

                    canvas.line(
                        18 * mm,
                        15 * mm,
                        page_width - 18 * mm,
                        15 * mm
                    )

                    canvas.setFillColor(GREY)
                    canvas.setFont("Helvetica", 8)

                    canvas.drawString(
                        18 * mm,
                        9 * mm,
                        "Educational research report"
                    )

                    canvas.drawRightString(
                        page_width - 18 * mm,
                        9 * mm,
                        f"Page {doc.page}"
                    )

                    canvas.restoreState()

                story = []

                # -------------------------------------------------
                # PAGE 1: COVER AND EXECUTIVE SUMMARY
                # -------------------------------------------------

                story.append(Spacer(1, 20 * mm))

                story.append(Paragraph(
                    "CREDINTEL",
                    styles["CredTitle"]
                ))

                story.append(Paragraph(
                    "CREDIT RISK INTELLIGENCE REPORT",
                    ParagraphStyle(
                        "CoverSubtitle",
                        parent=styles["CredBody"],
                        alignment=TA_CENTER,
                        textColor=BLUE,
                        fontName="Helvetica-Bold",
                        fontSize=12
                    )
                ))

                story.append(Spacer(1, 10 * mm))

                cover_data = [
                    ["REPORT DATE", datetime.now().strftime("%d %B %Y")],
                    ["REPORT TYPE", "Executive Portfolio Analysis"],
                    ["DATASET", "Default of Credit Card Clients"],
                    ["CUSTOMERS ANALYZED", f"{total:,}"]
                ]

                cover_table = Table(
                    cover_data,
                    colWidths=[48 * mm, 102 * mm]
                )

                cover_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (0, -1), NAVY),
                    ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
                    ("BACKGROUND", (1, 0), (1, -1), PALE),
                    ("TEXTCOLOR", (1, 0), (1, -1), DARK),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("PADDING", (0, 0), (-1, -1), 10),
                    ("GRID", (0, 0), (-1, -1), 0.5, WHITE)
                ]))

                story.append(cover_table)
                story.append(Spacer(1, 12 * mm))

                story.append(Paragraph(
                    "Executive Summary",
                    styles["CredSection"]
                ))

                story.append(Paragraph(
                    f"The selected portfolio contains <b>{total:,}</b> "
                    f"customers, including <b>{defaults:,}</b> recorded "
                    f"defaults. The observed default rate is "
                    f"<b>{rate:.2f}%</b>. The average credit limit is "
                    f"<b>{context['average_limit']:,.0f}</b>, and the "
                    f"average customer age is "
                    f"<b>{context['average_age']:.1f} years</b>.",
                    styles["CredBody"]
                ))

                kpi_data = [
                    ["TOTAL CUSTOMERS", "RECORDED DEFAULTS", "DEFAULT RATE"],
                    [
                        f"{total:,}",
                        f"{defaults:,}",
                        f"{rate:.2f}%"
                    ]
                ]

                kpi_table = Table(
                    kpi_data,
                    colWidths=[50 * mm, 50 * mm, 50 * mm],
                    rowHeights=[10 * mm, 17 * mm]
                )

                kpi_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("BACKGROUND", (0, 1), (-1, 1), PALE),
                    ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("FONTSIZE", (0, 1), (-1, 1), 16),
                    ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("PADDING", (0, 0), (-1, -1), 7)
                ]))

                story.append(kpi_table)

                story.append(Spacer(1, 8 * mm))

                additional_data = [
                    ["Additional Indicator", "Value"],
                    [
                        "Average credit limit",
                        f"{context['average_limit']:,.2f}"
                    ],
                    [
                        "Median credit limit",
                        f"{context['median_limit']:,.2f}"
                    ],
                    [
                        "Average customer age",
                        f"{context['average_age']:.1f} years"
                    ],
                    [
                        "Customers without recorded default",
                        f"{context['non_defaults']:,}"
                    ]
                ]

                additional_table = Table(
                    additional_data,
                    colWidths=[90 * mm, 60 * mm]
                )

                additional_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), PALE),
                    ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("GRID", (0, 0), (-1, -1), 0.4, GREY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                    ("PADDING", (0, 0), (-1, -1), 8)
                ]))

                story.append(additional_table)

                # -------------------------------------------------
                # PAGE 2: DEFAULT AND REPAYMENT ANALYSIS
                # -------------------------------------------------

                story.append(PageBreak())

                story.append(Paragraph(
                    "01 | Portfolio Risk Analysis",
                    styles["CredSection"]
                ))

                default_data = pd.DataFrame({
                    "Status": [
                        "No recorded default",
                        "Recorded default"
                    ],
                    "Customers": [
                        context["non_defaults"],
                        context["defaults"]
                    ]
                })

                fig1 = px.pie(
                    default_data,
                    names="Status",
                    values="Customers",
                    hole=0.58,
                    title="Customer Default Distribution",
                    color_discrete_sequence=[
                        "#2474D2",
                        "#E58A45"
                    ]
                )

                fig1.update_layout(
                    template="plotly_white",
                    title_x=0.05,
                    height=400
                )

                chart1 = BytesIO(
                    fig1.to_image(
                        format="png",
                        width=1100,
                        height=650,
                        scale=2
                    )
                )

                story.append(Image(
                    chart1,
                    width=155 * mm,
                    height=91 * mm
                ))

                story.append(Paragraph(
                    f"The selected portfolio contains {defaults:,} "
                    f"recorded defaults out of {total:,} customers. "
                    f"This corresponds to an observed default rate "
                    f"of {rate:.2f}%.",
                    styles["CredBody"]
                ))

                repayment = (
                    filtered.groupby("PAY_0")[TARGET]
                    .agg(["count", "sum"])
                    .reset_index()
                )

                repayment["Default Rate"] = (
                    repayment["sum"] /
                    repayment["count"].replace(0, 1) * 100
                )

                fig2 = px.bar(
                    repayment,
                    x="PAY_0",
                    y="Default Rate",
                    title="Observed Default Rate by Repayment Status",
                    labels={
                        "PAY_0": "Repayment status",
                        "Default Rate": "Default rate (%)"
                    },
                    color_discrete_sequence=["#2474D2"]
                )

                fig2.update_layout(
                    template="plotly_white",
                    title_x=0.05,
                    height=350
                )

                chart2 = BytesIO(
                    fig2.to_image(
                        format="png",
                        width=1100,
                        height=600,
                        scale=2
                    )
                )

                story.append(Image(
                    chart2,
                    width=155 * mm,
                    height=84 * mm
                ))

                story.append(Paragraph(
                    "Repayment status is a historical payment indicator. "
                    "Differences in observed rates are descriptive and "
                    "do not establish causation.",
                    styles["CredBody"]
                ))

                # -------------------------------------------------
                # PAGE 3: CREDIT LIMIT SEGMENTS
                # -------------------------------------------------

                story.append(PageBreak())

                story.append(Paragraph(
                    "02 | Customer Segment Analysis",
                    styles["CredSection"]
                ))

                bins = [
                    0,
                    50000,
                    100000,
                    200000,
                    500000,
                    float("inf")
                ]

                labels = [
                    "Under 50K",
                    "50K-99K",
                    "100K-199K",
                    "200K-499K",
                    "500K and above"
                ]

                segment_df = filtered.copy()

                segment_df["Credit Segment"] = pd.cut(
                    segment_df["LIMIT_BAL"],
                    bins=bins,
                    labels=labels,
                    right=False
                )

                segment_summary = (
                    segment_df.groupby(
                        "Credit Segment",
                        observed=False
                    )
                    .agg(
                        Customers=(TARGET, "count"),
                        Defaults=(TARGET, "sum")
                    )
                    .reset_index()
                )

                segment_summary["Default Rate"] = (
                    segment_summary["Defaults"] /
                    segment_summary["Customers"].replace(0, 1) * 100
                )

                fig3 = px.bar(
                    segment_summary,
                    x="Credit Segment",
                    y="Customers",
                    title="Customers by Credit Limit Segment",
                    color_discrete_sequence=["#2474D2"],
                    text="Customers"
                )

                fig3.update_layout(
                    template="plotly_white",
                    title_x=0.05,
                    height=400
                )

                chart3 = BytesIO(
                    fig3.to_image(
                        format="png",
                        width=1100,
                        height=650,
                        scale=2
                    )
                )

                story.append(Image(
                    chart3,
                    width=155 * mm,
                    height=91 * mm
                ))

                story.append(Paragraph(
                    "Credit limit segments provide a descriptive view "
                    "of portfolio composition and observed outcomes.",
                    styles["CredBody"]
                ))

                segment_table_data = [
                    ["Credit Segment", "Customers", "Defaults", "Default Rate"]
                ]

                for _, row in segment_summary.iterrows():

                    segment_table_data.append([
                        str(row["Credit Segment"]),
                        f"{int(row['Customers']):,}",
                        f"{int(row['Defaults']):,}",
                        (
                            f"{row['Default Rate']:.2f}%"
                            if row["Customers"] > 0 else "N/A"
                        )
                    ])

                segment_table = Table(
                    segment_table_data,
                    colWidths=[52 * mm, 30 * mm, 30 * mm, 38 * mm]
                )

                segment_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, GREY),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                    ("PADDING", (0, 0), (-1, -1), 7)
                ]))

                story.append(segment_table)

                # -------------------------------------------------
                # PAGE 4: AI EXECUTIVE COMMENTARY
                # -------------------------------------------------

                story.append(PageBreak())

                story.append(Paragraph(
                    "03 | AI Executive Commentary",
                    styles["CredSection"]
                ))

                ai_prompt = f"""
You are a senior banking credit risk analyst.

Write an executive commentary for this historical credit portfolio.

Use only these supplied figures:

Total customers: {total}
Recorded defaults: {defaults}
Observed default rate: {rate:.2f}%
Average credit limit: {context['average_limit']:.2f}
Median credit limit: {context['median_limit']:.2f}
Average age: {context['average_age']:.1f}

Write these sections:

1. Executive assessment
2. Key portfolio observations
3. Credit risk considerations
4. Management recommendations
5. Limitations and responsible use

Rules:
- Professional banking language.
- Do not invent statistics.
- Do not claim causation.
- Do not make individual lending decisions.
- Clearly identify this as historical Taiwan data.
- Keep the answer below 400 words.
"""

                try:

                    commentary = ask_gemini(ai_prompt)

                    for paragraph in commentary.split("\n"):

                        paragraph = paragraph.strip()

                        if not paragraph:
                            continue

                        safe_text = escape(paragraph)

                        story.append(Paragraph(
                            safe_text,
                            styles["CredBody"]
                        ))

                except Exception as ai_error:

                    story.append(Paragraph(
                        "AI commentary was unavailable for this report. "
                        "The statistical analysis and charts are still "
                        "included.",
                        styles["CredBody"]
                    ))

                    st.warning(
                        f"AI commentary unavailable: {ai_error}"
                    )

                # -------------------------------------------------
                # PAGE 5: METHODOLOGY AND LIMITATIONS
                # -------------------------------------------------

                story.append(PageBreak())

                story.append(Paragraph(
                    "04 | Methodology & Responsible Use",
                    styles["CredSection"]
                ))

                story.append(Paragraph(
                    "Dataset Overview",
                    styles["CredSubsection"]
                ))

                story.append(Paragraph(
                    "This project uses the Default of Credit Card Clients "
                    "dataset from the UCI Machine Learning Repository. "
                    "The original dataset contains 30,000 historical "
                    "customer records from Taiwan. The target variable "
                    "represents default payment in the following month.",
                    styles["CredBody"]
                ))

                story.append(Paragraph(
                    "Analytical Methodology",
                    styles["CredSubsection"]
                ))

                methods = [
                    "Data inspection and validation.",
                    "SQL aggregation for portfolio metrics.",
                    "Calculation of observed default rates.",
                    "Segmentation by credit limit and repayment status.",
                    "Interactive visual analysis and executive reporting."
                ]

                for method in methods:

                    story.append(Paragraph(
                        "• " + escape(method),
                        styles["CredBody"]
                    ))

                story.append(Paragraph(
                    "Responsible Use and Limitations",
                    styles["CredSubsection"]
                ))

                story.append(Paragraph(
                    "This is a historical dataset relating to credit "
                    "card clients in Taiwan. It may not represent "
                    "current customers, other countries, or present-day "
                    "lending environments. The results are descriptive "
                    "and do not establish causal relationships. "
                    "Historical data may contain bias and limitations. "
                    "This project is intended for educational and "
                    "analytical research only. It must not be used as "
                    "the sole basis for real-world individual lending, "
                    "credit approval, pricing, or adverse decisions. "
                    "Real-world use requires appropriate validation, "
                    "fairness testing, privacy safeguards, governance, "
                    "and human oversight.",
                    styles["CredBody"]
                ))

                story.append(Paragraph(
                    "Data Source and Attribution",
                    styles["CredSubsection"]
                ))

                story.append(Paragraph(
                    "UCI Machine Learning Repository: Default of "
                    "Credit Card Clients. Dataset ID: 350.",
                    styles["CredBody"]
                ))

                story.append(Paragraph(
                    "https://archive.ics.uci.edu/dataset/350/default",
                    styles["CredSmall"]
                ))

                story.append(Spacer(1, 12 * mm))

                story.append(Paragraph(
                    "CREDINTEL | TURN FINANCIAL DATA INTO INTELLIGENCE",
                    ParagraphStyle(
                        "ClosingCredIntel",
                        parent=styles["CredBody"],
                        alignment=TA_CENTER,
                        textColor=BLUE,
                        fontName="Helvetica-Bold"
                    )
                ))

                # -------------------------------------------------
                # BUILD PDF
                # -------------------------------------------------

                document.build(
                    story,
                    onFirstPage=draw_page,
                    onLaterPages=draw_page
                )

                buffer.seek(0)

                st.success(
                    "Your CredIntel executive report is ready."
                )

                st.download_button(
                    "Download CredIntel Executive PDF",
                    data=buffer.getvalue(),
                    file_name="CredIntel_Executive_Report.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )

            except Exception as e:

                st.error("The PDF report could not be generated.")
                st.exception(e)

    st.divider()

    st.markdown("### Dataset Information")

    st.write("**Source:** UCI Machine Learning Repository")
    st.write("**Dataset:** Default of Credit Card Clients")
    st.write("**Original records:** 30,000 historical customers")
    st.write("**Target:** Default payment next month")


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    "CREDINTEL | Credit Risk Analytics & AI | "
    "Educational Research Project"
)

st.caption(
    "Historical data analysis only. Not intended for individual "
    "credit approval or lending decisions."
)
