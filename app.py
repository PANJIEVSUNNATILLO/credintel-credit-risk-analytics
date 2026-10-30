
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

    if st.button("Ask CredIntel AI") and question.strip():

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

            Answer the user's question using only the supplied
            historical dataset analysis.

            Explain findings clearly and avoid claiming causation.
            Do not make individual lending recommendations.
            If the data does not answer the question, say so.

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

        except Exception as e:
            st.error("The AI assistant could not generate an answer.")
            st.caption(str(e))
