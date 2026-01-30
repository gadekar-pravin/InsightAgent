# InsightAgent

**AI-Powered Business Intelligence Assistant using Google ADK**

InsightAgent enables business users to conduct investigative analytics through natural conversation—without writing SQL or navigating complex BI tools. It answers questions, provides context from company knowledge, and remembers what matters.

**Live Demo:** https://insightagent-app.web.app

---

## Features

| Capability | Description |
|------------|-------------|
| **RAG (Retrieval-Augmented Generation)** | Grounds answers in company knowledge—explains *why* a metric matters using internal docs |
| **Tool Use** | Orchestrates multiple tools intelligently—chains 3+ tool calls to answer complex questions |
| **Persistent Memory** | Remembers context across turns and sessions—references earlier analysis without being reminded |

### Sample Questions

- "What was our Q4 2024 revenue?"
- "Why did we miss our target?"
- "Is our churn rate healthy?"
- "How does West region compare to last quarter?"

---

## Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Firebase Hosting                  │
│              React SPA (Vite + Tailwind)            │
│         Chat UI with Reasoning Trace Display        │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS API calls (SSE for streaming)
                      ▼
┌─────────────────────────────────────────────────────┐
│                    Cloud Run                        │
│                 FastAPI Backend                     │
│  ┌─────────────────────────────────────────────┐    │
│  │            Google ADK Agent                 │    │
│  │                                             │    │
│  │  Tools:                                     │    │
│  │  • query_bigquery                           │    │
│  │  • search_knowledge_base                    │    │
│  │  • get_conversation_context                 │    │
│  │  • save_to_memory                           │    │
│  └─────────────────────────────────────────────┘    │
└───────┬──────────────┬─────────────────┬─────────── ┘
        │              │                 │
        ▼              ▼                 ▼
   ┌─────────┐   ┌──────────┐    ┌─────────────┐
   │BigQuery │   │ Vertex   │    │  Firestore  │
   │  (Data) │   │ AI RAG   │    │  (Memory)   │
   └─────────┘   └──────────┘    └─────────────┘
```

---

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, Vite, TailwindCSS, TypeScript |
| **Backend** | FastAPI, Python 3.11 |
| **Agent Framework** | Google ADK with Gemini 2.5 Flash |
| **Database** | BigQuery (sales data) |
| **Vector Store** | Vertex AI RAG Engine |
| **Memory Store** | Firestore |
| **Hosting** | Cloud Run (backend), Firebase Hosting (frontend) |

---

## Getting Started

### Prerequisites

- Python 3.11+
- Node.js 18+
- Google Cloud SDK (`gcloud`)
- GCP project with enabled APIs (Vertex AI, BigQuery, Firestore, Cloud Run)

### Local Development

#### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your GCP project settings

# Authenticate with GCP
gcloud auth application-default login

# Start the server
uvicorn app.main:app --reload --port 8080
```

#### Frontend

```bash
cd frontend
npm install

# Configure environment
echo "VITE_API_KEY=your-api-key" > .env

# Start development server
npm run dev
```

The frontend runs at http://localhost:5173 and proxies API requests to the backend.

### Data Setup

Before using the app, seed the demo data (run from repo root):

```bash
source backend/.venv/bin/activate

# Seed BigQuery tables
python scripts/seed_bigquery.py

# Setup Vertex AI RAG corpus with knowledge base
python scripts/setup_rag_corpus.py
```

---

## Deployment

### Using the Deploy Script

```bash
# Deploy both backend and frontend
./scripts/deploy.sh all

# Deploy individually
./scripts/deploy.sh backend    # Cloud Run
./scripts/deploy.sh frontend   # Firebase Hosting

# Before a demo (reduce cold starts)
./scripts/deploy.sh warmup

# After a demo (save costs)
./scripts/deploy.sh cooldown
```

### Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://insightagent-app.web.app |
| Backend API | https://insightagent-650676557784.asia-south1.run.app |
| API Docs | https://insightagent-650676557784.asia-south1.run.app/docs |

---

## Project Structure

```
InsightAgent/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Configuration (ADC, settings)
│   │   ├── agent/
│   │   │   ├── insight_agent.py # ADK agent with Gemini
│   │   │   └── prompts.py       # System prompts
│   │   ├── tools/               # Tool implementations
│   │   │   ├── bigquery_tool.py
│   │   │   ├── knowledge_tool.py
│   │   │   ├── context_tool.py
│   │   │   └── memory_tool.py
│   │   ├── services/            # Backend services
│   │   │   ├── bigquery_service.py
│   │   │   ├── rag_engine.py
│   │   │   └── firestore_service.py
│   │   └── api/
│   │       └── routes.py        # API endpoints
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app component
│   │   ├── components/          # UI components
│   │   ├── context/             # State management
│   │   └── services/            # API client
│   ├── package.json
│   └── vite.config.ts
├── knowledge_base/              # RAG documents
│   ├── metrics_definitions.md
│   ├── company_targets_2024.md
│   ├── regional_strategy.md
│   ├── pricing_policy.md
│   └── customer_segments.md
├── scripts/
│   ├── deploy.sh                # Deployment automation
│   ├── seed_bigquery.py         # Data seeding
│   └── setup_rag_corpus.py      # RAG setup
└── tests/
    ├── conftest.py
    ├── test_demo_data.py
    └── test_integration.py
```

---

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/chat/session` | POST | Create new chat session |
| `/api/chat/message` | POST | Send message (SSE streaming response) |
| `/api/chat/history/{session_id}` | GET | Retrieve conversation history |
| `/api/user/memory` | GET | Retrieve user's persistent memory |
| `/api/user/memory/reset` | DELETE | Reset user memory |

### SSE Event Types

| Event | Description |
|-------|-------------|
| `reasoning` | Tool call trace (started, completed) |
| `content` | Response text delta |
| `memory` | Memory save notification |
| `done` | Completion with suggested follow-ups |
| `error` | Error notification |

---

## Testing

Tests are located at the repo root in `tests/`. Run from repo root:

```bash
source backend/.venv/bin/activate

# Run all tests
pytest tests/

# Run integration tests (requires GCP credentials)
RUN_INTEGRATION_TESTS=1 pytest tests/test_integration.py -v
```

---

## Environment Variables

### Backend (`backend/.env`)

```
GCP_PROJECT_ID=your-project-id
VERTEX_LOCATION=asia-south1
BQ_DATASET_ID=insightagent_data
RAG_CORPUS_NAME=projects/.../ragCorpora/...
DEMO_API_KEY=your-api-key
ALLOWED_CORS_ORIGIN=https://your-frontend-url
```

### Frontend (`frontend/.env`)

```
VITE_API_KEY=your-api-key
VITE_API_BASE_URL=https://your-backend-url/api  # Production only
```

---

## Demo Flow

A 5-minute demo showcasing all capabilities:

| Step | Question | Capability Demonstrated |
|------|----------|------------------------|
| 1 | "What was our Q4 2024 revenue?" | Data querying + RAG grounding |
| 2 | "Why did we miss the target?" | Multi-tool orchestration (3+ tools) |
| 3 | "How does West compare to Q3?" | Within-session memory |
| 4 | "Is our churn rate healthy?" | RAG contextual grounding |
| 5 | *(New session)* "Continue where we left off" | Cross-session memory |

---

## License

This project was created as a capstone demonstration of Google ADK capabilities.
