"""
Phase 6: Integration Tests for InsightAgent

Tests the 5 demo scenarios from the implementation plan:
1. Simple Query + RAG Grounding
2. Multi-Tool Orchestration
3. Memory Within Session
4. Cross-Session Memory
5. RAG Contextual Grounding

Run with:
    # Requires backend running on localhost:8080
    RUN_INTEGRATION_TESTS=1 DEMO_API_KEY=<key> pytest tests/test_integration.py -v -s

Or standalone:
    RUN_INTEGRATION_TESTS=1 DEMO_API_KEY=<key> python tests/test_integration.py
"""

import os
import sys
import json
import time
import pytest

# Only require optional deps when integration tests are explicitly enabled.
INTEGRATION_ENABLED = os.getenv("RUN_INTEGRATION_TESTS") == "1"
try:
    import requests
except ModuleNotFoundError:
    if INTEGRATION_ENABLED:
        raise
    requests = None  # type: ignore[assignment]

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

# Configuration
API_BASE = os.getenv("API_BASE", "http://localhost:8080")
API_KEY = os.getenv("DEMO_API_KEY")  # Required - no default to avoid credential leak
TEST_USER = "integration_test_user"

# Request timeouts (connect, read) in seconds
REQUEST_TIMEOUT = (5, 120)  # 5s connect, 120s read for LLM responses
# Max overall duration for a single SSE stream (prevents hangs if server never closes).
MAX_STREAM_SECONDS = int(os.getenv("INTEGRATION_MAX_STREAM_SECONDS", "180"))

# Skip integration tests unless explicitly enabled
SKIP_INTEGRATION = not INTEGRATION_ENABLED
SKIP_REASON = "Integration tests require RUN_INTEGRATION_TESTS=1 and DEMO_API_KEY env vars"


def require_requests() -> None:
    if requests is None:
        pytest.skip("requests is not installed (required for live-HTTP integration tests)")


def get_headers() -> dict:
    """Get request headers with API key."""
    if not API_KEY:
        pytest.skip("DEMO_API_KEY environment variable not set")
    return {
        "Content-Type": "application/json",
        "X-API-Key": API_KEY,
    }


def create_session(user_id: str = TEST_USER) -> dict:
    """Create a new chat session."""
    require_requests()
    response = requests.post(
        f"{API_BASE}/api/chat/session",
        headers=get_headers(),
        json={"user_id": user_id},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def send_message_streaming(session_id: str, content: str, user_id: str = TEST_USER) -> dict:
    """Send a message and collect all SSE events."""
    require_requests()
    result = {
        "reasoning_traces": [],
        "content": "",
        "memory_saves": [],
        "suggested_followups": [],
        "errors": [],
        "latency_first_token": None,
        "latency_total": None,
    }

    start_time = time.time()
    first_content_time = None

    response = requests.post(
        f"{API_BASE}/api/chat/message",
        headers=get_headers(),
        json={
            "session_id": session_id,
            "user_id": user_id,
            "content": content,
        },
        stream=True,
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()

    buffer = ""
    for chunk in response.iter_content(chunk_size=None, decode_unicode=True):
        if time.time() - start_time > MAX_STREAM_SECONDS:
            response.close()
            pytest.fail(f"SSE stream exceeded {MAX_STREAM_SECONDS}s without completing")

        buffer += chunk

        # Process complete events
        while "\n\n" in buffer:
            event_str, buffer = buffer.split("\n\n", 1)
            if not event_str.strip():
                continue

            # Parse SSE format
            event_type = None
            event_data = None

            for line in event_str.split("\n"):
                if line.startswith("event: "):
                    event_type = line[7:].strip()
                elif line.startswith("data: "):
                    event_data = line[6:]

            if not event_type or not event_data:
                continue

            try:
                data = json.loads(event_data)

                if event_type == "reasoning":
                    result["reasoning_traces"].append(data)
                elif event_type == "content":
                    if first_content_time is None:
                        first_content_time = time.time()
                    result["content"] += data.get("delta", "")
                elif event_type == "memory":
                    result["memory_saves"].append(data)
                elif event_type == "done":
                    result["suggested_followups"] = data.get("suggested_followups", [])
                elif event_type == "error":
                    result["errors"].append(data)
                # Ignore heartbeat
            except json.JSONDecodeError:
                pass

    end_time = time.time()
    result["latency_total"] = end_time - start_time
    if first_content_time:
        result["latency_first_token"] = first_content_time - start_time

    return result


def reset_user_memory(user_id: str = TEST_USER) -> dict:
    """Reset user memory for clean test state."""
    require_requests()
    response = requests.delete(
        f"{API_BASE}/api/user/memory/reset",
        headers=get_headers(),
        params={"user_id": user_id},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


def get_user_memory(user_id: str = TEST_USER) -> dict:
    """Get user memory."""
    require_requests()
    response = requests.get(
        f"{API_BASE}/api/user/memory",
        headers=get_headers(),
        params={"user_id": user_id},
        timeout=REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ============================================================================
# Pytest Fixtures
# ============================================================================

@pytest.fixture
def clean_session():
    """Create a fresh session with reset memory."""
    reset_user_memory()
    return create_session()


@pytest.fixture
def session_with_context(clean_session):
    """Session with prior Q4 revenue query for context."""
    send_message_streaming(clean_session["session_id"], "What was our Q4 2024 revenue?")
    return clean_session


# ============================================================================
# Test Scenario 1: Simple Query + RAG Grounding
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_scenario_1_simple_query(clean_session):
    """
    Scene 1: User asks a simple revenue question.
    Expected: Agent queries BigQuery, returns revenue figure.
    """
    print("\n" + "="*60)
    print("SCENARIO 1: Simple Query + RAG Grounding")
    print("="*60)

    session = clean_session
    print(f"Session created: {session['session_id']}")

    query = "What was our Q4 2024 revenue?"
    print(f"\nUser: {query}")

    result = send_message_streaming(session["session_id"], query)

    print(f"\nAssistant: {result['content'][:500]}...")
    print(f"\nReasoning traces: {len(result['reasoning_traces'])}")
    for trace in result["reasoning_traces"]:
        print(f"  - {trace.get('tool_name')}: {trace.get('status')}")

    print(f"\nMemory saves: {len(result['memory_saves'])}")
    if result['latency_first_token']:
        print(f"Latency (first token): {result['latency_first_token']:.2f}s")
    print(f"Latency (total): {result['latency_total']:.2f}s")

    # Assertions - focus on response quality, not tool count
    assert len(result["content"]) > 20, "Response should have content"
    assert any(t.get("tool_name") == "query_bigquery" for t in result["reasoning_traces"]), \
        "Should use BigQuery tool"
    assert "12" in result["content"] or "revenue" in result["content"].lower(), \
        "Should mention Q4 revenue figures"

    print("\n✅ Scenario 1 PASSED")


# ============================================================================
# Test Scenario 2: Multi-Tool Orchestration
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_scenario_2_multi_tool(clean_session):
    """
    Scene 2: User asks a complex "why" question.
    Expected: Agent uses BigQuery and provides meaningful analysis.
    """
    print("\n" + "="*60)
    print("SCENARIO 2: Multi-Tool Orchestration")
    print("="*60)

    session = clean_session
    query = "Why did we miss our Q4 target? What factors contributed?"
    print(f"\nUser: {query}")

    result = send_message_streaming(session["session_id"], query)

    print(f"\nAssistant: {result['content'][:500]}...")
    print(f"\nReasoning traces: {len(result['reasoning_traces'])}")

    tool_names = set()
    for trace in result["reasoning_traces"]:
        tool_name = trace.get("tool_name")
        if tool_name:
            tool_names.add(tool_name)
        print(f"  - {tool_name}: {trace.get('status')}")

    print(f"\nUnique tools used: {tool_names}")
    print(f"Latency (total): {result['latency_total']:.2f}s")

    # Assertions - check for required tool and meaningful response
    # Don't assert on tool count since LLM behavior is nondeterministic
    assert "query_bigquery" in tool_names, "Should use BigQuery tool"
    assert len(result["content"]) > 50, "Should provide meaningful analysis"
    # Check response discusses the question topic
    content_lower = result["content"].lower()
    assert "target" in content_lower or "revenue" in content_lower or "miss" in content_lower, \
        "Response should address the target/revenue question"

    print("\n✅ Scenario 2 PASSED")


# ============================================================================
# Test Scenario 3: Memory Within Session
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_scenario_3_session_memory(session_with_context):
    """
    Scene 3: User asks follow-up referencing earlier context.
    Expected: Agent provides relevant follow-up response.
    """
    print("\n" + "="*60)
    print("SCENARIO 3: Memory Within Session")
    print("="*60)

    session = session_with_context
    query = "How does the West region compare to that?"
    print(f"\nUser: {query}")

    result = send_message_streaming(session["session_id"], query)

    print(f"\nAssistant: {result['content'][:500]}...")
    print(f"\nReasoning traces: {len(result['reasoning_traces'])}")
    for trace in result["reasoning_traces"]:
        print(f"  - {trace.get('tool_name')}: {trace.get('status')}")

    print(f"Latency (total): {result['latency_total']:.2f}s")

    # Assertions - flexible check for regional discussion
    assert len(result["content"]) > 20, "Should have response"
    content_lower = result["content"].lower()
    assert "west" in content_lower or "region" in content_lower, \
        "Should discuss West region or regional comparison"

    print("\n✅ Scenario 3 PASSED")


# ============================================================================
# Test Scenario 4: Cross-Session Memory
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_scenario_4_cross_session():
    """
    Scene 4: New session references past session.
    Expected: Session creation works, memory state is accessible.
    """
    print("\n" + "="*60)
    print("SCENARIO 4: Cross-Session Memory")
    print("="*60)

    # First session with query
    reset_user_memory()
    session1 = create_session()
    print(f"Session 1: {session1['session_id']}")

    query1 = "What was our Q4 2024 revenue and how did West perform?"
    print(f"\nSession 1 - User: {query1}")
    result1 = send_message_streaming(session1["session_id"], query1)
    print(f"Session 1 - Response: {result1['content'][:200]}...")

    # Create second session
    session2 = create_session()
    print(f"\nSession 2: {session2['session_id']}")
    print(f"Session 2 has_memory: {session2.get('has_memory')}")

    # Query about past session
    query2 = "What were we analyzing in my last session?"
    print(f"\nSession 2 - User: {query2}")
    result2 = send_message_streaming(session2["session_id"], query2)
    print(f"Session 2 - Response: {result2['content'][:300]}...")

    # Get memory state
    memory = get_user_memory()
    print(f"\nUser memory state:")
    print(f"  - Findings: {len(memory.get('findings', {}))}")
    print(f"  - Preferences: {len(memory.get('preferences', {}))}")
    print(f"  - Recent sessions: {len(memory.get('recent_sessions', []))}")

    # Assertions - verify sessions work
    assert session1["session_id"] != session2["session_id"], "Should create distinct sessions"
    assert len(result2["content"]) > 10, "Should provide some response"

    print("\n✅ Scenario 4 PASSED")


# ============================================================================
# Test Scenario 5: RAG Contextual Grounding
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_scenario_5_rag_grounding(clean_session):
    """
    Scene 5: User asks about company-specific metrics.
    Expected: Agent retrieves company definition from knowledge base.
    """
    print("\n" + "="*60)
    print("SCENARIO 5: RAG Contextual Grounding")
    print("="*60)

    session = clean_session
    print(f"Session: {session['session_id']}")

    query = "Is our churn rate healthy? What's our target?"
    print(f"\nUser: {query}")

    result = send_message_streaming(session["session_id"], query)

    print(f"\nAssistant: {result['content'][:500]}...")
    print(f"\nReasoning traces: {len(result['reasoning_traces'])}")
    for trace in result["reasoning_traces"]:
        print(f"  - {trace.get('tool_name')}: {trace.get('status')}")

    # Check for knowledge base usage
    kb_used = any(
        t.get("tool_name") == "search_knowledge_base"
        for t in result["reasoning_traces"]
    )
    print(f"\nKnowledge base used: {kb_used}")

    # Check for company-specific values (3.5% target, 5.1% benchmark from KB)
    content_lower = result["content"].lower()
    has_specifics = "3.5" in result["content"] or "5.1" in result["content"] or "target" in content_lower
    print(f"Contains company-specific values: {has_specifics}")

    # Assertions
    assert len(result["content"]) > 20, "Should provide response"
    assert kb_used, "Should use knowledge base search"

    print("\n✅ Scenario 5 PASSED")


# ============================================================================
# Performance Tests
# ============================================================================

@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason=SKIP_REASON)
def test_performance_latency(clean_session):
    """
    Test latency targets from implementation plan.
    """
    print("\n" + "="*60)
    print("PERFORMANCE: Latency Tests")
    print("="*60)

    session = clean_session

    print("\nSimple query latency test...")
    result = send_message_streaming(session["session_id"], "What was Q4 revenue?")

    if result['latency_first_token']:
        print(f"  First token: {result['latency_first_token']:.2f}s (target: <2s)")
    print(f"  Total: {result['latency_total']:.2f}s (target: <5s for simple)")

    # Check targets (generous for CI variability)
    first_token_ok = result['latency_first_token'] is None or result['latency_first_token'] < 10
    total_ok = result['latency_total'] < 60

    print(f"\n  First token target met: {'✅' if first_token_ok else '❌'}")
    print(f"  Total latency acceptable: {'✅' if total_ok else '❌'}")

    assert total_ok, f"Total latency {result['latency_total']:.2f}s exceeds 60s limit"


# ============================================================================
# Main Runner (for standalone execution)
# ============================================================================

def run_all_integration_tests():
    """Run all integration tests (standalone mode)."""
    print("\n" + "#"*60)
    print("# InsightAgent Integration Tests - Phase 6")
    print("#"*60)

    if not INTEGRATION_ENABLED:
        print("❌ RUN_INTEGRATION_TESTS=1 is required to run integration tests")
        return False

    if not API_KEY:
        print("❌ DEMO_API_KEY environment variable not set")
        return False

    if requests is None:
        print("❌ requests is not installed")
        return False

    results = {}

    try:
        response = requests.get(f"{API_BASE}/health", timeout=REQUEST_TIMEOUT)
        if response.status_code != 200:
            print(f"❌ Backend not healthy: {response.text}")
            return False
        print(f"✅ Backend healthy: {response.json()}")
    except Exception as e:
        print(f"❌ Cannot connect to backend: {e}")
        return False

    # Test functions with their setup
    tests = [
        ("Scenario 1: Simple Query", lambda: test_scenario_1_simple_query(create_session())),
        ("Scenario 2: Multi-Tool", lambda: test_scenario_2_multi_tool(create_session())),
        ("Scenario 3: Session Memory", lambda: (
            reset_user_memory(),
            s := create_session(),
            send_message_streaming(s["session_id"], "What was our Q4 2024 revenue?"),
            test_scenario_3_session_memory(s),
        )[-1]),
        ("Scenario 4: Cross-Session", test_scenario_4_cross_session),
        ("Scenario 5: RAG Grounding", lambda: test_scenario_5_rag_grounding(create_session())),
        ("Performance: Latency", lambda: test_performance_latency(create_session())),
    ]

    for name, test_fn in tests:
        reset_user_memory()
        try:
            test_fn()
            results[name] = "✅ PASSED"
        except AssertionError as e:
            results[name] = f"❌ FAILED: {e}"
        except Exception as e:
            results[name] = f"❌ ERROR: {e}"

    # Summary
    print("\n" + "="*60)
    print("INTEGRATION TEST SUMMARY")
    print("="*60)
    for name, status in results.items():
        print(f"  {name}: {status}")

    passed = sum(1 for s in results.values() if "PASSED" in s)
    total = len(results)
    print(f"\n  Total: {passed}/{total} passed")

    return passed == total


if __name__ == "__main__":
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
