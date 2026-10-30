
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
    st.caption(
        "Generate a professional, multi-page CredIntel management report "
        "using the currently selected customer data."
    )

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

    st.info(
        "The report will reflect the filters currently selected in the sidebar."
    )

    if st.button("Generate Executive PDF Report", use_container_width=True):

        try:
            from io import BytesIO
            from datetime import datetime

            import pandas as pd
            import plotly.express as px

            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
            from reportlab.lib.pagesizes import A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import mm
            from reportlab.platypus import (
                SimpleDocTemplate,
                Paragraph,
                Spacer,
                Table,
                TableStyle,
                Image,
                PageBreak,
                KeepTogether
            )

            # -------------------------------------------------
            # BRAND COLORS
            # -------------------------------------------------

            NAVY = colors.HexColor("#0B1730")
            BLUE = colors.HexColor("#2474D2")
            LIGHT_BLUE = colors.HexColor("#EAF2FC")
            PALE = colors.HexColor("#F4F7FB")
            GREY = colors.HexColor("#667085")
            DARK = colors.HexColor("#182B49")
            WHITE = colors.white

            # -------------------------------------------------
            # DATA SUMMARY
            # -------------------------------------------------

            report_df = filtered.copy()

            total = len(report_df)

            defaults = (
                int(report_df[TARGET].sum())
                if total > 0 else 0
            )

            non_defaults = total - defaults

            rate = (
                calculate_default_rate(report_df)
                if total > 0 else 0
            )

            avg_limit = (
                report_df["LIMIT_BAL"].mean()
                if total > 0 else 0
            )

            avg_age = (
                report_df["AGE"].mean()
                if total > 0 else 0
            )

            median_limit = (
                report_df["LIMIT_BAL"].median()
                if total > 0 else 0
            )

            report_date = datetime.now().strftime("%d %B %Y")

            # -------------------------------------------------
            # REPORT STYLES
            # -------------------------------------------------

            styles = getSampleStyleSheet()

            styles.add(ParagraphStyle(
                name="CoverTitle",
                parent=styles["Title"],
                fontName="Helvetica-Bold",
                fontSize=27,
                leading=34,
                textColor=NAVY,
                alignment=TA_LEFT,
                spaceAfter=12
            ))

            styles.add(ParagraphStyle(
                name="SubtitleCustom",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=12,
                leading=18,
                textColor=GREY,
                spaceAfter=10
            ))

            styles.add(ParagraphStyle(
                name="SectionCustom",
                parent=styles["Heading2"],
                fontName="Helvetica-Bold",
                fontSize=16,
                leading=21,
                textColor=NAVY,
                spaceBefore=10,
                spaceAfter=10
            ))

            styles.add(ParagraphStyle(
                name="SubsectionCustom",
                parent=styles["Heading3"],
                fontName="Helvetica-Bold",
                fontSize=11,
                leading=15,
                textColor=BLUE,
                spaceBefore=8,
                spaceAfter=6
            ))

            styles.add(ParagraphStyle(
                name="BodyCustom",
                parent=styles["BodyText"],
                fontName="Helvetica",
                fontSize=9,
                leading=14,
                textColor=DARK,
                spaceAfter=8
            ))

            styles.add(ParagraphStyle(
                name="SmallCustom",
                parent=styles["Normal"],
                fontName="Helvetica",
                fontSize=8,
                leading=11,
                textColor=GREY
            ))

            # -------------------------------------------------
            # PDF HEADER AND FOOTER
            # -------------------------------------------------

            def draw_page(canvas, document):

                canvas.saveState()

                page_width, page_height = A4

                # Top navy brand strip
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

                # Footer line
                canvas.setStrokeColor(colors.HexColor("#D9E1EC"))
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
                    "Confidentiality: Educational research report"
                )

                canvas.drawRightString(
                    page_width - 18 * mm,
                    9 * mm,
                    f"Page {document.page}"
                )

                canvas.restoreState()

            # -------------------------------------------------
            # DOCUMENT SETUP
            # -------------------------------------------------

            buffer = BytesIO()

            document = SimpleDocTemplate(
                buffer,
                pagesize=A4,
                rightMargin=18 * mm,
                leftMargin=18 * mm,
                topMargin=22 * mm,
                bottomMargin=23 * mm,
                title="CredIntel Credit Risk Intelligence Report",
                author="CredIntel Analytics"
            )

            story = []

            # -------------------------------------------------
            # PAGE 1: COVER AND EXECUTIVE SUMMARY
            # -------------------------------------------------

            story.append(Spacer(1, 24 * mm))

            story.append(Paragraph(
                "CREDINTEL",
                ParagraphStyle(
                    "BrandLarge",
                    parent=styles["Normal"],
                    fontName="Helvetica-Bold",
                    fontSize=13,
                    textColor=BLUE,
                    spaceAfter=14
                )
            ))

            story.append(Paragraph(
                "Credit Risk<br/>Intelligence Report",
                styles["CoverTitle"]
            ))

            story.append(Paragraph(
                "Turning Financial Data Into Intelligence",
                styles["SubtitleCustom"]
            ))

            story.append(Spacer(1, 8 * mm))

            cover_info = [
                ["REPORT TYPE", "Executive Portfolio Analysis"],
                ["REPORT DATE", report_date],
                ["DATASET", "Default of Credit Card Clients"],
                ["RECORDS ANALYZED", f"{total:,}"]
            ]

            cover_table = Table(
                cover_info,
                colWidths=[45 * mm, 105 * mm]
            )

            cover_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("TEXTCOLOR", (0, 0), (0, -1), WHITE),
                ("TEXTCOLOR", (1, 0), (1, -1), DARK),
                ("BACKGROUND", (1, 0), (1, -1), PALE),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.5, WHITE),
                ("PADDING", (0, 0), (-1, -1), 11),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE")
            ]))

            story.append(cover_table)
            story.append(Spacer(1, 13 * mm))

            story.append(Paragraph(
                "Executive Summary",
                styles["SectionCustom"]
            ))

            if total > 0:
                summary_text = (
                    f"The selected portfolio contains <b>{total:,}</b> customers. "
                    f"Within this dataset, <b>{defaults:,}</b> customers are recorded "
                    f"as having defaulted, representing an observed default rate of "
                    f"<b>{rate:.2f}%</b>. The average credit limit is "
                    f"<b>{avg_limit:,.0f}</b>, while the average customer age is "
                    f"<b>{avg_age:.1f} years</b>."
                )
            else:
                summary_text = (
                    "No customer records match the current filters. "
                    "Adjust the sidebar filters to generate a populated report."
                )

            story.append(Paragraph(
                summary_text,
                styles["BodyCustom"]
            ))

            story.append(Paragraph(
                "Portfolio KPI Dashboard",
                styles["SubsectionCustom"]
            ))

            kpi_data = [
                ["TOTAL CUSTOMERS", "DEFAULTED", "OBSERVED DEFAULT RATE"],
                [
                    f"{total:,}",
                    f"{defaults:,}",
                    f"{rate:.2f}%"
                ]
            ]

            kpi_table = Table(
                kpi_data,
                colWidths=[50 * mm, 50 * mm, 50 * mm],
                rowHeights=[10 * mm, 18 * mm]
            )

            kpi_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("BACKGROUND", (0, 1), (-1, 1), LIGHT_BLUE),
                ("TEXTCOLOR", (0, 1), (-1, 1), NAVY),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 7),
                ("FONTSIZE", (0, 1), (-1, 1), 17),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOX", (0, 0), (-1, -1), 0.7, WHITE),
                ("PADDING", (0, 0), (-1, -1), 7)
            ]))

            story.append(kpi_table)

            story.append(Spacer(1, 8 * mm))

            story.append(Paragraph(
                "Additional portfolio indicators",
                styles["SubsectionCustom"]
            ))

            additional_data = [
                ["Indicator", "Portfolio value"],
                ["Average credit limit", f"{avg_limit:,.2f}"],
                ["Median credit limit", f"{median_limit:,.2f}"],
                [
                    "Average customer age",
                    f"{avg_age:.1f} years" if total else "N/A"
                ],
                ["Customers without recorded default", f"{non_defaults:,}"]
            ]

            additional_table = Table(
                additional_data,
                colWidths=[90 * mm, 60 * mm]
            )

            additional_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), LIGHT_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), NAVY),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E1EC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("PADDING", (0, 0), (-1, -1), 8)
            ]))

            story.append(additional_table)

            # -------------------------------------------------
            # PAGE 2: PORTFOLIO RISK ANALYSIS
            # -------------------------------------------------

            story.append(PageBreak())

            story.append(Paragraph(
                "01 | Portfolio Risk Analysis",
                styles["SectionCustom"]
            ))

            story.append(Paragraph(
                "Default distribution",
                styles["SubsectionCustom"]
            ))

            if total > 0:

                default_chart = pd.DataFrame({
                    "Status": ["No recorded default", "Recorded default"],
                    "Customers": [non_defaults, defaults]
                })

                fig1 = px.pie(
                    default_chart,
                    names="Status",
                    values="Customers",
                    hole=0.62,
                    title="Customer Default Distribution",
                    color_discrete_sequence=["#2474D2", "#E58A45"]
                )

                fig1.update_layout(
                    template="plotly_white",
                    font=dict(family="Arial", size=12),
                    title_x=0.05,
                    margin=dict(l=20, r=20, t=55, b=20),
                    height=350
                )

                chart_image = BytesIO(
                    fig1.to_image(
                        format="png",
                        width=1100,
                        height=650,
                        scale=2
                    )
                )

                story.append(Image(
                    chart_image,
                    width=155 * mm,
                    height=88 * mm
                ))

                story.append(Spacer(1, 5 * mm))

                story.append(Paragraph(
                    f"Of the {total:,} selected customers, "
                    f"{defaults:,} are recorded as having defaulted. "
                    f"This represents {rate:.2f}% of the selected portfolio. "
                    "The figures describe this historical dataset and should "
                    "not be interpreted as a forecast of future defaults.",
                    styles["BodyCustom"]
                ))

            else:
                story.append(Paragraph(
                    "No data is available for the selected filters.",
                    styles["BodyCustom"]
                ))

            # -------------------------------------------------
            # REPAYMENT STATUS ANALYSIS
            # -------------------------------------------------

            story.append(Paragraph(
                "Repayment Status Analysis",
                styles["SubsectionCustom"]
            ))

            repayment_column = (
                "PAY_0" if "PAY_0" in report_df.columns else None
            )

            if total > 0 and repayment_column:

                repayment = (
                    report_df
                    .groupby(repayment_column)
                    .agg(
                        Customers=(TARGET, "count"),
                        Defaults=(TARGET, "sum")
                    )
                    .reset_index()
                    .sort_values(repayment_column)
                )

                repayment["Default rate"] = (
                    100 * repayment["Defaults"] /
                    repayment["Customers"].replace(0, 1)
                )

                fig2 = px.bar(
                    repayment,
                    x=repayment_column,
                    y="Default rate",
                    title="Observed Default Rate by Repayment Status",
                    labels={
                        repayment_column: "Repayment status",
                        "Default rate": "Default rate (%)"
                    },
                    text_auto=".1f",
                    color_discrete_sequence=["#2474D2"]
                )

                fig2.update_layout(
                    template="plotly_white",
                    title_x=0.05,
                    margin=dict(l=20, r=20, t=55, b=30),
                    height=330
                )

                repayment_image = BytesIO(
                    fig2.to_image(
                        format="png",
                        width=1100,
                        height=600,
                        scale=2
                    )
                )

                story.append(Image(
                    repayment_image,
                    width=155 * mm,
                    height=84 * mm
                ))

                story.append(Paragraph(
                    "Repayment status categories are historical payment "
                    "indicators. Differences in observed default rates show "
                    "associations in this dataset, not proof of causation.",
                    styles["BodyCustom"]
                ))

            # -------------------------------------------------
            # PAGE 3: CREDIT LIMIT ANALYSIS
            # -------------------------------------------------

            story.append(PageBreak())

            story.append(Paragraph(
                "02 | Customer Segment Analysis",
                styles["SectionCustom"]
            ))

            story.append(Paragraph(
                "Credit Limit Distribution",
                styles["SubsectionCustom"]
            ))

            if total > 0:

                bins = [0, 50000, 100000, 200000, 500000, float("inf")]

                labels = [
                    "Under 50K",
                    "50K-99K",
                    "100K-199K",
                    "200K-499K",
                    "500K and above"
                ]

                segment_df = report_df.copy()

                segment_df["Credit Segment"] = pd.cut(
                    segment_df["LIMIT_BAL"],
                    bins=bins,
                    labels=labels,
                    right=False
                )

                segment_summary = (
                    segment_df
                    .groupby("Credit Segment", observed=False)
                    .agg(
                        Customers=(TARGET, "count"),
                        Defaults=(TARGET, "sum")
                    )
                    .reset_index()
                )

                segment_summary["Default rate"] = (
                    100 * segment_summary["Defaults"] /
                    segment_summary["Customers"].replace(0, 1)
                )

                fig3 = px.bar(
                    segment_summary,
                    x="Credit Segment",
                    y="Customers",
                    title="Customers by Credit Limit Segment",
                    text="Customers",
                    color_discrete_sequence=["#2474D2"]
                )

                fig3.update_layout(
                    template="plotly_white",
                    title_x=0.05,
                    margin=dict(l=20, r=20, t=55, b=30),
                    height=350
                )

                segment_image = BytesIO(
                    fig3.to_image(
                        format="png",
                        width=1100,
                        height=650,
                        scale=2
                    )
                )

                story.append(Image(
                    segment_image,
                    width=155 * mm,
                    height=92 * mm
                ))

                story.append(Paragraph(
                    "Credit limit segments provide a descriptive view of "
                    "portfolio composition. Customer counts and observed "
                    "default rates should be considered together when "
                    "reviewing segment-level patterns.",
                    styles["BodyCustom"]
                ))

                story.append(Paragraph(
                    "Credit Segment Summary",
                    styles["SubsectionCustom"]
                ))

                segment_table_data = [
                    ["Credit segment", "Customers", "Defaults", "Default rate"]
                ]

                for _, row in segment_summary.iterrows():

                    segment_table_data.append([
                        str(row["Credit Segment"]),
                        f"{int(row['Customers']):,}",
                        f"{int(row['Defaults']):,}",
                        (
                            f"{row['Default rate']:.2f}%"
                            if row["Customers"] > 0 else "N/A"
                        )
                    ])

                segment_table = Table(
                    segment_table_data,
                    colWidths=[55 * mm, 30 * mm, 30 * mm, 35 * mm]
                )

                segment_table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                    ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E1EC")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                    ("PADDING", (0, 0), (-1, -1), 7),
                    ("ALIGN", (1, 1), (-1, -1), "RIGHT")
                ]))

                story.append(segment_table)

            else:
                story.append(Paragraph(
                    "No customer data is available for segment analysis.",
                    styles["BodyCustom"]
                ))

            # -------------------------------------------------
            # PAGE 4: METHODOLOGY AND RESPONSIBLE USE
            # -------------------------------------------------

            story.append(PageBreak())

            story.append(Paragraph(
                "03 | Methodology & Responsible Use",
                styles["SectionCustom"]
            ))

            story.append(Paragraph(
                "Dataset Overview",
                styles["SubsectionCustom"]
            ))

            story.append(Paragraph(
                "This project uses the Default of Credit Card Clients "
                "dataset from the UCI Machine Learning Repository. "
                "The original dataset contains 30,000 historical customer "
                "records from Taiwan. The target variable represents "
                "default payment in the following month.",
                styles["BodyCustom"]
            ))

            story.append(Paragraph(
                "Analytical Methodology",
                styles["SubsectionCustom"]
            ))

            methodology_items = [
                "Data inspection and validation of customer records.",
                "SQL aggregation for portfolio-level performance metrics.",
                "Calculation of observed default rates.",
                "Segmentation by credit limit and repayment status.",
                "Interactive visual analysis and executive reporting."
            ]

            for item in methodology_items:
                story.append(Paragraph(
                    "• " + item,
                    styles["BodyCustom"]
                ))

            story.append(Paragraph(
                "Key Definitions",
                styles["SubsectionCustom"]
            ))

            definitions = [
                ["Metric", "Definition"],
                [
                    "Observed default rate",
                    "Recorded defaults divided by selected customer count."
                ],
                [
                    "Average credit limit",
                    "Mean credit limit among selected customer records."
                ],
                [
                    "Repayment status",
                    "Historical repayment status recorded in the dataset."
                ]
            ]

            definition_table = Table(
                definitions,
                colWidths=[48 * mm, 102 * mm]
            )

            definition_table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D9E1EC")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, PALE]),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP")
            ]))

            story.append(definition_table)

            story.append(Spacer(1, 8 * mm))

            story.append(Paragraph(
                "Responsible Use and Limitations",
                styles["SubsectionCustom"]
            ))

            limitations = (
                "This dataset is historical and relates to credit card "
                "clients in Taiwan. It may not represent current customers, "
                "other countries, or present-day lending environments. "
                "The results are descriptive and do not establish causal "
                "relationships. The dataset may contain historical biases "
                "and limitations. This project is intended for educational "
                "and analytical research purposes only. It must not be used "
                "as the sole basis for real-world individual lending, "
                "credit approval, pricing, or adverse decisions. Any "
                "real-world application requires appropriate validation, "
                "fairness testing, privacy safeguards, governance, and "
                "human oversight."
            )

            story.append(Paragraph(
                limitations,
                styles["BodyCustom"]
            ))

            story.append(Paragraph(
                "Data Source and Attribution",
                styles["SubsectionCustom"]
            ))

            story.append(Paragraph(
                "UCI Machine Learning Repository: Default of Credit Card "
                "Clients. Dataset ID: 350. "
                "https://archive.ics.uci.edu/dataset/350/default",
                styles["SmallCustom"]
            ))

            story.append(Spacer(1, 12 * mm))

            story.append(Paragraph(
                "CREDINTEL | TURN FINANCIAL DATA INTO INTELLIGENCE",
                ParagraphStyle(
                    "ClosingBrand",
                    parent=styles["Normal"],
                    fontName="Helvetica-Bold",
                    fontSize=10,
                    textColor=BLUE,
                    alignment=TA_CENTER,
                    spaceBefore=10
                )
            ))

            # -------------------------------------------------
            # BUILD PDF
            # -------------------------------------------------

          
            # -------------------------------------------------
            # AI-POWERED EXECUTIVE COMMENTARY
            # -------------------------------------------------

            story.append(PageBreak())

            story.append(Paragraph(
                "04 | AI Executive Commentary",
                styles["SectionCustom"]
            ))

            story.append(Paragraph(
                "AI-generated portfolio interpretation",
                styles["SubsectionCustom"]
            ))

            try:
                import os
                from google import genai

                api_key = st.secrets.get("GEMINI_API_KEY", None)

                if api_key and total > 0:

                    client = genai.Client(api_key=api_key)

                    ai_prompt = f"""
You are a senior banking credit risk analyst.

Prepare a professional executive commentary for a credit risk report.

Use only the following portfolio statistics:

Total customers: {total}
Recorded defaults: {defaults}
Observed default rate: {rate:.2f}%
Average credit limit: {avg_limit:.2f}
Median credit limit: {median_limit:.2f}
Average customer age: {avg_age:.1f}

Write five concise sections:

1. Executive assessment
2. Key portfolio observations
3. Credit risk considerations
4. Management recommendations
5. Limitations and responsible use

Rules:
- Use professional banking language.
- Do not invent statistics.
- Do not claim correlation proves causation.
- Do not make individual lending decisions.
- Clearly state that the dataset is historical.
- Recommendations must be suitable for analytical review.
- Keep the complete response under 450 words.
"""

                    response = client.models.generate_content(
                        model="gemini-3.5-flash",
                        contents=ai_prompt
                    )

                    commentary = response.text or (
                        "AI commentary could not be generated."
                    )

                    # Convert plain text into PDF paragraphs
                    for paragraph in commentary.split("\n"):

                        paragraph = paragraph.strip()

                        if not paragraph:
                            continue

                        safe_paragraph = (
                            paragraph
                            .replace("&", "&amp;")
                            .replace("<", "&lt;")
                            .replace(">", "&gt;")
                        )

                        if paragraph[:2].isdigit() and "." in paragraph[:4]:
                            story.append(Paragraph(
                                safe_paragraph,
                                styles["SubsectionCustom"]
                            ))
                        else:
                            story.append(Paragraph(
                                safe_paragraph,
                                styles["BodyCustom"]
                            ))

                else:

                    story.append(Paragraph(
                        "AI commentary is unavailable. "
                        "Check that GEMINI_API_KEY is configured "
                        "in Streamlit Secrets and that the selected "
                        "portfolio contains customer records.",
                        styles["BodyCustom"]
                    ))

            except Exception as ai_error:

                story.append(Paragraph(
                    "AI commentary could not be generated during this run. "
                    "The remaining report is still available.",
                    styles["BodyCustom"]
                ))

                story.append(Paragraph(
                    str(ai_error).replace("&", "&amp;").replace("<", "&lt;"),
                    styles["SmallCustom"]
                ))


    st.divider()

    st.markdown("#### Dataset information")
    st.write("**Source:** UCI Machine Learning Repository")
    st.write("**Dataset:** Default of Credit Card Clients")
    st.write("**Original records:** 30,000 historical customers")
    st.write("**Target:** Default payment next month")

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
