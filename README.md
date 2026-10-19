CredIntel — Credit Risk Analytics with SQL & AI

Turn Financial Data Into Intelligence.

CredIntel is a portfolio project exploring historical credit-card default patterns using SQL, Python, interactive visualizations, and generative AI.

Business Problem

How are historical repayment behavior and credit-limit segments associated with credit-card default outcomes?

CredIntel calculates default rates, compares repayment-status groups, explores credit-limit segments, and uses a Gemini-powered assistant to explain selected results derived from SQL queries.

Project Objectives

* Analyze authentic historical financial data.
* Use SQL to calculate and compare default rates.
* Explore repayment behavior and credit-limit segments.
* Create interactive Plotly visualizations.
* Integrate generative AI to explain selected database results.
* Practice responsible interpretation of financial data.

Technology Stack

* Python
* pandas
* SQLite and SQL
* Plotly
* Google Colab
* Google Gemini API

Dataset

Default of Credit Card Clients, from the UCI Machine Learning Repository.

The dataset contains 30,000 historical customer records, including credit limits, repayment status, bill amounts, payment amounts, and a following-month default outcome.

Source: https://archive.ics.uci.edu/dataset/350/default

The data relates to credit-card clients in Taiwan and reflects a historical period. It should not be assumed to represent today’s customers or other countries.

Analysis

The notebook explores:

1. Overall observed default rate.
2. Default rates grouped by repayment status.
3. Default rates grouped by credit-limit segment.
4. Interactive charts for comparing observed rates.

All reported statistics are calculated from the dataset rather than manually invented.

AI Component

CredIntel uses Gemini to explain selected SQL-derived results in natural language.

The current prototype provides database results and instructions to avoid unsupported claims. Its question-handling logic covers only the analyses explicitly implemented in the notebook.

AI output can still be inaccurate and should be checked against the underlying SQL results.

How to Run

1. Open the notebook in Google Colab.
2. Run its cells in order to download the dataset, prepare the SQLite database, and perform the analysis.
3. To use the AI features, configure a Gemini API key in Colab Secrets under the name GEMINI_API_KEY.
4. Run the AI cells when API access is available.

Never publish API keys, credentials, or private secrets in the repository.

Responsible Use and Limitations

* This is an educational analytics project, not a lending decision system.
* Observed associations do not establish causation.
* Group sizes affect how confidently default rates can be compared.
* The dataset reflects a particular historical and geographic context.
* AI explanations should be validated against the SQL results.
* API availability and usage limits depend on Google’s current service terms.

Data Attribution

Yeh, I. C., and Lien, C. H. (2009). The comparisons of data mining techniques for the predictive accuracy of probability of default of credit card clients. Expert Systems with Applications, 36(2), 2473–2480.

Dataset: UCI Machine Learning Repository, Default of Credit Card Clients. https://archive.ics.uci.edu/dataset/350/default

Review the dataset’s license and attribution requirements on the official source before redistributing any data.

Project Status

An evolving portfolio project demonstrating practical SQL analytics, data visualization, and a grounded generative-AI workflow for financial data exploration.
