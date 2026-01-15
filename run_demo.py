from src.graph.builder import build_graph
from src.graph.state import AgentState
from src.tools.vector_store import VectorStore
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()


def run_demo():
    """Run a sample pipeline debugging scenario."""
    print("="*60)
    print("AgentMesh - Automated Pipeline Debugging")
    print("="*60)
    
    # Seed sample data in vector store
    print("\n📦 Initializing vector store with historical failures...")
    vector_store = VectorStore()
    vector_store.seed_sample_data()
    
    # Build graph
    print("🔨 Building agent graph...")
    graph = build_graph()
    
    # Initial state - simulating a failed pipeline
    initial_state = AgentState(
        pipeline_id="data_ingestion_prod",
        pipeline_config={
            "source": "external_api",
            "destination": "postgres",
            "schedule": "hourly"
        },
        retry_counts={},
        started_at=datetime.now(),
        total_llm_calls=0,
        total_cost_usd=0.0
    )
    
    print(f"\n🚀 Starting analysis for pipeline: {initial_state['pipeline_id']}")
    print("-"*60)
    
    # Run the graph
    final_state = graph.invoke(initial_state)
    
    # Print results
    print("\n" + "="*60)
    print("RESULTS")
    print("="*60)
    print(f"Final Status: {final_state.get('final_status', 'unknown')}")
    print(f"Health: {final_state.get('health_status', 'unknown')}")
    
    if final_state.get('root_cause'):
        print(f"\n🔍 Root Cause: {final_state['root_cause']}")
        print(f"   Confidence: {final_state.get('confidence_score', 0):.0%}")
    
    if final_state.get('proposed_fix'):
        print(f"\n💡 Proposed Fix: {final_state['proposed_fix']}")
        print(f"   Type: {final_state.get('fix_type', 'unknown')}")
        print(f"   Validation: {final_state.get('validation_result', 'pending')}")
    
    print(f"\n📊 Metrics:")
    print(f"   LLM Calls: {final_state.get('total_llm_calls', 0)}")
    print(f"   Cost: ${final_state.get('total_cost_usd', 0):.4f}")
    
    completed = final_state.get('completed_at', datetime.now())
    started = final_state.get('started_at', datetime.now())
    duration = (completed - started).total_seconds()
    print(f"   Duration: {duration:.2f}s")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    run_demo()
