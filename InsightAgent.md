# InsightAgent — Demo Specification Document
## AI-Powered Business Intelligence Agent

---

## 1. Executive Summary

### 1.1 Purpose

InsightAgent is an AI-powered business intelligence assistant that demonstrates three core capabilities of Google ADK:

| Capability | What We're Proving | "Wow" Moment |
|------------|-------------------|--------------|
| **RAG** | Agent grounds answers in company knowledge | Agent explains *why* a metric matters using internal docs |
| **Tool Use** | Agent orchestrates multiple tools intelligently | Agent chains 3+ tool calls to answer one question |
| **Persistent Memory** | Agent remembers context across turns and sessions | Agent references earlier analysis without being reminded |

### 1.2 Product Vision

InsightAgent enables business users to conduct investigative analytics through natural conversation — without writing SQL or navigating complex BI tools. It answers questions, provides context from company knowledge, and remembers what matters.

**Tagline:** *"Ask questions. Get answers. With context."*

### 1.3 Success Criteria

| Metric | Target |
|--------|--------|
| Demo Duration | 5 minutes, scripted |
| Tool Chaining | At least one question requires 3+ tool calls |
| RAG Grounding | Every analytical answer includes knowledge base context |
| Memory Demonstration | Cross-session recall works seamlessly |
| Audience Reaction | Clear understanding of RAG, tools, and memory capabilities |

---

## 2. Scope Boundaries

### 2.1 In Scope (Build This)

- 4 well-defined tools with clear purposes
- 5-10 knowledge documents (markdown/text)
- Single BigQuery dataset (sales/revenue domain)
- Chat UI with visible reasoning trace
- Session memory (within conversation)
- Cross-session memory (user facts and past findings)
- Streaming responses with tool call visibility

### 2.2 Out of Scope (Do Not Build)

- Report generation (Word/Excel/PDF)
- Email delivery or scheduling
- Pivot tables and interactive charts
- Document upload UI
- User authentication
- Production error handling
- Multiple datasets or domains
- Data visualization beyond simple tables

---

## 3. Architecture Overview

### 3.1 Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Frontend** | React (Vite) + Firebase Hosting | Simple SPA, no SSR complexity |
| **Backend** | FastAPI + Cloud Run | Python-native for ADK, scales to zero |
| **Agent Framework** | Google ADK with Gemini 2.5 Flash | Target demonstration platform |
| **Database** | BigQuery | Enterprise data warehouse integration |
| **Vector Store** | ChromaDB (demo) or Vertex AI Vector Search (production) | RAG retrieval |
| **Memory Store** | Firestore  | Persistent user memory |

### 3.2 System Architecture

```
┌─────────────────────────────────────────────────────┐
│                   Firebase Hosting                   │
│              React SPA (Vite + Tailwind)            │
│         Chat UI with Reasoning Trace Display         │
└─────────────────────┬───────────────────────────────┘
                      │ HTTPS API calls (SSE for streaming)
                      ▼
┌─────────────────────────────────────────────────────┐
│                    Cloud Run                         │
│                 FastAPI Backend                      │
│  ┌─────────────────────────────────────────────┐   │
│  │            Google ADK Agent                  │   │
│  │                                              │   │
│  │  Tools:                                      │   │
│  │  • query_bigquery                           │   │
│  │  • search_knowledge_base                    │   │
│  │  • get_conversation_context                 │   │
│  │  • save_to_memory                           │   │
│  └─────────────────────────────────────────────┘   │
└───────┬──────────────┬─────────────────┬───────────┘
        │              │                 │
        ▼              ▼                 ▼
   ┌─────────┐   ┌──────────┐    ┌─────────────┐
   │BigQuery │   │ Vector   │    │  Firestore  │
   │  (Data) │   │  Store   │    │  (Memory)   │
   │         │   │  (RAG)   │    │             │
   └─────────┘   └──────────┘    └─────────────┘
```

---

## 4. Tool Specifications

### 4.1 Tool 1: `query_bigquery`

**Purpose:** Execute read-only SQL queries against the sales database

**When to Use:** 
- User asks "What", "How many", "Show me", or requests specific numbers
- Any question requiring actual data retrieval

**Input Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `sql_query` | string | Yes | Valid BigQuery SQL (SELECT only) |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether query executed successfully |
| `data` | array | List of row objects |
| `row_count` | integer | Number of rows returned |
| `columns` | array | Column names |
| `error` | string | Error message if failed |

**Constraints:**
- Maximum 1000 rows returned
- Query timeout: 30 seconds
- Read-only (SELECT statements only)
- Cost limit: $1 per query

**Few-Shot Examples to Include:**
1. Revenue by region with date filter
2. Top N customers by metric
3. Quarter-over-quarter comparison
4. Joining transactions with customers
5. Aggregation with multiple GROUP BY dimensions

**Error Handling:**
- If query returns zero rows: Do not invent data. Consider if filters were too restrictive. Try broader query or ask for clarification.
- If query fails: Return user-friendly error message, suggest correction.

---

### 4.2 Tool 2: `search_knowledge_base`

**Purpose:** Retrieve relevant company documents using semantic search

**When to Use:**
- User asks "Why", "How is X defined", "What's our policy on..."
- Questions about strategy, methodology, or business context
- When data alone doesn't explain the "why"

**Input Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `query` | string | Yes | Natural language search query |
| `top_k` | integer | No | Number of results (default 3, max 5) |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `results` | array | List of matching documents |
| `results[].content` | string | Relevant text chunk |
| `results[].source` | string | Document name |
| `results[].relevance_score` | float | Similarity score (0-1) |

**Knowledge Base Documents:**

| Document | Content Purpose |
|----------|-----------------|
| `metrics_definitions.md` | Definitions of churn, retention, LTV, CAC, MRR, revenue metrics |
| `company_targets_2024.md` | Revenue targets by region, growth goals, performance thresholds |
| `regional_strategy.md` | Notes on each region's strategy, challenges, market conditions |
| `pricing_policy.md` | Pricing tiers, discount rules, recent pricing changes |
| `customer_segments.md` | Definition of Enterprise/SMB/Consumer, characteristics, benchmarks |

**Retrieval Requirements:**
- Chunk size: 512 tokens with 50-token overlap
- Minimum relevance threshold: 0.7
- Always return source attribution

---

### 4.3 Tool 3: `get_conversation_context`

**Purpose:** Retrieve relevant information from current and past conversations

**When to Use:**
- User references "earlier", "last time", "what we discussed"
- Agent needs to recall previous findings or user preferences
- Starting a new session with returning user

**Input Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `context_type` | string | Yes | One of: "current_session", "user_preferences", "past_analyses" |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `context_type` | string | The type requested |
| `data` | object | Relevant context data |
| `last_updated` | timestamp | When context was last modified |

**Context Types:**

| Type | Contains |
|------|----------|
| `current_session` | Topics discussed, metrics queried, key findings from this conversation |
| `user_preferences` | Preferred formats, regions of interest, role, communication style |
| `past_analyses` | Summary of previous sessions with dates, topics, and key findings |

---

### 4.4 Tool 4: `save_to_memory`

**Purpose:** Persist important information for future reference

**When to Use:**
- Agent discovers a specific numerical finding
- User expresses a preference
- Key conclusion reached that should persist

**Input Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `memory_type` | string | Yes | One of: "finding", "preference", "context" |
| `key` | string | Yes | Short identifier (e.g., "q4_revenue_finding") |
| `value` | string | Yes | The information to remember |

**Output:**

| Field | Type | Description |
|-------|------|-------------|
| `success` | boolean | Whether save succeeded |
| `memory_type` | string | Type saved |
| `key` | string | Key used |
| `message` | string | Confirmation message |

**Memory Discipline — What to Save:**

| Save | Don't Save |
|------|------------|
| Specific metrics with numbers ("Q4 revenue was $12.4M") | Greetings or chit-chat |
| Root causes or explanations ("West decline due to pricing") | Intermediate query results |
| Explicit user preferences ("User focuses on Enterprise segment") | Information already in knowledge base |
| Key conclusions from analysis | General observations |

---

## 5. Memory Architecture

### 5.1 Memory Types

| Type | Scope | Persistence | Purpose |
|------|-------|-------------|---------|
| **Short-term** | Current conversation | Context window only | Maintain conversation flow |
| **Session Memory** | Current conversation | Tool-based storage | Track findings within session |
| **Long-term** | Cross-session | Database (Firestore) | Remember user across sessions |

### 5.2 Cross-Session Memory Injection

**Critical Requirement:** When a returning user starts a new session, past memory must be injected into the system prompt immediately — not retrieved only when the agent calls a tool.

**Behavior:**
1. On session start, check if user has past memory
2. If yes, inject summary into system prompt
3. Agent greets user with context: "Welcome back! Ready to continue that Q4 analysis?"
4. User doesn't need to ask "What did we discuss?"

### 5.3 Memory Data Structure

```
User Memory Store:
├── user_id
│   ├── preferences
│   │   ├── preferred_format: "tables with comparisons"
│   │   ├── regions_of_interest: ["West", "North"]
│   │   └── role: "Financial Analyst"
│   ├── findings
│   │   ├── q4_revenue: "Q4 revenue was $12.4M, 4.6% below target"
│   │   └── west_region: "West region drove Q4 miss, down 25.7%"
│   └── sessions
│       └── [session_id]
│           ├── date: "2024-01-15"
│           ├── topics: ["Q4 revenue", "West region", "pricing impact"]
│           └── key_findings: [...]
```

---

## 6. Agent System Prompt

```markdown
You are InsightAgent, an AI business intelligence assistant for Acme Corporation.

## Your Identity
You help business users understand their data through conversation. You're knowledgeable, 
precise, and always ground your answers in actual data and company knowledge.

## Your Capabilities
1. Query the company's BigQuery data warehouse for sales and customer data
2. Search the company knowledge base for definitions, policies, and context
3. Remember context within and across conversations
4. Provide analytical insights with business context

## Core Behaviors

### Always:
- Show your reasoning process (what tools you're using and why)
- Ground answers in BOTH data (query BigQuery) AND context (search knowledge base)
- Compare metrics to targets and benchmarks when available
- Remember key findings and user preferences for future reference
- Provide the direct answer first, then supporting details

### Never:
- Make up data or statistics
- Provide numbers without querying the database
- Ignore company-specific definitions in favor of generic ones
- Save trivial information to memory

## Tool Selection Guidelines

### Use `query_bigquery` when:
- User asks "What", "How many", "Show me", "List", "Compare"
- Any question requiring specific numbers or data

### Use `search_knowledge_base` when:
- User asks "Why", "What does X mean", "How do we calculate", "What's our policy"
- You need company-specific context to interpret data
- Data alone doesn't explain the situation

### Use `get_conversation_context` when:
- User references previous discussion ("earlier", "like we said", "continue")
- You need to recall what was already established
- Starting response to a returning user

### Use `save_to_memory` when:
- You discover a specific numerical finding worth remembering
- User expresses a clear preference
- You reach a key conclusion from analysis

### Multi-Tool Orchestration:
For complex questions, typically:
1. First, check if terms need definition → `search_knowledge_base`
2. Then, query the relevant data → `query_bigquery`
3. Add comparative context → `query_bigquery` (for historical comparison)
4. Explain with business context → `search_knowledge_base`
5. Save important findings → `save_to_memory`

## Response Format

### For Data Questions:
1. Direct answer with key number(s)
2. Formatted table if multiple data points
3. Comparison to targets/benchmarks/prior periods
4. Business context from knowledge base
5. Suggested follow-up questions

### For Context Questions:
1. Direct answer citing source document
2. Relevant details from knowledge base
3. Connection to data if applicable
4. Offer to run related analysis

### Formatting Rules:
- Use tables for data with 3+ rows
- Include trend indicators: ✅ (positive), ⚠️ (warning), 🔴 (negative)
- Keep explanations concise — 2-3 sentences max per insight
- Always indicate when you're saving something to memory: 💾

## Handling Edge Cases

### Empty Query Results:
If a query returns no data:
1. Do not invent data
2. Consider if your filters were too restrictive
3. Try a broader query or different approach
4. If still no data, tell the user and ask for clarification

### Ambiguous Questions:
If the question could be interpreted multiple ways:
1. State your interpretation
2. Provide the answer based on that interpretation
3. Offer alternative interpretations: "If you meant X instead, let me know"

### Conflicting Information:
If knowledge base and data seem to conflict:
1. Present both pieces of information
2. Note the apparent discrepancy
3. Suggest possible explanations
4. Recommend verification

## Available Data Domain
You have access to sales and customer data including:
- Transaction records (revenue, quantities, dates, regions, products)
- Customer information (segments, acquisition dates, lifetime value)
- Targets and benchmarks (by region, quarter, year)

## Returning Users
When a user returns with existing memory:
- Greet them with awareness of past context
- Offer to continue previous analysis or start fresh
- Reference relevant past findings when appropriate
```

---

## 7. Sample Conversation Flow — Demo Script

**Total Duration:** 5 minutes

---

### Scene 1: Simple Query + RAG Grounding (60 seconds)

**Setup:** Demonstrate that the agent queries data AND provides context from knowledge base.

**User:** 
> "What was our Q4 revenue?"

**Agent Reasoning (visible in UI):**
```
🔍 Searching knowledge base for revenue definitions...
📊 Querying BigQuery for Q4 2024 revenue...
📈 Querying targets for comparison...
```

**Agent Response:**

> **Q4 2024 Revenue: $12.4M**
>
> | Metric | Value |
> |--------|-------|
> | Q4 2024 Actual | $12.4M |
> | Q4 2024 Target | $13.0M |
> | vs Target | -$0.6M (-4.6%) ⚠️ |
> | vs Q4 2023 | +$2.8M (+29.2%) ✅ |
>
> **Context:** While we missed our Q4 target by 4.6%, year-over-year growth remains strong at 29%. Per company performance thresholds, this is classified as "slightly below target" (within 10% variance).
>
> 💾 *Saved: Q4 revenue was $12.4M, 4.6% below target*
>
> **Would you like to:**
> - Break down by region?
> - Understand why we missed target?
> - Compare to other quarters?

**Demo Point:** Agent didn't just return a number — it added target comparison and business context from knowledge base.

---

### Scene 2: Multi-Tool Orchestration (90 seconds)

**Setup:** Demonstrate complex tool chaining where agent decides which tools to call and in what order.

**User:** 
> "Why did we miss the target?"

**Agent Reasoning (visible in UI):**
```
🔍 Checking company definition of "underperformance"...
📊 Querying revenue by region to identify problem areas...
📊 Querying revenue by segment for additional breakdown...
🔍 Searching knowledge base for regional context...
💭 Synthesizing findings...
```

**Agent Response:**

> **Root Cause Analysis: Q4 Target Miss**
>
> The $0.6M shortfall is concentrated in **West region**:
>
> | Region | Actual | Target | Variance |
> |--------|--------|--------|----------|
> | North | $3.8M | $3.5M | +8.6% ✅ |
> | South | $3.1M | $3.0M | +3.3% ✅ |
> | East | $2.9M | $3.0M | -3.3% ⚠️ |
> | **West** | **$2.6M** | **$3.5M** | **-25.7%** 🔴 |
>
> **Why West Underperformed:**
>
> Per our knowledge base, two factors affected West region in Q4:
>
> 1. **November 1 Price Increase:** Our pricing policy shows a 12% price increase took effect Nov 1, primarily affecting West region customers on legacy pricing.
>
> 2. **Competitive Pressure:** Regional strategy notes indicate CompetitorX ran aggressive Q4 promotions targeting our West territory.
>
> 💾 *Saved: West region drove Q4 miss, down 25.7% due to pricing + competition*
>
> **Recommended Next Steps:**
> - Analyze West region customer churn post-price increase
> - Review competitive response options

**Demo Point:** Agent chained 4+ tool calls, combined data with knowledge base context, and reached a synthesized conclusion.

---

### Scene 3: Memory Within Session (60 seconds)

**Setup:** Demonstrate that agent remembers context from earlier in the conversation.

**User:** 
> "How does West compare to last quarter?"

**Agent Reasoning (visible in UI):**
```
💭 User is continuing West region analysis from earlier...
📊 Querying West region Q3 vs Q4 comparison...
```

**Agent Response:**

> **West Region: Q3 → Q4 Comparison**
>
> Following up on our West region analysis:
>
> | Metric | Q3 2024 | Q4 2024 | Change |
> |--------|---------|---------|--------|
> | Revenue | $3.4M | $2.6M | -23.5% 🔴 |
> | Transactions | 1,247 | 892 | -28.5% 🔴 |
> | Avg Deal Size | $2,726 | $2,915 | +6.9% ✅ |
>
> **Insight:** Transaction volume dropped sharply (28.5%), but customers who stayed are spending more per transaction (+6.9%). This suggests the price increase drove away price-sensitive customers while retaining higher-value accounts.
>
> 💾 *Saved: West lost volume but retained higher-value customers*
>
> This pattern aligns with the November pricing change we identified earlier.

**Demo Point:** Agent didn't ask "which region?" — it remembered we were discussing West from the previous exchange.

---

### Scene 4: Cross-Session Memory (45 seconds)

**Setup:** Simulate returning the next day. Demonstrate that agent remembers past session.

*[New session — next day]*

**User:** 
> "Continue where we left off"

**Agent Reasoning (visible in UI):**
```
💭 Retrieving past session context for this user...
```

**Agent Response:**

> Welcome back! In your last session, you were analyzing **Q4 performance**. Here's what we discovered:
>
> **Key Findings from Previous Session:**
> - Q4 revenue was $12.4M, 4.6% below target
> - West region drove the miss, down 25.7%
> - Root cause: November pricing change + competitor promotions
> - West lost transaction volume but retained higher-value customers
>
> **Where would you like to continue?**
> - Dive deeper into West region customer analysis
> - Look at other regions' performance
> - Analyze pricing impact company-wide
> - Start a fresh analysis

**Demo Point:** Agent immediately recalled past session without user having to summarize. This is the cross-session memory "wow" moment.

---

### Scene 5: RAG Contextual Grounding (45 seconds)

**Setup:** Demonstrate RAG providing company-specific definitions and benchmarks.

**User:** 
> "Is our churn rate healthy?"

**Agent Reasoning (visible in UI):**
```
🔍 Searching knowledge base for churn definition and benchmarks...
📊 Calculating current churn rate from customer data...
```

**Agent Response:**

> **Churn Rate Assessment**
>
> | Metric | Value | Status |
> |--------|-------|--------|
> | Current Churn | 4.2% | ⚠️ Above Target |
> | Company Target | 3.5% | — |
> | Industry Benchmark | 5.1% | — |
>
> **Assessment:**
>
> Per our metrics definitions, churn = customers with no purchase in last 90 days after being active in prior 90-day period.
>
> At 4.2%, we're **above our internal target (3.5%)** but **below industry average (5.1%)**. This is a moderate concern — not critical, but room for improvement.
>
> Given your earlier analysis showing West region customer losses, would you like to see churn broken down by region?

**Demo Point:** Agent didn't use a generic definition of churn — it used the company's specific definition from the knowledge base and compared to company-specific targets.

---

## 8. Frontend Requirements

### 8.1 Core Components

| Component | Purpose |
|-----------|---------|
| **Chat Container** | Scrollable message history |
| **Message Bubbles** | Distinguish user vs agent messages |
| **Reasoning Panel** | Expandable section showing tool calls in progress |
| **Input Area** | Text input with send button |
| **Suggested Actions** | Clickable follow-up suggestions |

### 8.2 Reasoning Trace Display

**Critical Requirement:** Users must see what the agent is doing in real-time.

**Display Format:**
```
┌─────────────────────────────────────────┐
│ 🔍 Searching knowledge base...          │
│ ✓ Found: metrics_definitions.md         │
│ 📊 Querying BigQuery...                 │
│ ✓ Retrieved 4 rows                      │
│ 💭 Synthesizing response...             │
└─────────────────────────────────────────┘
```

**Behavior:**
- Stream tool calls as they happen
- Show success/failure status for each
- Collapse after response completes
- Allow user to expand and review

### 8.3 Response Rendering

| Content Type | Rendering |
|--------------|-----------|
| Tables | Formatted HTML tables with alignment |
| Metrics | Highlighted numbers with trend indicators |
| Memory saves | Subtle indicator (💾) with saved content |
| Follow-ups | Clickable buttons/chips |
| Citations | Linked to source document name |

### 8.4 Streaming Requirements

- Use Server-Sent Events (SSE) for streaming responses
- Stream reasoning trace events separately from response text
- Handle connection drops gracefully
- Show typing indicator during generation

---

## 9. Backend API Requirements

### 9.1 Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/chat/session` | POST | Create new chat session |
| `/chat/message` | POST | Send message, receive streaming response |
| `/chat/history/{session_id}` | GET | Retrieve conversation history |
| `/user/memory` | GET | Retrieve user's persistent memory |

### 9.2 Message Request

```
POST /chat/message
{
  "session_id": "string",
  "user_id": "string", 
  "content": "string"
}
```

### 9.3 Streaming Response Format

```
event: reasoning
data: {"tool": "search_knowledge_base", "status": "started", "query": "..."}

event: reasoning
data: {"tool": "search_knowledge_base", "status": "completed", "results": 3}

event: reasoning
data: {"tool": "query_bigquery", "status": "started"}

event: content
data: {"delta": "**Q4 2024 Revenue: $12.4M**\n\n"}

event: content
data: {"delta": "| Metric | Value |\n"}

event: memory
data: {"action": "saved", "key": "q4_revenue", "value": "..."}

event: done
data: {"suggested_followups": ["Break down by region?", "Compare to Q3?"]}
```

### 9.4 Session Management

- Sessions persist for 24 hours of inactivity
- Session includes: conversation history, current context, temporary findings
- User memory persists indefinitely (separate from session)

---

## 10. Non-Functional Requirements

### 10.1 Performance

| Metric | Target |
|--------|--------|
| Time to first token | < 2 seconds |
| Simple query end-to-end | < 5 seconds |
| Complex multi-tool query | < 15 seconds |
| Knowledge base search | < 2 seconds |
| BigQuery execution | < 10 seconds |

### 10.2 Reliability

| Requirement | Specification |
|-------------|---------------|
| Error handling | User-friendly messages, no stack traces |
| Fallback behavior | If one tool fails, agent explains and continues |
| Timeout handling | Graceful timeout messages after 30 seconds |

### 10.3 Demo Environment

| Aspect | Requirement |
|--------|-------------|
| Concurrent users | Support 5 simultaneous demo sessions |
| Data freshness | Static demo data (no real-time updates needed) |
| Reset capability | Ability to clear user memory for fresh demo |

---

## 11. Demo Data Requirements

### 11.1 Data Characteristics

The seed data must be engineered to support the demo narrative:

| Requirement | Target Value |
|-------------|--------------|
| Q4 2024 total revenue | $12.4M |
| Q4 2024 target | $13.0M |
| West region variance | -25.7% vs target |
| Other regions | Slightly above target |
| Q4 2023 revenue | ~$9.6M (for YoY comparison) |
| Churn rate | 4.2% |
| Transaction drop in West (Q3→Q4) | ~28% |

### 11.2 Knowledge Base Requirements

Each document must contain specific content that will be retrieved during the demo:

| Document | Must Include |
|----------|--------------|
| `metrics_definitions.md` | Churn definition (90-day window), company target (3.5%), industry benchmark (5.1%) |
| `company_targets_2024.md` | Q4 targets by region, "underperformance" threshold (>10% below) |
| `regional_strategy.md` | Note about CompetitorX Q4 promotions in West |
| `pricing_policy.md` | November 1 price increase (12%), West region legacy pricing impact |
| `customer_segments.md` | Enterprise/SMB/Consumer definitions with LTV benchmarks |

---

## 12. Appendix: Capability Demonstration Checklist

Use this checklist to verify all three core capabilities are demonstrated:

### RAG Demonstration
- [ ] Agent retrieves company-specific metric definition
- [ ] Agent cites source document by name
- [ ] Agent uses internal benchmark (not generic industry data)
- [ ] Answer would be wrong or incomplete without RAG

### Tool Use Demonstration
- [ ] Agent chains 3+ tools for one question
- [ ] Agent shows reasoning for tool selection
- [ ] Agent handles tool combining data + context
- [ ] Visible reasoning trace shows tool progression

### Memory Demonstration
- [ ] Agent remembers topic from earlier in conversation
- [ ] Agent saves specific finding with 💾 indicator
- [ ] Cross-session: Agent recalls past session on return
- [ ] Agent uses saved preference to personalize response

---

