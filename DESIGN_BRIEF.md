# InsightAgent UI Design Brief

## Project Overview

**InsightAgent** is an AI-powered Business Intelligence assistant that helps sales managers analyze company performance data through natural conversation. The agent queries live data from BigQuery, retrieves context from a knowledge base, and remembers insights across sessions.

**Target Platform:** Web application (desktop-first, responsive)
**Tech Stack:** React 18, TypeScript, TailwindCSS

---

## User Persona

**Primary User:** Sarah, Regional Sales Manager
- 35-45 years old
- Non-technical but data-curious
- Needs quick answers during meetings or end-of-day reviews
- Values speed, clarity, and actionable insights
- Typically asks 3-5 follow-up questions per session

**Context of Use:**
- Morning review before team standup
- Preparing for executive meetings
- End-of-quarter performance analysis
- Ad-hoc questions throughout the day

---

## Core User Flows

### Flow 1: New Session
1. User opens app → sees welcome state with suggested questions
2. Types or clicks a question
3. Sees real-time reasoning trace (which tools the AI is using)
4. Receives formatted answer with data
5. Clicks suggested follow-up or types new question

### Flow 2: Returning User (with Memory)
1. User opens app → system shows "Welcome back" with memory indicator
2. Previous findings/preferences are automatically applied
3. AI references past analyses in responses
4. User can view or reset their memory

---

## Key Features & Components

### 1. Chat Interface
The primary interaction surface.

**Requirements:**
- Message bubbles (user right-aligned, assistant left-aligned)
- Support for markdown rendering in responses (bold, bullets, tables)
- Auto-scroll to latest message
- Input area with send button and keyboard shortcut (Enter)
- Character limit indicator (4000 chars max)

### 2. Reasoning Trace Panel
Shows AI "thinking" in real-time - a key differentiator.

**Requirements:**
- Collapsible panel (expanded by default on desktop)
- Shows tool calls as they happen:
  - `query_bigquery` → "Querying sales data..."
  - `search_knowledge_base` → "Searching company policies..."
  - `get_conversation_context` → "Loading your preferences..."
  - `save_to_memory` → "Saving this insight..."
- Status indicators: spinner (in progress), checkmark (complete), X (error)
- Subtle animation when new trace items appear
- Shows row counts for queries, result counts for searches

**Example Trace:**
```
▼ Reasoning
  ✓ Querying BigQuery... (4 rows)
  ✓ Searching knowledge base... (2 results)
  ● Generating response...
```

### 3. Memory Indicator
Shows the user that the system remembers them.

**Requirements:**
- Subtle indicator in header/session bar when user has stored memory
- Tooltip or expandable showing: "3 saved findings, 2 preferences"
- Link to view full memory
- Option to reset memory (with confirmation)

### 4. Suggested Follow-ups
Reduces friction for exploration.

**Requirements:**
- 2-3 clickable chips/buttons below each AI response
- Contextual to the current answer
- Subtle styling (not competing with main response)

### 5. Welcome/Empty State
First impression for new users.

**Requirements:**
- Brief explanation of what InsightAgent can do
- 3-4 example questions as clickable cards:
  - "What was our Q4 2024 revenue?"
  - "Why did we miss our target?"
  - "How is the West region performing?"
  - "What's our churn rate trend?"

---

## Real-Time Streaming Behavior

The UI receives Server-Sent Events (SSE) as the AI processes. This creates a "typing" effect.

**Event Types:**
| Event | UI Behavior |
|-------|-------------|
| `reasoning` (started) | Add new trace item with spinner |
| `reasoning` (completed) | Update trace item with checkmark + summary |
| `content` | Append text to current message (streaming effect) |
| `memory` | Show toast/indicator "Insight saved" |
| `heartbeat` | Ignore (connection keep-alive) |
| `done` | Show suggested follow-ups, enable input |
| `error` | Show error message, enable retry |

**Important:** While streaming, the input should be disabled and show a subtle loading state.

---

## Data Display Patterns

The AI returns data in various formats. The UI should render them appropriately.

### Markdown Support
- **Bold** for emphasis
- Bullet lists for breakdowns
- Tables for comparisons (rare but possible)

### Metrics Display
Numbers should be formatted clearly:
- Currency: $12,765,996 (with commas)
- Percentages: -24.3% (with sign, colored red/green)
- Comparisons: "vs target" or "vs last quarter"

### Source Attribution
Responses often cite data sources. Render subtly:
> Source: `transactions` table, Q4 2024

---

## Layout Recommendations

### Desktop (>1024px)
```
┌─────────────────────────────────────────────────────┐
│  Logo    InsightAgent         [Memory] [User]       │
├─────────────────────────────────────────────────────┤
│                                    │                │
│     Chat Messages                  │  Reasoning     │
│     (scrollable)                   │  Trace Panel   │
│                                    │  (collapsible) │
│                                    │                │
├─────────────────────────────────────────────────────┤
│  [Type your question...                    ] [Send] │
└─────────────────────────────────────────────────────┘
```

### Mobile (<768px)
- Full-width chat
- Reasoning trace as expandable accordion above input
- Memory accessible via menu

---

## Visual Design Direction

### Tone
- **Professional but approachable** - this is a business tool, not a toy
- **Clean and focused** - minimal distractions from the conversation
- **Trustworthy** - the reasoning trace builds confidence in AI responses

### Color Suggestions
- Primary: Deep blue or teal (business/data feel)
- Accent: For interactive elements, highlights
- Success: Green (positive metrics, completed traces)
- Warning: Amber (targets missed, caution)
- Error: Red (errors, negative variances)
- Neutral: Grays for backgrounds, borders

### Typography
- Clear, readable sans-serif
- Monospace for data values, SQL references, table names
- Good hierarchy: questions vs answers vs metadata

---

## Interaction States

### Input Field
- Default: Ready for input
- Disabled: While AI is responding (subtle loading indicator)
- Error: If message fails to send

### Send Button
- Default: Enabled
- Loading: Spinner while sending
- Disabled: When input is empty or AI is responding

### Message Bubbles
- User: Solid background, right-aligned
- Assistant: Light background or bordered, left-aligned
- Streaming: Subtle pulse or cursor animation

### Reasoning Trace Items
- Pending: Spinner + muted text
- Complete: Checkmark + normal text + summary
- Error: X icon + error styling

---

## Accessibility Requirements

- Keyboard navigation (Tab through elements, Enter to send)
- Screen reader support for reasoning trace updates
- Sufficient color contrast (WCAG AA)
- Focus indicators on interactive elements
- Reduced motion option for animations

---

## Out of Scope (v1)

- Multi-session history browser
- Data export functionality
- Collaborative features
- Custom dashboard/charts
- Voice input

---

## Deliverables Requested

1. **Wireframes** - Low-fidelity layout for desktop and mobile
2. **Component Library** - Styled versions of:
   - Message bubbles (user, assistant, streaming)
   - Reasoning trace panel and items
   - Input area with states
   - Suggested follow-up chips
   - Memory indicator and modal
   - Welcome/empty state
3. **Interaction Specs** - Animations, transitions, loading states
4. **Final Mockups** - High-fidelity designs for key screens:
   - Empty state (new user)
   - Active conversation (mid-stream)
   - Completed response with follow-ups
   - Memory view modal

---

## Reference Links

- **API Documentation:** See `backend/app/api/routes.py`
- **SSE Event Types:** See "Real-Time Streaming Behavior" above
- **Sample Responses:** Available on request

---

## Questions for Designer

1. Any preference on sidebar (right) vs bottom panel for reasoning trace?
2. Should memory indicator be persistent or only shown when relevant?
3. Preference for streaming text animation style?
4. Any brand guidelines or existing design system to align with?

---

*Brief created: 2026-01-29*
*Contact: [Project Lead]*
