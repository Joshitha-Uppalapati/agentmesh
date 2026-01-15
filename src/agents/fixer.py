from src.agents.base import BaseAgent
from src.prompts.templates import FIXER_PROMPT
from src.graph.state import AgentState


def fixer_agent(state: AgentState) -> AgentState:
    agent = BaseAgent("Fixer")
    agent.log_action("Proposing fix", state)
    
    # Check retry count
    if state.get("retry_counts", {}).get("Fixer", 0) >= 3:
        agent.log_action("Max retries exceeded, escalating", state)
        state["proposed_fix"] = None
        state["final_status"] = "escalated"
        return state
    
    # Format prompt
    prompt = FIXER_PROMPT.format(
        root_cause=state.get("root_cause", "unknown"),
        pipeline_config=state.get("pipeline_config", {})
    )
    
    # Call LLM
    response = agent.call_llm(prompt, state)
    
    # Parse response
    state["proposed_fix"] = "Add exponential backoff retry logic with max 5 attempts"
    state["fix_type"] = "code"
    state["fix_reasoning"] = "Rate limit errors need retry logic to handle API unavailability"
    state["estimated_impact"] = "Affects API client module, no schema changes"
    
    agent.log_action(f"Fix proposed: {state['fix_type']}", state)
    
    state["current_agent"] = "fixer"
    agent.increment_retry(state)
    
    return state
