# InsightAgent: Architecture & Deployment Guide

This document provides a detailed technical overview of InsightAgent's architecture, GCP service selections, and deployment patterns. InsightAgent is an AI-powered business intelligence assistant demonstrating Google ADK capabilities: RAG (grounded answers), Tool Use (multi-tool orchestration), and Persistent Memory (cross-session context).

**Production URL:** https://insightagent-app.web.app

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [GCP Services Selection](#3-gcp-services-selection)
4. [Component Architecture](#4-component-architecture)
5. [Data Flow & Sequence Diagrams](#5-data-flow--sequence-diagrams)
6. [Deployment Architecture](#6-deployment-architecture)
7. [Security Architecture](#7-security-architecture)
8. [Scalability & Performance](#8-scalability--performance)

---

## 1. System Overview

InsightAgent enables business users to conduct investigative analytics through natural conversation. The system combines:

| Capability | Implementation | GCP Service |
|------------|----------------|-------------|
| **RAG** | Semantic search over company knowledge base | Vertex AI RAG Engine |
| **Data Querying** | Natural language to SQL translation | BigQuery |
| **Persistent Memory** | Cross-session user context | Firestore |
| **LLM Orchestration** | Agent with function calling | Gemini 2.5 Flash |
| **Hosting** | Serverless compute + CDN | Cloud Run + Firebase Hosting |

---

## 2. High-Level Architecture

```mermaid
flowchart TB
    subgraph "Client Layer"
        UI[React SPA<br/>Firebase Hosting]
    end

    subgraph "API Layer"
        CR[Cloud Run<br/>FastAPI Backend]
    end

    subgraph "Agent Layer"
        AGENT[Google ADK Agent<br/>Gemini 2.5 Flash]
    end

    subgraph "Data Services"
        BQ[(BigQuery<br/>Sales Data)]
        RAG[(Vertex AI RAG<br/>Knowledge Base)]
        FS[(Firestore<br/>Memory Store)]
    end

    UI -->|HTTPS/SSE| CR
    CR --> AGENT
    AGENT -->|query_bigquery| BQ
    AGENT -->|search_knowledge_base| RAG
    AGENT -->|get_context / save_memory| FS

    style UI fill:#4285F4,color:#fff
    style CR fill:#4285F4,color:#fff
    style AGENT fill:#EA4335,color:#fff
    style BQ fill:#34A853,color:#fff
    style RAG fill:#FBBC04,color:#000
    style FS fill:#FF6D01,color:#fff
```

### Architecture Principles

1. **Serverless-First**: No infrastructure management; auto-scaling based on demand
2. **Event-Driven Streaming**: SSE for real-time response streaming
3. **Managed AI Services**: Vertex AI for embeddings, RAG, and LLM inference
4. **Separation of Concerns**: Clear boundaries between UI, API, Agent, and Data layers

---

## 3. GCP Services Selection

### 3.1 Compute & Hosting

```mermaid
flowchart LR
    subgraph "Frontend Hosting Options"
        A[Cloud Storage + CDN]
        B[Firebase Hosting]
        C[App Engine]
    end

    subgraph "Backend Hosting Options"
        D[Cloud Functions]
        E[Cloud Run]
        F[GKE]
    end

    B -->|Selected| FRONTEND[Static SPA<br/>Global CDN<br/>Zero Cold Starts]
    E -->|Selected| BACKEND[Container Flexibility<br/>SSE Support<br/>Concurrency Control]

    style B fill:#34A853,color:#fff
    style E fill:#34A853,color:#fff
    style FRONTEND fill:#E8F5E9
    style BACKEND fill:#E8F5E9
```

| Service | Selection | Rationale |
|---------|-----------|-----------|
| **Firebase Hosting** | Frontend | Global CDN, automatic SSL, zero configuration deploys, instant rollback |
| **Cloud Run** | Backend | Container-native (Dockerfile), native SSE support, configurable concurrency, min-instances for warm-up |

**Why Cloud Run over Cloud Functions:**
- SSE streaming requires long-lived HTTP connections (functions timeout at 60s)
- Container flexibility allows custom Python dependencies
- Better control over instance scaling (min-instances for demos)

### 3.2 AI/ML Services

```mermaid
flowchart TB
    subgraph "Vertex AI Platform"
        GEMINI[Gemini 2.5 Flash<br/>LLM Inference]
        RAG_ENGINE[RAG Engine<br/>Vector Store + Retrieval]
        EMBED[Text Embeddings<br/>text-embedding-004]
    end

    subgraph "Alternative Options"
        OPENAI[OpenAI API]
        MATCHING[Vertex Matching Engine]
        PINECONE[Pinecone]
    end

    GEMINI -->|Selected| WHY_GEMINI[Function Calling<br/>Streaming<br/>Native GCP Integration]
    RAG_ENGINE -->|Selected| WHY_RAG[Managed Corpus<br/>Built-in Chunking<br/>No Infra Management]

    style GEMINI fill:#EA4335,color:#fff
    style RAG_ENGINE fill:#FBBC04,color:#000
    style WHY_GEMINI fill:#FFEBEE
    style WHY_RAG fill:#FFF8E1
```

| Service | Selection | Rationale |
|---------|-----------|-----------|
| **Gemini 2.5 Flash** | LLM | Fast inference, native function calling, streaming support, cost-effective |
| **Vertex AI RAG Engine** | Vector Store | Fully managed, automatic chunking, handles embeddings, no separate vector DB |

**Why Vertex AI RAG Engine over custom vector store:**
- Zero infrastructure: No need to manage Pinecone, Weaviate, or Matching Engine
- Automatic document chunking and embedding generation
- Built-in relevance scoring with configurable thresholds
- Native integration with Gemini models

### 3.3 Data Services

```mermaid
flowchart LR
    subgraph "Analytical Data"
        BQ[(BigQuery)]
        CLOUDSQL[(Cloud SQL)]
        SPANNER[(Cloud Spanner)]
    end

    subgraph "Operational Data"
        FS[(Firestore)]
        DATASTORE[(Datastore)]
        BIGTABLE[(Bigtable)]
    end

    BQ -->|Selected| WHY_BQ[Serverless<br/>Petabyte Scale<br/>Standard SQL<br/>Dry-Run Validation]
    FS -->|Selected| WHY_FS[Real-time Sync<br/>Hierarchical Data<br/>Strong Consistency<br/>Serverless]

    style BQ fill:#34A853,color:#fff
    style FS fill:#FF6D01,color:#fff
    style WHY_BQ fill:#E8F5E9
    style WHY_FS fill:#FFF3E0
```

| Service | Selection | Use Case | Rationale |
|---------|-----------|----------|-----------|
| **BigQuery** | Analytical queries | Sales transactions, targets | Serverless, cost-effective (pay-per-query), dry-run validation for safety |
| **Firestore** | User memory & sessions | Conversation history, user preferences | Real-time listeners, hierarchical documents, strong consistency |

**Why Firestore over Datastore:**
- Native document model fits user memory structure (nested findings, preferences)
- Real-time listeners (future: live memory updates)
- Better local development experience with emulator

---

## 4. Component Architecture

### 4.1 Backend Component Diagram

```mermaid
flowchart TB
    subgraph "FastAPI Application"
        MAIN[main.py<br/>Entry Point]
        ROUTES[routes.py<br/>API Endpoints]
        AUTH[auth.py<br/>API Key Validation]

        subgraph "Agent Module"
            AGENT[InsightAgent<br/>Agentic Loop]
            PROMPTS[prompts.py<br/>System Prompt Builder]
        end

        subgraph "Tools Module"
            T1[bigquery_tool]
            T2[knowledge_tool]
            T3[context_tool]
            T4[memory_tool]
        end

        subgraph "Services Module"
            S1[bigquery_service<br/>Query Execution]
            S2[rag_engine<br/>Vector Retrieval]
            S3[firestore_service<br/>Memory CRUD]
        end
    end

    MAIN --> ROUTES
    ROUTES --> AUTH
    ROUTES --> AGENT
    AGENT --> PROMPTS
    AGENT --> T1 & T2 & T3 & T4
    T1 --> S1
    T2 --> S2
    T3 & T4 --> S3

    S1 -->|BigQuery API| BQ[(BigQuery)]
    S2 -->|Vertex AI API| RAG[(RAG Engine)]
    S3 -->|Firestore API| FS[(Firestore)]
```

### 4.2 Agent Architecture

```mermaid
flowchart TB
    subgraph "InsightAgent"
        INIT[Initialize<br/>Load User Memory]
        BUILD[Build Request<br/>System Prompt + History]
        CALL[Call Gemini<br/>generate_content]

        subgraph "Agentic Loop (max 10 iterations)"
            CHECK{Response has<br/>tool calls?}
            EXEC[Execute Tools]
            FEED[Feed Results<br/>Back to Model]
        end

        STREAM[Stream Events<br/>reasoning, content, memory]
    end

    INIT --> BUILD --> CALL --> CHECK
    CHECK -->|Yes| EXEC --> FEED --> CALL
    CHECK -->|No| STREAM

    style CHECK fill:#FBBC04,color:#000
    style EXEC fill:#34A853,color:#fff
```

### 4.3 Frontend Component Diagram

```mermaid
flowchart TB
    subgraph "React Application"
        APP[App.tsx<br/>Layout Container]

        subgraph "Context Layer"
            CTX[ChatContext<br/>State Management]
        end

        subgraph "Components"
            HEADER[Header]
            WELCOME[WelcomeScreen]
            CHAT[ChatArea]
            MSG[MessageBubble]
            INPUT[ChatInput]
            REASON[ReasoningPanel]
            FOLLOWUP[SuggestedFollowups]
        end

        subgraph "Services"
            API[api.ts<br/>SSE Client]
        end
    end

    APP --> CTX
    CTX --> HEADER & WELCOME & CHAT & REASON
    CHAT --> MSG & INPUT & FOLLOWUP
    CTX --> API
    API -->|fetch + ReadableStream| BACKEND[Cloud Run Backend]
```

---

## 5. Data Flow & Sequence Diagrams

### 5.1 Chat Message Flow (SSE Streaming)

```mermaid
sequenceDiagram
    participant User
    participant Frontend as React SPA
    participant Backend as Cloud Run
    participant Agent as InsightAgent
    participant Gemini as Gemini 2.5 Flash
    participant Tools as Tool Services

    User->>Frontend: Send message
    Frontend->>Backend: POST /api/chat/message
    Backend->>Agent: chat(message)

    Agent->>Agent: Load user memory context
    Agent->>Gemini: generate_content(prompt + tools)

    loop Agentic Loop
        Gemini-->>Agent: Response with tool_calls
        Agent-->>Backend: SSE: reasoning (tool started)
        Agent->>Tools: Execute tool
        Tools-->>Agent: Tool result
        Agent-->>Backend: SSE: reasoning (tool completed)
        Agent->>Gemini: Feed tool results
    end

    Gemini-->>Agent: Final text response
    Agent-->>Backend: SSE: content (text delta)
    Agent->>Tools: save_to_memory (if findings)
    Agent-->>Backend: SSE: memory (saved)
    Agent-->>Backend: SSE: done (with followups)

    Backend-->>Frontend: Close SSE stream
    Frontend-->>User: Display response
```

### 5.2 RAG Retrieval Flow

```mermaid
sequenceDiagram
    participant Agent as InsightAgent
    participant Tool as knowledge_tool
    participant Service as rag_engine
    participant Vertex as Vertex AI RAG Engine
    participant Corpus as RAG Corpus

    Agent->>Tool: search_knowledge_base(query)
    Tool->>Service: search(query, top_k=5)
    Service->>Vertex: retrieval_query(corpus, query)

    Note over Vertex,Corpus: 1. Generate query embedding<br/>2. Vector similarity search<br/>3. Return top-k chunks

    Vertex->>Corpus: Vector search
    Corpus-->>Vertex: Matching chunks + scores
    Vertex-->>Service: RetrievalResponse

    Service->>Service: Filter by relevance threshold (0.3)
    Service->>Service: Format results with metadata
    Service-->>Tool: List[RetrievalResult]
    Tool-->>Agent: Formatted knowledge context
```

### 5.3 BigQuery Tool Flow

```mermaid
sequenceDiagram
    participant Agent as InsightAgent
    participant Tool as bigquery_tool
    participant Service as bigquery_service
    participant BQ as BigQuery API

    Agent->>Tool: query_bigquery(sql)
    Tool->>Service: execute_query(sql)

    Service->>Service: Validate SQL (prohibited keywords)

    alt Invalid SQL
        Service-->>Tool: Error: Prohibited operation
        Tool-->>Agent: Tool error result
    end

    Service->>BQ: Dry-run query (validate + estimate cost)

    alt Dry-run fails or exceeds cost limit
        BQ-->>Service: Error or bytes > limit
        Service-->>Tool: Error: Invalid query or too expensive
    end

    Service->>BQ: Execute query (with timeout)
    BQ-->>Service: QueryResults

    Service->>Service: Format results (row limit: 100)
    Service-->>Tool: Formatted data
    Tool-->>Agent: Query results
```

### 5.4 Memory Persistence Flow

```mermaid
sequenceDiagram
    participant Agent as InsightAgent
    participant MemTool as memory_tool
    participant CtxTool as context_tool
    participant Service as firestore_service
    participant FS as Firestore

    Note over Agent: Session Start
    Agent->>CtxTool: get_conversation_context()
    CtxTool->>Service: get_user_memory(user_id)
    Service->>FS: Get document
    FS-->>Service: User memory document
    Service-->>CtxTool: Memory data
    CtxTool-->>Agent: Context string

    Note over Agent: During Conversation
    Agent->>MemTool: save_to_memory(type, content)
    MemTool->>Service: save_memory_item(user_id, type, content)

    Service->>FS: Transaction: Read current
    FS-->>Service: Current document
    Service->>Service: Merge new item
    Service->>FS: Transaction: Write merged
    FS-->>Service: Success

    Service-->>MemTool: Saved item
    MemTool-->>Agent: Confirmation
```

---

## 6. Deployment Architecture

### 6.1 Deployment Pipeline

```mermaid
flowchart TB
    subgraph "Source"
        CODE[GitHub Repository]
    end

    subgraph "Build Phase"
        BUILD_BE[Cloud Build<br/>Docker Image]
        BUILD_FE[npm run build<br/>Vite Production]
    end

    subgraph "Artifact Storage"
        AR[Artifact Registry<br/>Docker Images]
        DIST[Local dist/<br/>Static Files]
    end

    subgraph "Deploy Phase"
        DEPLOY_BE[gcloud run deploy]
        DEPLOY_FE[firebase deploy]
    end

    subgraph "Production"
        CR[Cloud Run<br/>asia-south1]
        FH[Firebase Hosting<br/>Global CDN]
    end

    CODE --> BUILD_BE --> AR --> DEPLOY_BE --> CR
    CODE --> BUILD_FE --> DIST --> DEPLOY_FE --> FH

    style AR fill:#4285F4,color:#fff
    style CR fill:#4285F4,color:#fff
    style FH fill:#FF6D01,color:#fff
```

### 6.2 Infrastructure Diagram

```mermaid
flowchart TB
    subgraph "Internet"
        USERS[Users<br/>Worldwide]
    end

    subgraph "Firebase"
        CDN[Firebase Hosting<br/>Global CDN]
    end

    subgraph "Google Cloud - asia-south1"
        subgraph "Compute"
            CR[Cloud Run<br/>insightagent]
        end

        subgraph "AI Platform"
            VERTEX[Vertex AI<br/>Gemini API]
            RAG[RAG Engine<br/>Corpus]
        end

        subgraph "Data"
            BQ[(BigQuery<br/>insightagent_data)]
            FS[(Firestore<br/>User Memory)]
        end

        subgraph "IAM"
            SA[Service Account<br/>insightagent-sa]
        end
    end

    USERS -->|HTTPS| CDN
    CDN -->|Static Files| USERS
    CDN -->|/api/* proxy| CR

    CR --> VERTEX
    CR --> RAG
    CR --> BQ
    CR --> FS

    SA -.->|Identity| CR
    SA -.->|Permissions| VERTEX & RAG & BQ & FS

    style CDN fill:#FF6D01,color:#fff
    style CR fill:#4285F4,color:#fff
    style VERTEX fill:#EA4335,color:#fff
    style RAG fill:#FBBC04,color:#000
    style BQ fill:#34A853,color:#fff
    style FS fill:#FF6D01,color:#fff
```

### 6.3 Deployment Commands

```bash
# Full deployment
./scripts/deploy.sh all

# Individual deployments
./scripts/deploy.sh backend   # Cloud Run
./scripts/deploy.sh frontend  # Firebase Hosting

# Demo warm-up (reduce cold starts)
./scripts/deploy.sh warmup    # min-instances=1
./scripts/deploy.sh cooldown  # min-instances=0
```

### 6.4 Cloud Run Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| **Region** | asia-south1 | Proximity to users, Vertex AI availability |
| **Memory** | 2GB | Buffer for Gemini client, concurrent requests |
| **CPU** | 2 | Handle multiple tool executions |
| **Min Instances** | 0 (default) / 1 (demo) | Cost optimization vs latency |
| **Max Instances** | 5 | Prevent runaway scaling |
| **Timeout** | 300s | Long-running agentic loops |
| **Concurrency** | 80 | Handle multiple SSE streams |

---

## 7. Security Architecture

### 7.1 Authentication & Authorization Flow

```mermaid
flowchart TB
    subgraph "Client"
        FE[Frontend]
    end

    subgraph "API Layer"
        AUTH[API Key Auth<br/>X-API-Key Header]
        ROUTES[Protected Routes]
    end

    subgraph "GCP IAM"
        SA[Service Account]
        ROLES[IAM Roles]
    end

    subgraph "Resources"
        BQ[(BigQuery)]
        FS[(Firestore)]
        VA[(Vertex AI)]
    end

    FE -->|API Key| AUTH
    AUTH -->|Valid| ROUTES
    AUTH -->|Invalid| REJECT[401 Unauthorized]

    ROUTES -->|ADC| SA
    SA -->|IAM Binding| ROLES
    ROLES -->|bigquery.dataViewer| BQ
    ROLES -->|datastore.user| FS
    ROLES -->|aiplatform.user| VA

    style AUTH fill:#EA4335,color:#fff
    style SA fill:#4285F4,color:#fff
```

### 7.2 Security Controls

```mermaid
flowchart LR
    subgraph "Input Validation"
        SQL[SQL Injection<br/>Prevention]
        XSS[XSS Prevention<br/>Input Sanitization]
        PATH[Path Traversal<br/>User ID Validation]
    end

    subgraph "Query Safety"
        DRYRUN[BigQuery Dry-Run<br/>Validate Before Execute]
        READONLY[SELECT-Only<br/>Enforcement]
        COST[Cost Limits<br/>max_bytes_billed]
    end

    subgraph "Runtime"
        CORS[CORS<br/>Origin Whitelist]
        RATE[Rate Limiting<br/>Per User]
        LOG[PII Redaction<br/>In Logs]
    end
```

| Control | Implementation |
|---------|----------------|
| **API Authentication** | API key in `X-API-Key` header, validated in middleware |
| **SQL Injection** | Prohibited keyword list (DROP, DELETE, UPDATE, etc.) |
| **Query Validation** | BigQuery dry-run validates syntax and permissions |
| **Cost Control** | `maximum_bytes_billed` prevents expensive queries |
| **SELECT-Only** | Dry-run rejects non-SELECT statements |
| **CORS** | Whitelist of allowed origins |
| **User ID Validation** | Alphanumeric only, prevents path traversal |

---

## 8. Scalability & Performance

### 8.1 Scaling Architecture

```mermaid
flowchart TB
    subgraph "Load"
        USERS[Concurrent Users]
    end

    subgraph "Frontend - Scales Infinitely"
        CDN[Firebase CDN<br/>Cached Static Files]
    end

    subgraph "Backend - Auto-Scales"
        CR1[Cloud Run Instance 1]
        CR2[Cloud Run Instance 2]
        CRN[Cloud Run Instance N]
    end

    subgraph "Data Services - Serverless"
        BQ[BigQuery<br/>Auto-scales]
        FS[Firestore<br/>Auto-scales]
        VA[Vertex AI<br/>Managed Capacity]
    end

    USERS --> CDN
    CDN --> CR1 & CR2 & CRN
    CR1 & CR2 & CRN --> BQ & FS & VA

    style CDN fill:#FF6D01,color:#fff
    style CR1 fill:#4285F4,color:#fff
    style CR2 fill:#4285F4,color:#fff
    style CRN fill:#4285F4,color:#fff
```

### 8.2 Performance Characteristics

| Component | Latency | Scaling |
|-----------|---------|---------|
| **Firebase CDN** | ~50ms | Global edge, infinite scale |
| **Cloud Run** | 2-5s cold start, ~100ms warm | 0-5 instances auto-scale |
| **BigQuery** | 1-3s per query | Serverless, parallel execution |
| **Vertex AI RAG** | 500ms-1s | Managed, no config needed |
| **Gemini API** | 2-4s first token | Managed, quota-based |
| **Firestore** | ~50ms reads, ~100ms writes | Auto-scales with traffic |

### 8.3 Cold Start Mitigation

```mermaid
flowchart LR
    subgraph "Normal Operation"
        MIN0[min-instances: 0]
        COLD[Cold Start: 2-5s]
    end

    subgraph "Demo Mode"
        MIN1[min-instances: 1]
        WARM[Warm Response: ~100ms]
    end

    WARMUP[./deploy.sh warmup] --> MIN1
    COOLDOWN[./deploy.sh cooldown] --> MIN0

    style MIN0 fill:#FFCDD2
    style MIN1 fill:#C8E6C9
    style WARMUP fill:#34A853,color:#fff
    style COOLDOWN fill:#EA4335,color:#fff
```

**Warm-up Strategy:**
- Default: `min-instances=0` for cost optimization
- Before demos: `./scripts/deploy.sh warmup` sets `min-instances=1`
- After demos: `./scripts/deploy.sh cooldown` reverts to 0

---

## Appendix: Resource Summary

### GCP Resources

| Resource | Name/ID | Region |
|----------|---------|--------|
| **GCP Project** | `insightagent-adk` | - |
| **Cloud Run Service** | `insightagent` | asia-south1 |
| **Artifact Registry** | `insightagent/backend` | asia-south1 |
| **BigQuery Dataset** | `insightagent_data` | asia-south1 |
| **RAG Corpus** | `6917529027641081856` | asia-south1 |
| **Firestore** | (default database) | asia-south1 |
| **Service Account** | `insightagent-sa@insightagent-adk.iam.gserviceaccount.com` | - |

### IAM Roles

| Role | Purpose |
|------|---------|
| `roles/aiplatform.user` | Vertex AI API access (Gemini, RAG) |
| `roles/bigquery.dataViewer` | Read BigQuery tables |
| `roles/bigquery.jobUser` | Execute BigQuery queries |
| `roles/datastore.user` | Firestore read/write |

### Production URLs

| Service | URL |
|---------|-----|
| **Frontend** | https://insightagent-app.web.app |
| **Backend API** | https://insightagent-650676557784.asia-south1.run.app |
| **API Docs** | https://insightagent-650676557784.asia-south1.run.app/docs |

---
