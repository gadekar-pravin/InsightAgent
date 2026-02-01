# InsightAgent Feature Ideas

Feature suggestions to enhance the demo experience for internal stakeholders.

---

## Current Capabilities

| Capability | Description |
|------------|-------------|
| **RAG** | Grounds answers in company knowledge using Vertex AI RAG Engine |
| **Tool Use** | Orchestrates 4 tools (BigQuery, Knowledge Base, Context, Memory) |
| **Persistent Memory** | Remembers context across sessions via Firestore |
| **Reasoning Panel** | Shows tool execution traces in the UI |
| **SSE Streaming** | Real-time response streaming |

---

## High-Impact Features for Demo

### 1. Data Visualization

Auto-generate charts when the agent returns numerical data (revenue trends, regional comparisons). Libraries like Recharts integrate well with React.

- **Demo moment:** "Show me quarterly revenue trend" → interactive bar chart appears
- **Effort:** Medium
- **Tech:** Recharts or Chart.js

### 2. Voice Input

Add speech-to-text using the Web Speech API (browser-native, no cost). Executives love talking to AI.

- **Demo moment:** Click mic icon, ask "What's our churn rate?" hands-free
- **Effort:** Low
- **Tech:** Web Speech API (built into browsers)

### 3. Source Citations with Links

When RAG retrieves from knowledge_base, show clickable citations (e.g., "According to [Regional Strategy]..."). Builds trust.

- **Demo moment:** Shows the agent isn't hallucinating—answers are grounded
- **Effort:** Medium
- **Tech:** Modify RAG response to include source metadata

### 4. Thumbs Up/Down Feedback

Simple feedback buttons on each response. Store in Firestore. Shows you're thinking about quality.

- **Demo moment:** "We're collecting feedback to improve the model"
- **Effort:** Low
- **Tech:** Firestore collection for feedback

### 5. Export Conversation as PDF/Report

One-click export of the analysis with charts included. Business users love shareable artifacts.

- **Demo moment:** "Here's the report from our 5-minute conversation"
- **Effort:** Medium
- **Tech:** react-pdf or html2pdf.js

### 6. Interactive Data Table + Drilldowns

When answers include tabular results (e.g., top customers, churn by segment), render a sortable/filterable table with quick drilldown actions.

- **Demo moment:** Click a row → "Explain why this segment churned" with the row pre-attached as context
- **Effort:** Medium
- **Tech:** TanStack Table (React Table) + existing SSE payloads

---

## Medium-Effort, High-Polish Features

| Feature | Description | Effort |
|---------|-------------|--------|
| **Dark Mode** | Toggle in header—always gets a reaction | Low |
| **Typing Indicators** | Show "Analyzing data..." with tool-specific animations | Low |
| **Suggested Questions** | Prominent chips after each response (SSE event exists) | Low |
| **Data Freshness Badge** | Show “Data as of …” for BigQuery-backed answers | Low |
| **Conversation Bookmarks** | Star important findings for quick reference | Medium |
| **Multi-session Sidebar** | Show past conversations, not just memory | Medium |
| **Shareable Conversation Link** | Read-only link for stakeholders (no login for demo) | Medium |
| **Prompt Templates / Scenario Picker** | Pre-built prompts for “Revenue deep dive”, “Churn analysis”, etc. | Medium |

---

## Advanced Showcase Features

### 7. Proactive Insights / Anomaly Detection

Agent notices unusual patterns and highlights them automatically.

- **Example:** "I noticed West region revenue dropped 15% vs last quarter—want me to investigate?"
- **Effort:** High
- **Tech:** Add anomaly detection logic in BigQuery tool or post-processing

### 8. Comparison Mode

Split-screen comparing two time periods or regions side-by-side with synchronized charts.

- **Demo moment:** Visual side-by-side of Q3 vs Q4 performance
- **Effort:** High
- **Tech:** New UI component with dual chart rendering

### 9. "Show Your Work" Mode

Expand the reasoning panel to show the actual SQL queries and RAG chunks retrieved—transparency for technical stakeholders.

- **Demo moment:** Technical audience sees exactly what data was queried
- **Effort:** Low (data already available in reasoning events)
- **Tech:** Enhance ReasoningPanel component

### 10. What-If Scenarios

Allow hypothetical questions with projected calculations.

- **Example:** "What would revenue look like if West matched East's growth rate?"
- **Effort:** High
- **Tech:** Add calculation tool or enhance BigQuery tool

### 11. Enterprise Guardrails (PII + Policy)

Detect and block/redact sensitive outputs, and show a clear policy banner when something is refused. This reads as “enterprise-ready” in demos.

- **Demo moment:** "Can you list customer emails?" → polite refusal + safe alternative summary
- **Effort:** Medium–High
- **Tech:** Simple rules + DLP API (optional) + allowlist-based tool schemas

### 12. Action Integrations (Jira/Slack/Email)

Turn insights into actions: create a Jira ticket, draft an email, or post a summary to Slack/Teams.

- **Demo moment:** "Create a ticket for investigating West churn drivers"
- **Effort:** High
- **Tech:** Add action tools with OAuth + audit logging

---

## Quick Wins (< 1 day each)

| Feature | Description |
|---------|-------------|
| **Keyboard shortcuts** | `⌘+K` to focus input, `⌘+N` for new session |
| **Copy response button** | One-click copy on each message |
| **Token/cost counter** | Show in reasoning panel (demonstrates efficiency) |
| **Loading skeleton** | Replace spinner with skeleton UI |
| **Onboarding tooltips** | Guide first-time users through the interface |
| **Demo scenario gallery** | One-click buttons to run “best demo” flows end-to-end |
| **Download table as CSV** | When results are tabular, allow export for follow-up analysis |
| **Regenerate options** | “Shorter”, “More detailed”, “Executive summary” buttons |

---

## Recommended Priority

For maximum demo impact with reasonable effort:

| Priority | Feature | Why |
|----------|---------|-----|
| 1 | **Data Visualization** | Transforms raw numbers into visual insights |
| 2 | **Source Citations** | Proves trustworthiness and grounding |
| 3 | **Voice Input** | Wow factor for executives |
| 4 | **Feedback Buttons** | Shows production-readiness thinking |
| 5 | **Dark Mode** | Quick win, always impressive |

---

## Implementation Notes

### Data Visualization Approach

```
User asks about revenue → Agent returns data →
Frontend detects numeric data → Auto-renders chart
```

Consider adding a `visualization` field to SSE events:
```json
{
  "type": "visualization",
  "data": {
    "chartType": "bar",
    "labels": ["Q1", "Q2", "Q3", "Q4"],
    "values": [2.1, 2.3, 2.5, 2.2]
  }
}
```

### Voice Input Approach

```typescript
const recognition = new webkitSpeechRecognition();
recognition.onresult = (event) => {
  const transcript = event.results[0][0].transcript;
  sendMessage(transcript);
};
```

### Feedback Storage Schema

```
Firestore: feedback/{feedbackId}
{
  sessionId: string,
  messageId: string,
  rating: "positive" | "negative",
  timestamp: Timestamp,
  userId: string
}
```

---

*Document created: 2025. Updated: 2026-02-01*
