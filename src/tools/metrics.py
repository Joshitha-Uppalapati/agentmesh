import logging

logger = logging.getLogger(__name__)


def log_metrics(state: dict):
    # Keep this simple — this is mostly for demo visibility.
    # If we expand this, it should move to a proper metrics sink (Prometheus, etc.)

    logger.info(
        "metrics pipeline=%s llm_calls=%d cost=%.6f",
        state.get("pipeline_id"),
        state.get("total_llm_calls", 0),
        state.get("total_cost_usd", 0.0),
    )