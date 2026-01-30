# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

InsightAgent is an AI-powered business intelligence assistant demonstrating Google ADK capabilities: RAG (grounded answers from company knowledge), Tool Use (multi-tool orchestration), and Persistent Memory (cross-session context). Users ask business questions in natural language and receive data-driven answers with context.

## Development Commands

### Backend (FastAPI + Google ADK)
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8080   # Start dev server
```

### Tests (run from repo root)
```bash
source backend/.venv/bin/activate
pytest tests/                                # All tests
pytest tests/test_demo_data.py              # Data validation tests
RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v  # Integration tests (requires GCP)
```

### Frontend (React + Vite + Tailwind)
```bash
cd frontend
npm run dev      # Start dev server on port 5173
npm run build    # Production build
npm run lint     # ESLint
```

### Deployment
```bash
./scripts/deploy.sh all       # Deploy both backend and frontend
./scripts/deploy.sh backend   # Deploy backend to Cloud Run only
./scripts/deploy.sh frontend  # Deploy frontend to Firebase Hosting only
./scripts/deploy.sh warmup    # Set min-instances=1 before demo
./scripts/deploy.sh cooldown  # Set min-instances=0 after demo
```

### Data Setup (run from repo root)
```bash
source backend/.venv/bin/activate
python scripts/seed_bigquery.py       # Seed demo data to BigQuery
python scripts/setup_rag_corpus.py    # Setup Vertex AI RAG corpus with knowledge base
```

## Architecture

### Backend Structure (`backend/app/`)
- **main.py**: FastAPI entry point with CORS, logging middleware
- **config.py**: Settings via Pydantic (loads from `.env`), Vertex AI initialization
- **api/routes.py**: REST endpoints (`/api/chat/session`, `/api/chat/message` with SSE streaming)
- **agent/insight_agent.py**: Core agent using `google.genai.Client` with Gemini 2.5 Flash, implements agentic loop with tool calling
- **agent/prompts.py**: System prompt builder, injects user memory context
- **tools/**: Four tool implementations:
  - `bigquery_tool.py`: Execute read-only SQL against BigQuery sales data
  - `knowledge_tool.py`: Semantic search via Vertex AI RAG Engine
  - `context_tool.py`: Retrieve conversation context from Firestore
  - `memory_tool.py`: Persist findings/preferences to Firestore
- **services/**: Backend services:
  - `bigquery_service.py`: BigQuery client with safety limits
  - `rag_engine.py`: Vertex AI RAG retrieval
  - `firestore_service.py`: User memory and session persistence
  - `tool_middleware.py`: Tool execution wrapper

### Frontend Structure (`frontend/src/`)
- **App.tsx**: Main layout with Header, ChatArea, ReasoningPanel
- **context/ChatContext.tsx**: Chat state management, SSE message handling
- **services/api.ts**: Backend API client with SSE streaming
- **components/**: ChatMessage, ChatInput, ReasoningPanel (shows tool execution traces)

### Data Flow
1. User message -> FastAPI `/api/chat/message` (SSE stream)
2. Agent receives message, builds Gemini request with system prompt + tools
3. Agent enters agentic loop: tool calls -> execute -> feed results back to model
4. SSE events streamed to frontend: `reasoning` (tool traces), `content` (response text), `memory` (saved findings), `done`

### Key Files
- **knowledge_base/**: 5 markdown documents (metrics definitions, targets, regional strategy, pricing, customer segments) used for RAG
- **backend/.env.example**: Required environment variables template
- **frontend/.env.production**: API key and backend URL for production builds

## Environment Variables

Backend requires:
- `GCP_PROJECT_ID`: Google Cloud project
- `VERTEX_LOCATION`: Region for Vertex AI (default: us-central1)
- `RAG_CORPUS_NAME`: Vertex AI RAG corpus resource name
- `DEMO_API_KEY`: API key for frontend authentication
- `ALLOWED_CORS_ORIGIN`: Frontend URL for CORS

## Testing Notes

- Integration tests require `RUN_INTEGRATION_TESTS=1` and valid GCP credentials
- Tests use the `@pytest.mark.integration` marker for integration tests
- Demo data tests validate that seeded BigQuery data matches expected values for demo script
