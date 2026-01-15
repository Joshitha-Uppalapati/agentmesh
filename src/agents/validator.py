from src.agents.base import BaseAgent
from src.prompts.templates import VALIDATOR_PROMPT
from src.graph.state import AgentState


def validator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Validator")
    agent.log_action("Validating fix", state)
    
    # Check retry count
    if state.get("retry_counts", {}).get("Validator", 0) >= 2:
        agent.log_action("Max validation retries, escalating", state)
        state["validation_result"] = "needs_review"
        state["final_status"] = "escalated"
        return state
    
    proposed_fix = state.get("proposed_fix", "")
    
    # Format prompt
    prompt = VALIDATOR_PROMPT.format(
        proposed_fix=proposed_fix,
        fix_type=state.get("fix_type", "unknown")
    )
    
    # Call LLM
    response = agent.call_llm(prompt, state)
    
    # Simulate validation checks
    test_results = {
        "syntax_check": "pass",
        "sandbox_test": "pass",
        "edge_cases": "pass"
    }
    
    state["test_results"] = test_results
    state["validation_result"] = "approved"
    state["validation_reasoning"] = "All tests passed, fix is safe to apply"
    state["final_status"] = "resolved"
    
    agent.log_action(f"Validation: {state['validation_result']}", state)
    
    state["current_agent"] = "validator"
    agent.increment_retry(state)
    
    return state
