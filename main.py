import os
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

import streamlit as st

from prompts.response_prompt import email_response_prompt
from prompts.summary_prompt import email_summary_prompt

llm = ChatOpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    model='gpt-4o-mini',
    max_tokens=1000,
    temperature=0.1,
)

class AgentState(BaseModel):
    email_text: str = ''
    summary_llm_response: str = ''
    email_responses: list[str] = []

@traceable
def llm_summary_response(state):
    response = llm.invoke(
        input = [
            {"role":"system", "content": email_summary_prompt},
            {"role":"user", "content": state.email_text}
        ]
    )
    summary = response.content
    return {'summary_llm_response': summary}

@traceable
def llm_email_responses(state):
    response = llm.invoke(
        input = [
            {"role":"system", "content": email_response_prompt},
            {"role":"user", "content": state.email_text}
        ]
    )
    email_responses = response.content.split("---")
    return {'email_responses': email_responses}

workflow = StateGraph(AgentState)
workflow.add_node("llm_summary_response", llm_summary_response)
workflow.add_node("llm_email_responses", llm_email_responses)

workflow.add_edge(START, "llm_summary_response")
workflow.add_edge("llm_summary_response", "llm_email_responses")
workflow.add_edge("llm_email_responses", END)

graph = workflow.compile()

st.title("Email Assistant")

page = st.sidebar.radio("Select a page", ["Email Summary", "Email Responses"])

#Store Results in Session State
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "responses" not in st.session_state:
    st.session_state.responses = []

if page == "Email Summary":
    st.subheader("Enter Email Text:")
    email_text = st.text_area("Paste your email here:", height=200)

    if st.button("Generate Summary"):
        if email_text.strip():
            result = graph.invoke({"email_text": email_text})
            st.session_state.summary = result['summary_llm_response']
            st.session_state.responses = result['email_responses']
            st.success("Summary Generated Successfully!")
        else:
            st.warning("Please enter an email first.")

    if st.session_state.summary:
        st.subheader("Email Summary:")
        st.write(st.session_state.summary)

elif page == "Email Responses":
    st.subheader("Generated Email Responses:")
    if st.session_state.responses:
        for i, response in enumerate(st.session_state.responses):
            st.write(response)
    else:
        st.warning("No response generated yet. Go to 'Email Summary' and generate first.")
