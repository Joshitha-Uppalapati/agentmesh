from typing import Dict, Any
from datetime import datetime
import os


class BaseAgent:
    
    def __init__(self, name: str):
        self.name = name
        self.llm_provider = self._init_llm()
    
    def _init_llm(self):
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        
        if anthropic_key:
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model="claude-3-5-sonnet-20241022", api_key=anthropic_key)
        elif openai_key:
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model="gpt-4o-mini", api_key=openai_key)
        else:
            # Mock LLM for development without API keys
            return None
    
    def call_llm(self, prompt: str, state: Dict[str, Any]) -> str:
        if self.llm_provider is None:
            return self._mock_response(prompt, state)
        
        try:
            response = self.llm_provider.invoke(prompt)
            
            # Track cost (approximate)
            state["total_llm_calls"] = state.get("total_llm_calls", 0) + 1
            state["total_cost_usd"] = state.get("total_cost_usd", 0.0) + 0.001
            
            return response.content
        except Exception as e:
            print(f"LLM error in {self.name}: {e}")
            return self._mock_response(prompt, state)
    
    def _mock_response(self, prompt: str, state: Dict[str, Any]) -> str:
        if "Monitor" in self.name:
            return """health_status: failed
failure_detected: true
failure_symptoms: ["Missing data in target table orders_daily", "Last successful run was 6 hours ago"]"""
        
        elif "Investigator" in self.name:
            return """root_cause: Source API rate limit exceeded - receiving 429 errors
confidence_score: 0.85
relevant_logs: ["2024-01-15 10:23:45 ERROR: API returned 429", "2024-01-15 10:23:46 WARN: Retry attempt 3 failed"]"""
        
        elif "Fixer" in self.name:
            return """proposed_fix: Add exponential backoff retry logic with max 5 attempts and 60s delay
fix_type: code
fix_reasoning: Rate limit errors need retry logic to handle temporary API unavailability
estimated_impact: Affects API client module, no schema changes"""
        
        elif "Validator" in self.name:
            return """validation_result: approved
validation_reasoning: Retry logic properly implements exponential backoff, tested with simulated rate limits
test_results: {"syntax_check": "pass", "sandbox_test": "pass", "edge_cases": "pass"}"""
        
        return "Mock response"
    
    def increment_retry(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if "retry_counts" not in state:
            state["retry_counts"] = {}
        
        state["retry_counts"][self.name] = state["retry_counts"].get(self.name, 0) + 1
        return state
    
    def log_action(self, action: str, state: Dict[str, Any]):
        timestamp = datetime.now().strftime("%H:%M:%S")
        pipeline = state.get("pipeline_id", "unknown")
        print(f"[{timestamp}] {self.name} | {pipeline} | {action}")
