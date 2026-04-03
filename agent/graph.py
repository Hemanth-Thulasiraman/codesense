from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agent.state import AgentState
from agent.nodes import (
    fetch_diff, static_analysis, security_check,
    llm_review, notify_slack, post_review,
    save_result, emergency_stop
)

MAX_TOOL_CALLS = 12

def should_continue(state: AgentState) -> str:
    if state.get("status") == "FAILED":
        return "emergency_stop"
    if state.get("tool_call_count", 0) >= MAX_TOOL_CALLS:
        return "emergency_stop"
    return "continue"

def build_graph():
    workflow = StateGraph(AgentState)
    # TODO: add all 8 nodes
    workflow.add_node("fetch_diff", fetch_diff)
    workflow.add_node("static_analysis", static_analysis)
    workflow.add_node("security_check", security_check)
    workflow.add_node("llm_review", llm_review)
    workflow.add_node("notify_slack", notify_slack)
    workflow.add_node("post_review", post_review)
    workflow.add_node("save_result", save_result)
    workflow.add_node("emergency_stop", emergency_stop)
    # TODO: set entry point to fetch_diff
    workflow.set_entry_point("fetch_diff")
    # TODO: add conditional edges after every node
    workflow.add_conditional_edges(
        "fetch_diff",
        should_continue,
        {
            "continue": "static_analysis",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_conditional_edges(
        "static_analysis",
        should_continue,
        {
            "continue": "security_check",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_conditional_edges(
        "security_check",
        should_continue,
        {
            "continue": "llm_review",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_conditional_edges(
        "llm_review",
        should_continue,
        {
            "continue": "notify_slack",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_conditional_edges(
        "notify_slack",
        should_continue,
        {
            "continue": "post_review",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_conditional_edges(
        "post_review",
        should_continue,
        {
            "continue": "save_result",
            "emergency_stop": "emergency_stop"
        }
    )
    workflow.add_edge("save_result", END)
    workflow.add_edge("emergency_stop", END)
    
    memory = MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["post_review"]
    )
graph = build_graph()