# InsightAgent Implementation Plan
## AI-Powered Business Intelligence Agent using Google ADK

---

## Overview

This document outlines the implementation plan for InsightAgent, an AI-powered business intelligence assistant that demonstrates RAG, Tool Use, and Persistent Memory capabilities using Google ADK (Agent Development Kit).

**Target:** 5-minute demo showcasing all three core capabilities

---

## Quick Navigation

| Phase | Section | Key Contents |
|-------|---------|--------------|
| **Setup** | [Phase 1: Project Setup](#phase-1-project-setup--infrastructure) | Directory structure, GCP setup, dev environment |
| **Data** | [Phase 4: Data Setup](#phase-4-knowledge-base--data-setup) | Knowledge base docs, seed data, RAG corpus setup |
| **Backend** | [Phase 2: Backend Core](#phase-2-backend-core-implementation) | ADK agent, tools, services |
| | → [2.1 ADK Agent](#21-google-adk-agent-setup) | Runner events, streaming |
| | → [2.2 Tools](#22-tool-implementation) | BigQuery, RAG, Context, Memory |
| | → [2.3 Services](#23-services-layer) | BigQuery service, RAG engine, Firestore |
| **API** | [Phase 3: API Layer](#phase-3-api-layer-implementation) | FastAPI, endpoints, SSE streaming |
| **Frontend** | [Phase 5: Frontend](#phase-5-frontend-implementation) | React components, reasoning trace UI |
| **Testing** | [Phase 6: Testing](#phase-6-integration--testing) | Integration tests, golden tests, performance |
| **Deploy** | [Phase 7: Deployment](#phase-7-deployment) | Cloud Run, Firebase Hosting |
| **Reference** | [Implementation Order](#implementation-order--dependencies) | Dependency graph |
| | [Risk Mitigation](#risk-mitigation) | Risk table |
| | [Technical Decisions](#key-technical-decisions) | Architecture choices |
| | [Success Metrics](#success-metrics) | Demo targets |

---

## Phase 1: Project Setup & Infrastructure

### 1.1 Initialize Project Structure

```
InsightAgent/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration management
│   │   ├── agent/
│   │   │   ├── __init__.py
│   │   │   ├── insight_agent.py # ADK agent definition
│   │   │   └── prompts.py       # System prompts
│   │   ├── tools/
│   │   │   ├── __init__.py
│   │   │   ├── bigquery_tool.py
│   │   │   ├── knowledge_tool.py
│   │   │   ├── context_tool.py
│   │   │   └── memory_tool.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── bigquery_service.py
│   │   │   ├── rag_engine.py
│   │   │   ├── firestore_service.py
│   │   │   └── tool_middleware.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   └── schemas.py       # Pydantic models
│   │   └── api/
│   │       ├── __init__.py
│   │       └── routes.py        # API endpoints
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── services/
│   │   └── App.tsx
│   ├── package.json
│   └── vite.config.ts
├── knowledge_base/
│   ├── metrics_definitions.md
│   ├── company_targets_2024.md
│   ├── regional_strategy.md
│   ├── pricing_policy.md
│   └── customer_segments.md
├── data/
│   └── seed_data/
│       ├── transactions.csv
│       ├── customers.csv
│       └── targets.csv
├── scripts/
│   ├── seed_bigquery.py
│   └── setup_rag_corpus.py
└── tests/
    ├── __init__.py
    └── test_demo_data.py
```

### 1.2 GCP Project Setup

**Tasks:**
1. Create GCP project or use existing one
2. Enable required APIs:
   - Vertex AI API (includes RAG Engine)
   - BigQuery API
   - Firestore API
   - Cloud Run API
   - Firebase Hosting
3. Create service account with necessary permissions
4. Set up authentication credentials

### 1.3 Development Environment

**Tasks:**
1. Create Python virtual environment (Python 3.11+)
2. Install Google ADK: `pip install google-adk`
3. Install dependencies: FastAPI, uvicorn, google-cloud-bigquery, google-cloud-aiplatform, vertexai, firebase-admin
4. Set up environment variables configuration
5. Configure authentication handling for local vs Cloud Run:
   ```python
   # config.py - handles both local dev and Cloud Run
   import google.auth

   credentials, project = google.auth.default()
   # Local: uses gcloud auth application-default login
   # Cloud Run: uses service account automatically
   ```

---

## Phase 2: Backend Core Implementation

### 2.1 Google ADK Agent Setup

**File:** `backend/app/agent/insight_agent.py`

**Tasks:**
1. Initialize ADK Agent with Gemini 2.5 Flash model
2. Configure agent with system prompt from spec (Section 6)
3. Register all four tools with the agent
4. Implement streaming response handling via ADK Events
5. Configure agent memory settings
6. Set low temperature for demo consistency

**Key Implementation Details:**
```python
from google.adk import Agent
from google.adk.tools import Tool

# Agent initialization with Gemini 2.5 Flash
agent = Agent(
    model="gemini-2.5-flash",
    system_prompt=INSIGHT_AGENT_SYSTEM_PROMPT,
    tools=[
        query_bigquery_tool,
        search_knowledge_base_tool,
        get_conversation_context_tool,
        save_to_memory_tool
    ],
    temperature=0.2  # Low temperature for demo consistency
)
```

**ADK Events Bridge (using Runner):**
Use ADK's `Runner.run_async()` event loop (not model "thinking" text) as source of truth for reasoning trace:
```python
from google.adk import Runner

runner = Runner(agent=agent, app_name="insightagent", session_service=session_service)

# Stream events from Runner - this is ADK's actual streaming surface
async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
    # Tool start: when we see a function_call in event.content.parts
    if event.content and any(hasattr(p, 'function_call') for p in event.content.parts):
        for part in event.content.parts:
            if hasattr(part, 'function_call'):
                yield sse_event(seq, "reasoning", {
                    "trace_id": event.id,
                    "tool_name": part.function_call.name,
                    "status": "started"
                })
    # Tool end: when we see a function_response
    elif event.content and any(hasattr(p, 'function_response') for p in event.content.parts):
        for part in event.content.parts:
            if hasattr(part, 'function_response'):
                yield sse_event(seq, "reasoning", {
                    "trace_id": event.id,
                    "tool_name": part.function_response.name,
                    "status": "completed",
                    "summary": sanitize_output(part.function_response.response)
                })
    # Text deltas: check partial/turn_complete flags for UI state
    elif event.content and event.content.parts:
        for part in event.content.parts:
            if hasattr(part, 'text'):
                yield sse_event(seq, "content", {"delta": part.text})
```

### 2.2 Tool Implementation

#### Tool 1: `query_bigquery`

**File:** `backend/app/tools/bigquery_tool.py`

**Tasks:**
1. Create BigQuery client wrapper
2. Implement SQL validation (SELECT only)
3. Add query execution with timeout (30s)
4. Implement row limit (1000 rows max)
5. Format results as specified (success, data, row_count, columns, error)
6. Include few-shot SQL examples in tool description

**Constraints to implement:**
- Single-statement enforcement: reject queries containing `;` (prevents `SELECT 1; DROP TABLE`)
- Dry-run validation before execution:
  ```python
  job_config = bigquery.QueryJobConfig(dry_run=True, use_query_cache=False)
  dry_run_job = client.query(sql, job_config=job_config)

  # Verify statement type (server-side truth)
  if dry_run_job.statement_type != "SELECT":
      return {"success": False, "error": "Only SELECT queries allowed"}

  # Check cost estimate
  bytes_estimate = dry_run_job.total_bytes_processed
  if bytes_estimate > MAX_BYTES_ALLOWED:
      return {"success": False, "error": f"Query too expensive: {bytes_estimate} bytes"}
  ```
- Hard cost limit via `maximum_bytes_billed` on actual query
- Query timeout: 30 seconds
- Auto-inject `LIMIT 1000` if absent: wrap query as `SELECT * FROM (<original_sql>) LIMIT 1000`
- Return `total_bytes_processed` and `total_bytes_billed` in output

**Tool Chaining Guidance in Docstring:**
Include explicit guidance: *"Returns raw data. If the user asks 'why' or needs context to interpret results, follow up with `search_knowledge_base` to provide business context."*

#### Tool 2: `search_knowledge_base`

**File:** `backend/app/tools/knowledge_tool.py`

**Tasks:**
1. Set up Vertex AI RAG Engine corpus
2. Configure RAG corpus with appropriate chunking (512 tokens, 50-token overlap)
3. Import knowledge base documents into corpus
4. Implement semantic search using RAG Engine retrieval API
5. Configure relevance threshold (0.7 minimum)
6. Return results with content, source, and relevance_score

**Document processing:**
- Use Vertex AI RAG Engine's built-in document processing
- Configure chunking parameters at corpus creation
- Documents automatically embedded using Vertex AI embeddings

**Tool Chaining Guidance in Docstring:**
Include explicit guidance: *"Use this tool AFTER querying BigQuery when you need to explain the 'why' behind the numbers, or BEFORE querying to understand metric definitions."*

#### Tool 3: `get_conversation_context`

**File:** `backend/app/tools/context_tool.py`

**Tasks:**
1. Implement context retrieval from Firestore
2. Support three context types:
   - `current_session`: Topics, metrics queried, findings
   - `user_preferences`: Formats, regions, role, style
   - `past_analyses`: Session summaries with dates and topics
3. Return with last_updated timestamp

#### Tool 4: `save_to_memory`

**File:** `backend/app/tools/memory_tool.py`

**Tasks:**
1. Implement Firestore write operations
2. Support memory types: finding, preference, context
3. Validate key/value requirements
4. Return success confirmation with saved details

### 2.3 Services Layer

#### BigQuery Service

**File:** `backend/app/services/bigquery_service.py`

**Tasks:**
1. Initialize BigQuery client
2. Implement secure query execution
3. Add SQL injection prevention
4. Handle query results transformation
5. Implement error handling and user-friendly messages

#### RAG Engine Service

**File:** `backend/app/services/rag_engine.py`

**Tasks:**
1. Initialize Vertex AI RAG Engine client
2. Create/reference RAG corpus for knowledge base
3. Implement document import into corpus
4. Implement retrieval as custom tool (NOT ADK's built-in RAG tool - it has single-tool-per-agent limitation)
5. Handle relevance scoring and source attribution
6. Configure retrieval parameters (top_k, similarity threshold)

**Retrieval Implementation:**
```python
from vertexai import rag

def search_knowledge_base(query: str, top_k: int = 3) -> dict:
    response = rag.retrieval_query(
        rag_resources=[rag.RagResource(rag_corpus=CORPUS_NAME)],
        text=query,
        rag_retrieval_config=rag.RagRetrievalConfig(
            top_k=top_k,
            filter=rag.Filter(vector_distance_threshold=0.7)  # relevance threshold
        )
    )
    return format_results(response)
```

#### Firestore Service

**File:** `backend/app/services/firestore_service.py`

**Tasks:**
1. Initialize Firestore client
2. Implement user memory CRUD operations
3. Implement session management
4. Handle cross-session memory retrieval
5. Implement memory injection for returning users
6. Maintain a `summary` field that stores condensed context (not full history) for efficient system prompt injection

**Memory Document Structure:**
```
users/{user_id}/
├── summary: "Q4 analysis focused on West region underperformance..."  # For prompt injection
├── preferences: { regions_of_interest: ["West"], role: "Analyst" }
├── findings: { q4_revenue: "$12.4M, 4.6% below target", ... }
└── sessions/{session_id}/
    └── { date, topics, key_findings }
```

**Memory Compaction Rule:**
Keep injected context small and stable:
- Last N findings (e.g., 5 most recent)
- Top user preferences
- Last session summary only
- Total injected context < 500 tokens

**Session Creation with Memory Injection:**
`/chat/session` endpoint must:
1. Load user memory from Firestore
2. Apply compaction rule to create summary
3. Create session-scoped agent instance with injected memory
4. Store `injected_memory_snapshot` in session record (for auditability)

**Session TTL:**
Sessions persist for 24 hours of inactivity. Cleanup options:
- Use Firestore TTL policies (set `expireAt` field on session documents)
- Or scheduled Cloud Function to delete stale sessions

#### Tool Output Middleware

**File:** `backend/app/services/tool_middleware.py`

**Tasks:**
1. Sanitize tool outputs before sending to UI:
   - Redact any secrets or sensitive patterns
   - Truncate long SQL results (keep first N rows for display)
   - Truncate KB content chunks if excessively long
2. Attach `source` citations for KB chunks
3. Log tool calls for debugging (with sanitization)

---

## Phase 3: API Layer Implementation

### 3.1 FastAPI Application

**File:** `backend/app/main.py`

**Tasks:**
1. Initialize FastAPI application
2. Configure CORS for frontend
3. Set up SSE (Server-Sent Events) support
4. Configure middleware (logging, error handling)
5. Include API routes

### 3.2 API Endpoints

**File:** `backend/app/api/routes.py`

**Endpoints to implement:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/chat/session` | POST | Create new chat session |
| `/chat/message` | POST | Send message, receive streaming response |
| `/chat/history/{session_id}` | GET | Retrieve conversation history |
| `/user/memory` | GET | Retrieve user's persistent memory |
| `/user/memory/reset` | DELETE | Reset user memory (demo feature) |

### 3.3 Streaming Response Implementation

**Tasks:**
1. Implement SSE event types with monotonic sequence IDs (for Last-Event-ID resume):
   ```
   id: 1
   event: reasoning
   data: {"seq": 1, "trace_id": "abc123", "tool": "query_bigquery", "status": "started"}

   id: 2
   event: reasoning
   data: {"seq": 2, "trace_id": "abc123", "tool": "query_bigquery", "status": "completed", "rows": 4}

   id: 3
   event: content
   data: {"seq": 3, "delta": "**Q4 Revenue: $12.4M**"}

   id: 4
   event: memory
   data: {"seq": 4, "key": "q4_revenue", "value": "..."}

   id: 5
   event: done
   data: {"seq": 5, "suggested_followups": [...]}
   ```
   Note: `id` is monotonic integer for SSE resume; `trace_id` in payload correlates tool start/end; `seq` duplicated in payload for debugging reconnect gaps.
2. Handle streaming from ADK agent via events bridge
3. Frontend maintains `currentToolCall` state for UI rendering

**SSE Reliability:**
- Include monotonically increasing `seq` number for reconnect robustness
- Send periodic heartbeat events (every 15s) to prevent proxy timeouts
- Flush after each event to ensure immediate delivery
- Add tool output sanitization middleware (redact secrets, truncate long outputs)

### 3.4 Request/Response Models

**File:** `backend/app/models/schemas.py`

**Models to create:**
- `SessionCreate` / `SessionResponse`
- `MessageRequest` / `MessageResponse`
- `ReasoningEvent`
- `ContentEvent`
- `MemoryEvent`
- `UserMemory`

---

## Phase 4: Knowledge Base & Data Setup

### 4.1 Create Knowledge Base Documents

**Location:** `knowledge_base/`

**Documents to create:**

| Document | Key Content |
|----------|-------------|
| `metrics_definitions.md` | Churn (90-day window), target 3.5%, benchmark 5.1%; LTV, CAC, MRR definitions |
| `company_targets_2024.md` | Q4 targets: North $3.5M, South $3.0M, East $3.0M, West $3.5M; underperformance threshold (>10%) |
| `regional_strategy.md` | CompetitorX Q4 promotions in West; regional market conditions |
| `pricing_policy.md` | Nov 1 price increase (12%); West legacy pricing impact |
| `customer_segments.md` | Enterprise/SMB/Consumer definitions; LTV benchmarks |

### 4.2 Create Demo Seed Data

**Location:** `data/seed_data/`

**Data requirements per spec (Section 11):**

| Metric | Value |
|--------|-------|
| Q4 2024 total revenue | $12.4M |
| Q4 2024 target | $13.0M |
| West region variance | -25.7% vs target |
| Q4 2023 revenue | ~$9.6M |
| Churn rate | 4.2% |
| West Q3→Q4 transaction drop | ~28% |

**Tables to create:**
1. `transactions`: revenue, quantities, dates, regions, products
2. `customers`: segments, acquisition dates, lifetime value
3. `targets`: region, quarter, year, target_amount

### 4.3 Data Loading Scripts

**Script 1:** `scripts/seed_bigquery.py`
- Create BigQuery dataset
- Create tables with appropriate schemas
- Load seed data from CSV files

**Script 2:** `scripts/setup_rag_corpus.py`
- Create Vertex AI RAG Engine corpus
- Configure chunking parameters (512 tokens, 50-token overlap)
- Import knowledge base markdown documents
- Verify corpus is ready for queries

**Vertex AI RAG Engine Setup:**
```python
from vertexai import rag
import vertexai

vertexai.init(project=PROJECT_ID, location=VERTEX_LOCATION)

# Create corpus
corpus = rag.create_corpus(
    display_name="insightagent-knowledge-base",
    description="Company knowledge base for InsightAgent"
)

# Import documents with chunking config (512 tokens, 50 overlap per spec)
rag.import_files(
    corpus_name=corpus.name,
    paths=["gs://bucket/knowledge_base/"],
    transformation_config=rag.TransformationConfig(
        chunking_config=rag.ChunkingConfig(
            chunk_size=512,
            chunk_overlap=50
        )
    )
)
```

**IMPORTANT:** Do NOT use ADK's built-in `vertex_ai_rag_retrieval` tool. It has a "single tool per agent" limitation. Since InsightAgent requires 4 tools, implement RAG as a custom tool wrapper around `rag.retrieval_query()`.

---

## Phase 5: Frontend Implementation

### 5.1 React App Setup

**Tasks:**
1. Initialize Vite + React + TypeScript project
2. Install dependencies: Tailwind CSS, SSE client library
3. Configure environment variables
4. Set up project structure

### 5.2 Core Components

| Component | Purpose |
|-----------|---------|
| `ChatContainer` | Scrollable message history container |
| `MessageBubble` | User/agent message display with markdown rendering |
| `ReasoningPanel` | Expandable tool call trace display |
| `InputArea` | Text input with send button |
| `SuggestedActions` | Clickable follow-up chips |
| `TableRenderer` | Formatted data tables with indicators |
| `MemoryIndicator` | 💾 save notifications |

### 5.3 Key Features

**Reasoning Trace Display:**
```
┌─────────────────────────────────────────┐
│ 🔍 Searching knowledge base...          │
│ ✓ Found: metrics_definitions.md         │
│ 📊 Querying BigQuery...                 │
│ ✓ Retrieved 4 rows                      │
│ 💭 Synthesizing response...             │
└─────────────────────────────────────────┘
```

**Tasks:**
1. Implement SSE connection handling
2. Parse and display reasoning events in real-time
3. Collapse reasoning after response completes
4. Allow expand/collapse toggle

### 5.4 Response Rendering

**Tasks:**
1. Markdown rendering with table support
2. Trend indicators: ✅ (positive), ⚠️ (warning), 🔴 (negative)
3. Memory save indicator (💾)
4. Clickable follow-up suggestions
5. Source document citations

### 5.5 Streaming Handling

**Tasks:**
1. Implement EventSource connection
2. Handle reconnection on drops
3. Show typing indicator during generation
4. Buffer and render content deltas smoothly

---

## Phase 6: Integration & Testing

### 6.1 Integration Testing

**Test Scenarios (from Demo Script):**

1. **Simple Query + RAG Grounding (Scene 1)**
   - Input: "What was our Q4 revenue?"
   - Verify: Data query + knowledge base context + memory save

2. **Multi-Tool Orchestration (Scene 2)**
   - Input: "Why did we miss the target?"
   - Verify: 3+ tool chains, data + context synthesis

3. **Memory Within Session (Scene 3)**
   - Input: "How does West compare to last quarter?"
   - Verify: Contextual understanding from earlier conversation

4. **Cross-Session Memory (Scene 4)**
   - Input: "Continue where we left off" (new session)
   - Verify: Past session recall

5. **RAG Contextual Grounding (Scene 5)**
   - Input: "Is our churn rate healthy?"
   - Verify: Company-specific definition retrieval

### 6.2 Golden Tests for Demo Data

**Purpose:** Validate seed data produces exact demo narrative values. Catches drift if someone edits CSVs.

| Assertion | Expected Value |
|-----------|----------------|
| Q4 2024 total revenue | $12.4M |
| Q4 2024 target | $13.0M |
| West region variance vs target | -25.7% |
| Q4 2023 revenue (YoY baseline) | ~$9.6M |
| Current churn rate | 4.2% |
| West Q3→Q4 transaction drop | ~28% |
| West Q3→Q4 avg deal size change | +6.9% |

**Implementation:** Add `tests/test_demo_data.py` that queries BigQuery and asserts these values.

### 6.3 Performance Testing

**Targets:**
| Metric | Target |
|--------|--------|
| Time to first token | < 2 seconds |
| Simple query end-to-end | < 5 seconds |
| Complex multi-tool query | < 15 seconds |
| Knowledge base search | < 2 seconds |
| BigQuery execution | < 10 seconds |

### 6.4 Demo Verification Checklist

**RAG:**
- [ ] Agent retrieves company-specific metric definition
- [ ] Agent cites source document by name
- [ ] Agent uses internal benchmark (not generic)

**Tool Use:**
- [ ] Agent chains 3+ tools for one question
- [ ] Agent shows reasoning for tool selection
- [ ] Visible reasoning trace shows tool progression

**Memory:**
- [ ] Agent remembers topic from earlier in conversation
- [ ] Agent saves specific finding with 💾 indicator
- [ ] Cross-session: Agent recalls past session on return

---

## Phase 7: Deployment

### 7.1 Backend Deployment (Cloud Run)

**Tasks:**
1. Create Dockerfile for FastAPI app
2. Build and push container image
3. Deploy to Cloud Run with:
   - Min instances: 0 (production) or 1 (demo profile for TTFT < 2s)
   - Max instances: 5
   - Memory: 2GB
   - CPU: 2

**Demo Deployment Profile:**
Use `--min-instances=1` during demos to avoid cold start latency. Production can use 0 for cost savings.

**Pre-Demo Warm-up:**
Before presenting, run a simple warm-up script or endpoint that executes:
- 1 BigQuery query (warms connection pool)
- 1 RAG retrieval (warms embedding model)
This ensures first demo question has optimal latency.
4. Configure environment variables
5. Set up service account permissions

### 7.2 Frontend Deployment (Firebase Hosting)

**Tasks:**
1. Build production React app
2. Configure Firebase project
3. Deploy to Firebase Hosting
4. Set up custom domain (optional)

### 7.3 Environment Configuration

**Required Environment Variables:**
```
# GCP
GCP_PROJECT_ID=
VERTEX_LOCATION=us-central1  # Configurable, not hardcoded

# BigQuery
BQ_DATASET_ID=
# Note: No BQ_CREDENTIALS needed on Cloud Run - uses ADC via service account
# For local dev without gcloud auth: optionally set GOOGLE_APPLICATION_CREDENTIALS

# Firestore
FIRESTORE_COLLECTION_PREFIX=

# Vertex AI / ADK
GEMINI_MODEL=gemini-2.5-flash

# RAG Engine
RAG_CORPUS_NAME=

# API
API_BASE_URL=
```

---

## Implementation Order & Dependencies

**Key insight:** Data setup must come before backend tool development. You cannot effectively build or test `query_bigquery` or `search_knowledge_base` until the data exists. This allows testing tool logic immediately as you write it.

```
Phase 1: Setup (Foundation)
    │
    ├── 1.1 Project Structure
    ├── 1.2 GCP Setup
    └── 1.3 Dev Environment
          │
          ▼
Phase 4: Data Setup (MOVED UP - tools need data to test against)
    │
    ├── 4.1 Knowledge Base Documents
    ├── 4.2 Seed Data (CSVs)
    └── 4.3 Load BigQuery + RAG Corpus
          │
          ▼
Phase 2: Backend Core (now testable against real data)
    │
    ├── 2.1 ADK Agent Setup ─────────────┐
    ├── 2.2 Tool Implementation          │
    │   ├── BigQuery Tool (test immediately) │
    │   ├── Knowledge Tool (test immediately)│
    │   ├── Context Tool                 │
    │   └── Memory Tool                  │
    └── 2.3 Services Layer ──────────────┘
          │
          ▼
Phase 3: API Layer
    │
    ├── 3.1 FastAPI Setup
    ├── 3.2 Endpoints
    ├── 3.3 Streaming
    └── 3.4 Models
          │
          ▼
Phase 5: Frontend
    │
    ├── 5.1 React Setup
    ├── 5.2 Components
    ├── 5.3 Reasoning Display
    ├── 5.4 Response Rendering
    └── 5.5 Streaming
          │
          ▼
Phase 6: Testing
    │
    ├── 6.1 Integration Tests
    ├── 6.2 Performance Tests
    └── 6.3 Demo Verification
          │
          ▼
Phase 7: Deployment
    │
    ├── 7.1 Cloud Run
    └── 7.2 Firebase Hosting
```

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| ADK streaming complexity | High | Start with non-streaming, add streaming later |
| BigQuery query latency | Medium | Pre-warm queries, optimize SQL examples |
| RAG Engine latency | Low | Managed service handles scaling; configure appropriate timeout |
| Cross-session memory injection | High | Test early, ensure system prompt injection works |
| Tool chaining reliability | High | Extensive prompt engineering, few-shot examples |

---

## Key Technical Decisions

1. **Vector Store**: Use Vertex AI RAG Engine for native GCP integration, managed infrastructure, and seamless compatibility with Gemini models

2. **Memory Architecture**: Use Firestore with structured collections per user; store a **summary** field (not full history) and inject into system prompt on session start:
   ```python
   past_context = get_user_memory_summary(user_id)
   if past_context:
       system_prompt += f"\n\n## PAST CONTEXT\n{past_context}"
   ```

3. **Streaming**: Implement SSE from backend with distinct event types; frontend parses and routes to appropriate UI components

4. **Tool Definitions**: Provide detailed descriptions and few-shot examples to guide agent tool selection

5. **Error Handling**: User-friendly messages only; no stack traces; graceful degradation when tools fail

---

## Success Metrics

| Metric | Target | Verification |
|--------|--------|--------------|
| Demo Duration | 5 minutes | Time the scripted flow |
| Tool Chaining | 3+ tools per complex question | Count tool calls in reasoning trace |
| RAG Grounding | Every answer includes KB context | Verify source citations |
| Memory Recall | Cross-session works | Test Scene 4 flow |
| Latency | First token < 2s | Performance monitoring |

---

*Document Version: 1.0*
*Created: 2026-01-29*
