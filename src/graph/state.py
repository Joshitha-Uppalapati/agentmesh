from typing import TypedDict, Optional, Dict, List, Literal
from datetime import datetime


class AgentState(TypedDict, total=False):
    
    # INPUT - Set at start
    pipeline_id: str
    pipeline_config: Dict
    
    # MONITOR AGENT - Writes these
    health_status: Literal["healthy", "degraded", "failed"]
    failure_detected: bool
    failure_timestamp: Optional[datetime]
    failure_symptoms: List[str]
    
    # INVESTIGATOR AGENT - Writes these
    investigation_complete: bool
    root_cause: Optional[str]
    relevant_logs: List[str]
    similar_past_failures: List[Dict]
    confidence_score: float
    
    # FIXER AGENT - Writes these
    proposed_fix: Optional[str]
    fix_type: Optional[Literal["code", "config", "schema"]]
    fix_reasoning: str
    estimated_impact: str
    
    # VALIDATOR AGENT - Writes these
    validation_result: Optional[Literal["approved", "rejected", "needs_review"]]
    validation_reasoning: str
    test_results: Dict
    
    # CONTROL FLOW - System manages
    retry_counts: Dict[str, int]
    current_agent: str
    final_status: Optional[Literal["resolved", "escalated", "failed"]]
    
    # METADATA - Tracking
    started_at: datetime
    completed_at: Optional[datetime]
    total_llm_calls: int
    total_cost_usd: float
