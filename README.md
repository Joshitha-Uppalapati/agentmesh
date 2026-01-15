# AgentMesh
Multi-agent system for automated data pipeline debugging using LangGraph.

## Overview
AgentMesh detects pipeline failures, investigates root causes, proposes fixes, and validates them before escalating to humans. Built with LangGraph for controlled multi-agent workflows.

## Architecture

**Agent Flow:**
1. **Monitor** → Detects failures and symptoms
2. **Investigator** → Diagnoses root cause using logs + RAG
3. **Fixer** → Proposes code/config/schema fixes
4. **Validator** → Tests fixes in sandbox before approval

**Control Flow:**
- Retry limits prevent infinite loops
- Escalation paths for human review
- State tracking for observability

## Quick Start
```bash
# Install dependencies
pip install -r requirements.txt

# Add API key (optional)
cp .env.example .env
# Edit .env with your Anthropic/OpenAI key

# Run demo
python run_demo.py
```

## Project Structure
```
agentmesh/
├── src/
│   ├── agents/        # Individual agent logic
│   ├── graph/         # LangGraph orchestration
│   ├── tools/         # Log analyzer, vector store
│   ├── prompts/       # Separated prompt templates
│   └── config/        # Settings management
├── tests/             # Unit tests
├── data/              # Sample logs, vector DB
└── run_demo.py        # Demo script
```

## Key Design Decisions

**Why multi-agent?**
- Separation of concerns: detection ≠ diagnosis ≠ remediation
- Each agent has specific responsibilities and failure modes
- Debuggability: Can pinpoint which agent made bad decisions

**Why LangGraph?**
- Explicit control flow (not just prompt chaining)
- Built-in retry and routing logic
- State management across agents

**Why ChromaDB?**
- Local development (no external deps)
- Vector search for similar past failures
- Lightweight for MVP

## Limitations
- Mock LLM responses when no API key (for development)
- Simple log parsing (regex-based)
- No actual sandbox execution (validation is simulated)
- Single-pipeline focus (no concurrent processing)

## What Would Break at Scale

**Bottleneck:** Investigator agent (I/O bound - fetching logs, querying vector DB)

**What breaks first:** Cost (LLM calls per pipeline check)

**Would measure:** Time-to-fix, false positive rate, fix acceptance rate

## Trade-offs

**Used Chroma because:** Fast local setup, good enough for 1000s of failures

**Wouldn't use Chroma if:** Multi-tenancy needed, ACID guarantees required, or Pinecone already in prod stack

## Future Improvements
- Real sandbox validation (Docker containers)
- Streaming LLM responses for faster UX
- Memory across runs (agent learns from past fixes)
- Multi-pipeline batch processing
- Cost optimization (cache common diagnoses)

## Built With
- LangGraph 0.2.45 - Agent orchestration
- LangChain 0.3.15 - LLM integration
- ChromaDB 0.5.23 - Vector storage
- FastAPI 0.115.6 - API wrapper (future)

## License
MIT
