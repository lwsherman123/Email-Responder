import os
import re
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

import streamlit as st

from prompts.response_prompt import email_response_prompt
from prompts.summary_prompt import email_summary_prompt
from prompts.spam_checker_prompt import spam_checker_prompt

# Configure OpenAI API
llm = ChatOpenAI(
    api_key=os.getenv('OPENAI_API_KEY'),
    model='gpt-4o-mini',
    max_tokens=1000,
    temperature=0.1,
)

# AgentState model to track the state throughout the workflow. 
class AgentState(BaseModel):
    email_text: str = ''
    summary_llm_response: str = ''
    sentiment: str = ''
    category: str = ''
    email_responses: list[dict[str, str]] = []
    is_spam: bool = False
    summary_length: int = 50

def llm_spam_checker(state):
    """Basic spam checker using keyword matching."""
    response = llm.invoke(
        input = [
            {"role":"system", "content": spam_checker_prompt},
            {"role":"user", "content": state.email_text}
        ]
    )
    is_spam = response.content.lower().strip() == "spam"
    return {'is_spam': is_spam}

@traceable
def llm_summary_response(state) -> dict:
    """Generates the email summary, sentiment, and category using LLM."""
    full_summary_prompt = email_summary_prompt + f"\n\nSummarise in approximately {state.summary_length} words."
    response = llm.invoke(
        input = [
            {"role":"system", "content": full_summary_prompt},
            {"role":"user", "content": state.email_text}
        ]
    )

    content = response.content.strip()

    # Extract summary, sentiment, and category using regex
    summary_match = re.search(r"Summary:\s*(.*?)\nSentiment:", content, re.DOTALL)
    sentiment_match = re.search(r"Sentiment:\s*(\w+)", content)
    category_match = re.search(r"Category:\s*(\w+)", content)

    summary = summary_match.group(1).strip() if summary_match else "No summary provided."
    sentiment = sentiment_match.group(1).strip() if sentiment_match else "Neutral"
    category = category_match.group(1).strip() if category_match else "Uncategorized"

    return {
        'summary_llm_response': summary,
        'sentiment': sentiment,
        'category': category
        }

@traceable
def llm_email_responses(state) -> dict:
    """Generates email responses if the email is not flagged as spam."""
    if state.is_spam:
        return {'email_responses': ["⚠️ This email was flagged as spam, so no responses were generated."]}
    
    response = llm.invoke(
        input=[
            {"role": "system", "content": email_response_prompt},
            {"role": "user", "content": state.email_text}
        ]
    )
    return {'email_responses': response.content.split("---")}

workflow = StateGraph(AgentState)
workflow.add_node("llm_summary_response", llm_summary_response)
workflow.add_node("llm_email_responses", llm_email_responses)
workflow.add_node("llm_spam_checker", llm_spam_checker)

workflow.add_edge(START, "llm_spam_checker")
workflow.add_edge("llm_spam_checker", "llm_summary_response")
workflow.add_edge("llm_summary_response", "llm_email_responses")
workflow.add_edge("llm_email_responses", END)

graph = workflow.compile()

st.title("📄 Email Assistant")
email_text = st.text_area("Paste your email here:", height=200)

summary_length = st.slider("Select Summary Length: ", min_value=50, max_value=300, value=50, step=20)

#Store Results in Session State
if "summary" not in st.session_state:
    st.session_state.summary = ""
if "responses" not in st.session_state:
    st.session_state.responses = []
if "sentiment" not in st.session_state:
    st.session_state.sentiment = "Neutral"
if "category" not in st.session_state:
    st.session_state.category = "Uncategorized"


if st.button("Generate Summary"):
    if email_text.strip():
        result = graph.invoke({"email_text": email_text, "summary_length": summary_length})

        st.session_state.is_spam = result['is_spam']
        st.session_state.summary = result['summary_llm_response']
        st.session_state.responses = result['email_responses']
        st.session_state.sentiment = result['sentiment']
        st.session_state.category = result['category']
        st.success("Summary Generated Successfully!")
    else:
        st.warning("Please enter an email first.")

if st.session_state.summary:
    if st.session_state.is_spam:
        st.warning("⚠️ This email has been flagged as **possible spam**. Please review carefully.")

    st.subheader("📌 Email Summary:")
    st.write(st.session_state.summary)

    st.subheader("📊 Sentiment Analysis:")
    st.write(f"**{st.session_state.sentiment}**")

    st.subheader("📚 Category:")
    st.write(f"**{st.session_state.category}**")

