import os
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langsmith import traceable

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

def read_content(state):
    """This function currently reads the email from local files. Due to be changed to read from the streamlit app for usability."""
    file_path = "data/email1.txt"

    with open(file_path, 'r') as file:
        text = file.read()
        return {'email_text': text}

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
workflow.add_node("read_content", read_content)
workflow.add_node("llm_summary_response", llm_summary_response)
workflow.add_node("llm_email_responses", llm_email_responses)

workflow.add_edge(START, "read_content")
workflow.add_edge("read_content", "llm_summary_response")
workflow.add_edge("llm_summary_response", "llm_email_responses")
workflow.add_edge("llm_email_responses", END)

graph = workflow.compile()
result = graph.invoke({"email_text": "Hello, I am writing to you to discuss the project we are working on."})
print(result)
