from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import ToolNode
from langchain_core.messages import RemoveMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from httpx import HTTPStatusError
import time
from LLM.llm import llm, llm_with_tools, tools, load_prompt

prompt_template = ChatPromptTemplate.from_messages(
    [
        ("system", load_prompt('assistant'),),
        MessagesPlaceholder(variable_name="messages")
    ])

summary_prompt = load_prompt("dialogue_summary")

def should_continue(state: MessagesState):
    messages = state["messages"]
    last_message = messages[-1]
    if last_message.tool_calls:
        return "tools"
    return END

def trim_messages(state: MessagesState):
    if len(state["messages"]) >= 10 and state["messages"][-1].type == "human":
        last_human_message = state["messages"][-1]
        summary_message = llm.invoke(state["messages"][:-1] + [HumanMessage(content=summary_prompt)])
        delete_messages = [RemoveMessage(id=m.id) for m in state["messages"]]
        history = [summary_message, last_human_message]
    else:
        delete_messages = []
        history = state["messages"]
    return history, delete_messages


def call_model(state: MessagesState):
    messages, delete_messages = trim_messages(state)
    prompt = prompt_template.invoke({"messages": messages})
    try:
        response = llm_with_tools.invoke(prompt)
    except HTTPStatusError:
        time.sleep(2)
        response = llm_with_tools.invoke(prompt)
    message_updates = messages + [response] + delete_messages
    return {"messages": message_updates}

workflow = StateGraph(MessagesState)
tool_node = ToolNode(tools)
memory = MemorySaver()

workflow.add_node("agent", call_model)
workflow.add_node("tools", tool_node)

workflow.add_edge(START, "agent")
workflow.add_conditional_edges("agent", should_continue, ["tools", END])
workflow.add_edge("tools", "agent")

app = workflow.compile(checkpointer=memory)
