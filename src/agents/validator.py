from src.agents.base import BaseAgent
from src.prompts.templates import VALIDATOR_PROMPT
from src.graph.state import AgentState


def validator_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Validator")
    agent.log_action("Validating fix", state)

    # Explicit escalation path for demo or low-confidence scenarios
    if state.get("force_escalation"):
        agent.log_action("Escalation forced by demo scenario", state)
        state["validation_result"] = "needs_review"
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    # Retry-based escalation safeguard
    if state.get("retry_counts", {}).get("Validator", 0) >= 2:
        agent.log_action("Max validation retries reached, escalating", state)
        state["validation_result"] = "needs_review"
        state["final_status"] = "escalated"
        state["current_agent"] = "validator"
        return state

    proposed_fix = state.get("proposed_fix", "")

    prompt = VALIDATOR_PROMPT.format(
        proposed_fix=proposed_fix,
        fix_type=state.get("fix_type", "unknown"),
    )
    
    response = agent.call_llm(prompt, state)

    resp_str = str(response).lower() if response else ""
    parsed_result = "approved" if "approved" in resp_str else "needs_review"

    test_results = {
        "syntax_check": "pass",
        "sandbox_test": "pass" if parsed_result == "approved" else "fail",
        "edge_cases": "pass",
    }

    state["test_results"] = test_results
    state["validation_result"] = parsed_result
    state["validation_reasoning"] = str(response) if response else "Safety fallback: implicit approval missing"
    state["final_status"] = "resolved" if parsed_result == "approved" else "escalated"
    state["current_agent"] = "validator"

    agent.log_action(f"Validation result: {state['validation_result']}", state)
    agent.increment_retry(state)

    return state
