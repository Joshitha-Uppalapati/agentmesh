from langgraph.graph import StateGraph, END
from src.graph.state import AgentState
from src.graph.router import should_investigate, should_retry_fix, route_after_validation
from src.agents.monitor import monitor_agent
from src.agents.investigator import investigator_agent
from src.agents.fixer import fixer_agent
from src.agents.validator import validator_agent


def escalate_to_human(state: AgentState) -> AgentState:
    print("\n🚨 ESCALATED TO HUMAN REVIEW")
    print(f"Reason: {state.get('validation_reasoning', 'Max retries exceeded')}")
    state["final_status"] = "escalated"
    return state


def build_graph():
    graph = StateGraph(AgentState)
    
    # Add nodes
    graph.add_node("monitor", monitor_agent)
    graph.add_node("investigator", investigator_agent)
    graph.add_node("fixer", fixer_agent)
    graph.add_node("validator", validator_agent)
    graph.add_node("escalate", escalate_to_human)
    
    # Set entry point
    graph.set_entry_point("monitor")
    
    # Add edges
    graph.add_conditional_edges(
        "monitor",
        should_investigate,
        {
            "healthy": END,
            "investigate": "investigator"
        }
    )
    
    graph.add_edge("investigator", "fixer")
    
    graph.add_conditional_edges(
        "fixer",
        should_retry_fix,
        {
            "validate": "validator",
            "retry": "investigator",
            "escalate": "escalate"
        }
    )
    
    graph.add_conditional_edges(
        "validator",
        route_after_validation,
        {
            "approved": END,
            "retry_fix": "fixer",
            "escalate": "escalate"
        }
    )
    
    graph.add_edge("escalate", END)
    
    return graph.compile()
