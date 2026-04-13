import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


def escalate_to_human(state: dict) -> dict:
    log_path = "data/escalations.log"

    # This used to assume the directory exists.
    # First prod run on a fresh machine = instant crash.
    os.makedirs("data", exist_ok=True)

    try:
        with open(log_path, "a") as f:
            f.write(
                f"{datetime.utcnow().isoformat()} | "
                f"pipeline_id={state.get('pipeline_id')} | "
                f"root_cause={state.get('root_cause')} | "
                f"proposed_fix={state.get('proposed_fix')} | "
                f"confidence={state.get('confidence')}\n"
            )

    except Exception as e:
        # Escalation failing silently is worse than the original bug.
        # At least surface it.
        logger.warning("failed to persist escalation log: %s", e)

    state["final_status"] = "escalated"
    return state