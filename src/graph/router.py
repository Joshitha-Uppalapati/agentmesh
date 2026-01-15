from src.graph.state import AgentState
from typing import Literal


def should_investigate(state: AgentState) -> Literal["healthy", "investigate"]:
    if state.get("failure_detected", False):
        return "investigate"
    return "healthy"


def should_retry_fix(state: AgentState) -> Literal["validate", "retry", "escalate"]:
    retry_count = state.get("retry_counts", {}).get("Fixer", 0)
    
    if retry_count >= 3:
        return "escalate"
    
    if not state.get("proposed_fix"):
        return "retry"
    
    return "validate"


def route_after_validation(state: AgentState) -> Literal["approved", "retry_fix", "escalate"]:
    result = state.get("validation_result")
    retry_count = state.get("retry_counts", {}).get("Validator", 0)
    
    if result == "approved":
        return "approved"
    
    if retry_count >= 2:
        return "escalate"
    
    return "retry_fix"
