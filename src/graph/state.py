from datetime import datetime
from typing import Dict, List, Literal, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # Entry payload. Keep this skinny or every node ends up doing defensive unpacking.
    pipeline_id: str
    pipeline_config: Dict

    # Traceability - Batch 4 (correlation across agents/logs)
    run_id: str

    # Demo switches. Keeping this in state avoided messy branching through kwargs.
    force_escalation: bool

    # Monitor output
    health_status: Literal["healthy", "degraded", "failed"]
    failure_detected: bool
    failure_timestamp: Optional[datetime]
    failure_symptoms: List[str]

    # Investigator output
    investigation_complete: bool
    root_cause: Optional[str]
    relevant_logs: List[str]
    similar_past_failures: List[Dict]

    # confidence is a model hallucination risk, but useful for routing decisions
    confidence_score: Optional[float]

    # Fixer output
    proposed_fix: Optional[str]
    fix_type: Optional[Literal["code", "config", "schema"]]
    fix_reasoning: Optional[str]
    estimated_impact: Optional[str]

    # Validator output
    validation_result: Optional[Literal["approved", "rejected", "needs_review"]]
    validation_reasoning: Optional[str]
    test_results: Optional[Dict]

    # Graph bookkeeping.
    retry_counts: Dict[str, int]
    current_agent: str
    final_status: Optional[Literal["resolved", "escalated", "failed"]]

    # Run metadata
    started_at: datetime
    completed_at: Optional[datetime]
    total_llm_calls: int
    total_cost_usd: float
    