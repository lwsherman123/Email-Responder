import streamlit as st

st.title("📩 Email Responses")

if "responses" in st.session_state and st.session_state["responses"]:
    st.subheader("Generated Email Responses:")
    for idx, response in enumerate(st.session_state["responses"], 1):
        st.write(f"**Response {idx}:**")
        st.write(response)
        st.write("---")
else:
    st.warning("No responses generated yet. Go to 'Email Summary' and generate first.")