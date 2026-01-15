import json
from datetime import datetime

def persist_escalation(state):
    payload = {
        "pipeline_id": state.get("pipeline_id"),
        "root_cause": state.get("root_cause"),
        "proposed_fix": state.get("proposed_fix"),
        "timestamp": datetime.utcnow().isoformat(),
    }

    with open("data/escalations.log", "a") as f:
        f.write(json.dumps(payload) + "\n")

