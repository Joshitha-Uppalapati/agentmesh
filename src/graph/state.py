from datetime import datetime
from typing import Dict, List, Literal, Optional, TypedDict


class AgentState(TypedDict, total=False):
    # Entry payload. Keep this skinny or every node ends up doing defensive unpacking.
    pipeline_id: str
    pipeline_config: Dict

    # Demo switches. I left them in state instead of kwargs because LangGraph routing got annoying
    # once the branching logic started depending on scenario flags.
    force_escalation: bool

    # Monitor owns failure detection. Other nodes should read these, not reinterpret them.
    health_status: Literal["healthy", "degraded", "failed"]
    failure_detected: bool
    failure_timestamp: Optional[datetime]
    failure_symptoms: List[str]

    # Investigator writes diagnosis. The temptation is to let Fixer mutate root_cause too.
    # Don't. That turned into state whiplash fast during early graph experiments.
    investigation_complete: bool
    root_cause: Optional[str]
    relevant_logs: List[str]
    similar_past_failures: List[Dict]
    confidence_score: float

    # Fixer output.
    proposed_fix: Optional[str]
    fix_type: Optional[Literal["code", "config", "schema"]]
    fix_reasoning: str
    estimated_impact: str

    # Validator output.
    validation_result: Optional[Literal["approved", "rejected", "needs_review"]]
    validation_reasoning: str
    test_results: Dict

    # Graph bookkeeping.
    retry_counts: Dict[str, int]
    current_agent: str
    final_status: Optional[Literal["resolved", "escalated", "failed"]]

    # Run metadata.
    started_at: datetime
    completed_at: Optional[datetime]
    total_llm_calls: int
    total_cost_usd: float