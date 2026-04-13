# AgentMesh
AgentMesh is a reliability-first multi-agent system designed to diagnose and respond to pipeline failures.

It is built using LangGraph with explicit node transitions and conditional routing.  
The system emphasizes separation of detection and diagnosis, confidence-based escalation, and structured LLM outputs.

---

## Architecture Overview

The system is composed of four primary agents:

- **Monitor**: Detects pipeline anomalies based on health signals  
- **Investigator**: Diagnoses root cause using structured LLM output  
- **Fixer**: Proposes remediation actions based on diagnosis  
- **Validator**: Evaluates proposed fixes before execution  

Routing is handled via explicit graph edges and conditional transitions.  
Each agent operates on a shared `AgentState` object with defined ownership of fields to avoid state conflicts.

Key design choices:
- Separation of detection vs diagnosis (Monitor vs Investigator)
- Per-agent retry tracking instead of global retries
- Confidence-based routing to prevent unsafe automation

Example failure scenario:
- Monitor detects missing data in a downstream table
- Investigator identifies upstream API rate limiting as root cause
- Fixer proposes retry/backoff logic
- Validator evaluates the change before approval

---

## The "Reliability" Refactor

Early versions of this system relied on string parsing and keyword matching over LLM outputs.  
This approach was brittle and produced incorrect state transitions under ambiguity.

The system now uses structured outputs via `llm.with_structured_output(...)` with Pydantic models:

- `InvestigationResult`
- `FixProposal`
- `ValidationResult`

This change eliminates:
- False positives from keyword matching
- Inconsistent parsing across agents
- Silent failure modes

It also makes agent behavior explicit and testable.

---

## Observability

Each execution is assigned a `run_id` (UUID) at graph entry.  
This ID is propagated through all agent logs.

Logging follows a consistent structured format:
- No `print()` statements
- All logs include `run_id`, `agent`, and `pipeline_id`

Example log:
```
run_id=abc-123 agent=Investigator pipeline=orders_etl action=diagnosis_completed
```

This makes it possible to trace a single execution across agents and reconstruct failures after the run.

LLM calls include:
- Call count tracking
- Cost estimation (approximate, model-dependent)
- Timeout enforcement (30s) to prevent graph hangs

---

## Known Limitations

- No retry/backoff for LLM calls (timeouts fail fast)
- No distributed tracing (logs only)
- Validator does not execute real sandboxed code
- Vector store schema is implicit and not versioned

---

## Future Roadmap

- Add retry + exponential backoff using Tenacity
- Integrate LangSmith for trace-level observability
- Replace Validator with real sandbox execution (Docker-based)
- Introduce typed state schema validation at graph boundaries
- Add async execution (`graph.ainvoke`) for concurrency

---

## Setup

Requires Python 3.10+
```
pip install -r requirements.txt
```

---

## Running the System

Requires one of:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`

```
python run_demo.py
```
Without an API key, agents fall back to deterministic logic and the system runs in demo mode.

---

## License
MIT
