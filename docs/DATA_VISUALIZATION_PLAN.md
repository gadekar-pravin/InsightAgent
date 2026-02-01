# Data Visualization Implementation Plan

**Feature**: Auto-generate charts when BigQuery returns visualizable numerical data.

**Status**: Planning Complete

---

## Overview

Add auto-generated charts to InsightAgent when BigQuery returns visualizable data. Charts render inline with assistant messages, providing immediate visual insights without user action.

**Approach**: Backend detects visualizable data and emits a new `visualization` SSE event. Frontend receives the event, stores it with the message, and renders the appropriate chart component using Recharts.

**Important note about SSE framing in this repo**: the backend API writes `event: visualization` and the frontend receives only the JSON payload written on the `data:` line. The `seq` is assigned in `/backend/app/api/routes.py` (the API layer), not by the agent.

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  BigQuery Tool  │────▶│  Visualization   │────▶│  SSE Event      │
│  (returns data) │     │  Detection       │     │  (event: visualization) │
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Chart Render   │◀────│  State Update    │◀────│  SSE Handler    │
│  (Recharts)     │     │  (ChatContext)   │     │  (api.ts)       │
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

**Key Decision**: Backend decides when/what to visualize because it has access to the data structure and query context.

---

## Design Decisions

### 1. Data Delivery: New SSE Event Type

**Decision**: Introduce a dedicated `visualization` SSE event type.

**Rationale**:
- Clean separation of concerns (visualization data is distinct from content text)
- No parsing/extraction needed on frontend
- Backend has full control over what/when to visualize
- Aligns with existing event pattern (`reasoning`, `content`, `memory`, `done`)

**Event Structure**:
```json
{
  "seq": 5,
  "chart_type": "bar",
  "title": "Revenue by Region",
  "data": [
    {"region": "North", "total_revenue": 2500000},
    {"region": "South", "total_revenue": 2100000}
  ],
  "columns": ["region", "total_revenue"],
  "x_axis": "region",
  "y_axis": "total_revenue"
}
```

This payload is emitted as:

```
event: visualization
data: { ...json above... }
```

### 2. Chart Library: Recharts

**Decision**: Use Recharts for chart rendering.

| Criteria | Recharts | Chart.js | Custom SVG |
|----------|----------|----------|------------|
| React-native | Yes (composable) | Wrapper needed | Manual |
| Bundle size | ~40KB | ~60KB | Minimal |
| Tailwind integration | Easy (className props) | Difficult | Full control |
| TypeScript | Excellent | Good | Full control |
| Dark mode | Easy theming | CSS hacks | Full control |

**Rationale**: Recharts is designed for React with composable components, supports responsive containers, easy to style with Tailwind, and has excellent TypeScript support.

### 3. Visualization Detection

**Decision**: Backend detects and emits visualization events.

**Detection Criteria**:
- Query returned successfully
- 2-20 rows (optimal for chart clarity)
- At least 1 numeric column and 1 categorical column
- Data structure is suitable for charting

**Implementation detail (recommended)**:
- Determine column types by scanning for the first non-null sample per column (avoid a null in the first row breaking detection).
- Treat `date/datetime` values as chartable x-axis values (they are serialized as ISO strings by `_json_dumps(..., default=str)`).
- Emit only the fields needed for the chart (typically `x_axis`, `y_axis`, and the projected `{x,y}` rows) to reduce SSE payload size and avoid leaking unrelated columns.

### 4. Chart Type Selection

**Heuristics**:

| Data Shape | Chart Type |
|------------|------------|
| Time-based x-axis (date, month, quarter, year) | Line chart |
| 2-5 categorical rows | Pie chart |
| Default (6-20 rows) | Bar chart |

---

## Implementation Steps

### Phase 1: Backend - Visualization Detection & SSE Event

**File**: `/backend/app/agent/insight_agent.py`

#### Step 1.1: Add Visualization Detection Methods

Add helper methods near other formatting/helpers (exact line numbers may drift):

```python
def _should_visualize(self, result: dict) -> dict | None:
    """
    Determine if BigQuery result should be visualized.

    Args:
        result: BigQuery tool result dictionary

    Returns:
        Visualization config dict if data is chartable, None otherwise
    """
    if not result.get("success") or result.get("row_count", 0) < 2:
        return None

    data = result.get("data", [])
    columns = result.get("columns", [])

    # Need 2-20 rows for meaningful chart
    if len(data) > 20:
        return None

    # Identify column types (recommend: scan for first non-null sample)
    numeric_cols = []
    categorical_cols = []

    for col in columns:
        sample_value = data[0].get(col)
        if isinstance(sample_value, (int, float)):
            numeric_cols.append(col)
        elif isinstance(sample_value, str):
            categorical_cols.append(col)

    # Need at least 1 categorical and 1 numeric for meaningful chart
    if not numeric_cols or not categorical_cols:
        return None

    chart_type = self._select_chart_type(data, categorical_cols[0], len(data))

    return {
        "chart_type": chart_type,
        "title": self._generate_chart_title(columns),
        "data": data,
        "columns": columns,
        "x_axis": categorical_cols[0],
        "y_axis": numeric_cols[0],
    }

def _select_chart_type(self, data: list, x_col: str, row_count: int) -> str:
    """
    Select appropriate chart type based on data shape.

    Args:
        data: List of data rows
        x_col: Name of the x-axis column
        row_count: Number of data rows

    Returns:
        Chart type string: 'bar', 'line', or 'pie'
    """
    x_lower = x_col.lower()

    # Time-based data -> line chart
    time_indicators = ['date', 'month', 'quarter', 'year', 'time', 'period']
    if any(t in x_lower for t in time_indicators):
        return 'line'

    # Few categories -> pie chart (good for showing proportions)
    if row_count <= 5:
        return 'pie'

    # Default to bar chart
    return 'bar'

def _generate_chart_title(self, columns: list) -> str:
    """
    Generate a chart title from column names.

    Args:
        columns: List of column names

    Returns:
        Human-readable chart title
    """
    if len(columns) >= 2:
        y_label = columns[1].replace('_', ' ').title()
        x_label = columns[0].replace('_', ' ').title()
        return f"{y_label} by {x_label}"
    return "Query Results"
```

#### Step 1.2: Emit Visualization Event

Modify the tool execution block. After the "completed" reasoning event (around line 536), add visualization event emission:

```python
# Emit tool complete event with summary
yield {
    "type": "reasoning",
    "seq": next_seq(),
    "data": {
        "trace_id": trace_id,
        "tool_name": fc.name,
        "status": "completed",
        "summary": summary,
        **event_data,
    },
}

# NEW: Emit visualization event if applicable
if fc.name == "query_bigquery" and result.get("success"):
    viz_data = self._should_visualize(result)
    if viz_data:
        yield {
            "type": "visualization",
            "seq": next_seq(),
            "data": viz_data,
        }
```

Note: the API layer assigns the final `seq` sent to the client; the agent-local `next_seq()` is fine to keep for internal ordering, but it is not the source of truth for frontend ordering.

---

### Phase 2: Frontend - Type Definitions

**File**: `/frontend/src/types/api.ts`

#### Step 2.1: Add Visualization Types

Add after line 77 (after `ErrorEvent`):

```typescript
// =============================================================================
// Visualization Types
// =============================================================================

export interface VisualizationData {
  chart_type: 'bar' | 'line' | 'pie';
  title: string;
  data: Array<Record<string, string | number>>;
  columns: string[];
  x_axis: string;
  y_axis: string;
}

export type VisualizationEvent = VisualizationData & { seq: number };
```

#### Step 2.2: Update SSEEventType

Change line 43:

```typescript
// Before
export type SSEEventType = 'reasoning' | 'content' | 'memory' | 'heartbeat' | 'done' | 'error';

// After
export type SSEEventType = 'reasoning' | 'content' | 'memory' | 'visualization' | 'heartbeat' | 'done' | 'error';
```

#### Step 2.3: Update ChatMessage Interface

Modify lines 198-205:

```typescript
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  reasoning_trace?: ReasoningTrace[];
  visualization?: VisualizationData;  // NEW
  isStreaming?: boolean;
}
```

---

### Phase 3: Frontend - SSE Handler

**File**: `/frontend/src/services/api.ts`

#### Step 3.1: Update SSECallback Interface

Find the `SSECallback` interface and add:

```typescript
export type SSECallback = {
  onReasoning?: (event: ReasoningEvent) => void;
  onContent?: (event: ContentEvent) => void;
  onMemory?: (event: MemoryEvent) => void;
  onVisualization?: (event: VisualizationEvent) => void;  // NEW
  onDone?: (event: DoneEvent) => void;
  onError?: (event: ErrorEvent) => void;
  onHeartbeat?: () => void;
};
```

#### Step 3.2: Add Case in Switch Statement

Find the switch statement in `sendMessage` and add:

```typescript
case 'visualization':
  callbacks.onVisualization?.(data as VisualizationEvent);
  break;
```

---

### Phase 4: Frontend - State Management

**File**: `/frontend/src/context/ChatContext.tsx`

#### Step 4.1: Add Import

```typescript
import type { VisualizationData, VisualizationEvent } from '../types/api';
```

#### Step 4.2: Add Action Type

Find the `ChatAction` type definition and add:

```typescript
| { type: 'SET_VISUALIZATION'; payload: VisualizationData }
```

#### Step 4.3: Add Reducer Case

Add in the `chatReducer` switch statement:

```typescript
case 'SET_VISUALIZATION': {
  const messages = [...state.messages];
  const lastIdx = messages.length - 1;
  if (lastIdx >= 0 && messages[lastIdx].role === 'assistant') {
    messages[lastIdx] = {
      ...messages[lastIdx],
      visualization: action.payload,
    };
  }
  return { ...state, messages };
}
```

#### Step 4.4: Add Callback in sendChatMessage

In the `sendChatMessage` function, add to the callbacks object:

```typescript
onVisualization: (event: VisualizationEvent) => {
  dispatch({
    type: 'SET_VISUALIZATION',
    payload: {
      chart_type: event.chart_type as 'bar' | 'line' | 'pie',
      title: event.title,
      data: event.data,
      columns: event.columns,
      x_axis: event.x_axis,
      y_axis: event.y_axis,
    },
  });
},
```

---

### Phase 5: Frontend - Chart Components

#### Step 5.1: Install Recharts

```bash
cd frontend
npm install recharts
```

#### Step 5.2: Create Chart Configuration

**File**: `/frontend/src/components/charts/chartConfig.ts` (NEW)

```typescript
/**
 * Chart configuration and theme utilities.
 */

// Primary color palette matching Tailwind config
export const CHART_COLORS = [
  '#137fec',  // Primary blue
  '#10b981',  // Emerald
  '#f59e0b',  // Amber
  '#ef4444',  // Red
  '#8b5cf6',  // Violet
];

/**
 * Get theme-aware colors for chart elements.
 */
export const getThemeColors = (isDark: boolean) => ({
  axis: isDark ? '#94a3b8' : '#64748b',      // slate-400 / slate-500
  grid: isDark ? '#334155' : '#e2e8f0',      // slate-700 / slate-200
  bg: isDark ? '#1e293b' : '#ffffff',        // slate-800 / white
  border: isDark ? '#334155' : '#e2e8f0',    // slate-700 / slate-200
  text: isDark ? '#e2e8f0' : '#334155',      // slate-200 / slate-700
});

/**
 * Format large numbers for display on chart axes.
 */
export const formatValue = (value: number): string => {
  if (typeof value !== 'number') return String(value);

  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return value.toLocaleString();
};
```

#### Step 5.3: Create Main Visualization Component

**File**: `/frontend/src/components/charts/DataVisualization.tsx` (NEW)

```typescript
/**
 * Data visualization component that renders appropriate chart type.
 */

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { VisualizationData } from '../../types/api';
import { CHART_COLORS, getThemeColors, formatValue } from './chartConfig';

interface DataVisualizationProps {
  data: VisualizationData;
}

export function DataVisualization({ data }: DataVisualizationProps) {
  // Detect dark mode from document class
  const isDark = document.documentElement.classList.contains('dark');
  const theme = getThemeColors(isDark);

  const commonChartProps = {
    data: data.data,
    margin: { top: 20, right: 30, left: 20, bottom: 5 },
  };

  const tooltipStyle = {
    backgroundColor: theme.bg,
    border: `1px solid ${theme.border}`,
    borderRadius: '8px',
    padding: '8px 12px',
  };

  const renderChart = () => {
    switch (data.chart_type) {
      case 'bar':
        return (
          <BarChart {...commonChartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis
              dataKey={data.x_axis}
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
            />
            <YAxis
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar
              dataKey={data.y_axis}
              fill={CHART_COLORS[0]}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        );

      case 'line':
        return (
          <LineChart {...commonChartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis
              dataKey={data.x_axis}
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
            />
            <YAxis
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey={data.y_axis}
              stroke={CHART_COLORS[0]}
              strokeWidth={2}
              dot={{ fill: CHART_COLORS[0], strokeWidth: 2 }}
              activeDot={{ r: 6, fill: CHART_COLORS[0] }}
            />
          </LineChart>
        );

      case 'pie':
        return (
          <PieChart>
            <Pie
              data={data.data}
              dataKey={data.y_axis}
              nameKey={data.x_axis}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${name}: ${(percent * 100).toFixed(0)}%`
              }
              labelLine={{ stroke: theme.axis }}
            >
              {data.data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend
              wrapperStyle={{ color: theme.text }}
            />
          </PieChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="my-4 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
      {data.title && (
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
          {data.title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={280}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
```

#### Step 5.4: Create Export File

**File**: `/frontend/src/components/charts/index.ts` (NEW)

```typescript
export { DataVisualization } from './DataVisualization';
export { CHART_COLORS, getThemeColors, formatValue } from './chartConfig';
```

---

### Phase 6: Integrate into MessageBubble

**File**: `/frontend/src/components/MessageBubble.tsx`

#### Step 6.1: Add Import

Add at the top with other imports:

```typescript
import { DataVisualization } from './charts';
```

#### Step 6.2: Render Visualization

In the assistant message section (after line 37, before ReactMarkdown), add:

```typescript
{/* Visualization - rendered before text explanation */}
{message.visualization && (
  <DataVisualization data={message.visualization} />
)}
```

The full assistant message section becomes:

```typescript
return (
  <div className="flex gap-4 max-w-4xl">
    {/* AI Avatar */}
    <div className="size-10 rounded-lg bg-primary/10 dark:bg-primary/20 flex-shrink-0 flex items-center justify-center">
      <span className="material-symbols-outlined text-2xl text-primary">auto_awesome</span>
    </div>
    {/* Message Content */}
    <div className="flex flex-col gap-1.5 flex-1 min-w-0">
      <p className="text-sm font-bold text-primary">InsightAgent</p>

      {/* Visualization - rendered before text explanation */}
      {message.visualization && (
        <DataVisualization data={message.visualization} />
      )}

      <div className="space-y-4 prose prose-slate dark:prose-invert max-w-none">
        <ReactMarkdown ...>
          {message.content}
        </ReactMarkdown>
        {/* Streaming indicator */}
        {message.isStreaming && (
          <div className="flex items-center gap-2 text-sm text-primary">
            <span className="material-symbols-outlined text-base animate-spin-slow">
              progress_activity
            </span>
            <span>Generating response...</span>
          </div>
        )}
      </div>
    </div>
  </div>
);
```

---

## Files Summary

### Backend Files to Modify

| File | Changes |
|------|---------|
| `/backend/app/agent/insight_agent.py` | Add `_should_visualize()`, `_select_chart_type()`, `_generate_chart_title()` methods; emit `visualization` SSE event |

### Frontend Files to Modify

| File | Changes |
|------|---------|
| `/frontend/package.json` | Add `recharts` dependency (via npm install) |
| `/frontend/src/types/api.ts` | Add `VisualizationData`, `VisualizationEvent` types; update `SSEEventType`, `ChatMessage` |
| `/frontend/src/services/api.ts` | Add `onVisualization` callback; handle `visualization` event |
| `/frontend/src/context/ChatContext.tsx` | Add `SET_VISUALIZATION` action and reducer case; add callback handler |
| `/frontend/src/components/MessageBubble.tsx` | Import and render `DataVisualization` component |

### New Frontend Files to Create

| File | Purpose |
|------|---------|
| `/frontend/src/components/charts/chartConfig.ts` | Theme colors, formatting utilities |
| `/frontend/src/components/charts/DataVisualization.tsx` | Main chart container component |
| `/frontend/src/components/charts/index.ts` | Export barrel file |

---

## Verification Plan

### 1. Backend Unit Tests

Run existing tests to ensure no regressions:
```bash
source backend/.venv/bin/activate
pytest tests/
```

### 2. Manual End-to-End Testing

Start the application:
```bash
# Terminal 1: Backend
cd backend
source .venv/bin/activate
uvicorn app.main:app --reload --port 8080

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 3. Test Scenarios

| Query | Expected Chart | Verification |
|-------|----------------|--------------|
| "What was Q4 revenue by region?" | Bar chart (4 bars) | Regions on x-axis, revenue on y-axis |
| "Show quarterly revenue for 2024" | Line chart | Quarters on x-axis, trend line visible |
| "Customer segment breakdown" | Pie chart | Segments as slices with percentages |
| "What was total Q4 revenue?" | No chart | Single value, not visualizable |
| "List all transactions" | No chart | Too many rows (>20) |

### 4. Dark Mode Testing

This repo uses Tailwind `darkMode: "class"`. If/when a `dark` class toggle exists on `<html>`, verify:
1. Chart colors adapt (axes, grid, tooltip background)
2. Text remains readable

### 5. Responsive Testing

1. Resize browser window
2. Verify charts scale appropriately
3. Check mobile view (chart should remain visible)

---

## Future Enhancements

1. **Multiple series**: Support grouped bar charts for comparing metrics
2. **Interactive drilldown**: Click chart element to ask follow-up question
3. **Chart type override**: Let user request specific chart type
4. **Download as image**: Export chart as PNG
5. **Animation**: Add enter animations for chart elements

---

## Open Questions / Scope Decisions

1. **Persistence (decision)**: **Live-only**. Do not persist charts to Firestore or hydrate them from `/chat/history`.
2. **Multiple BigQuery calls (decision, minimal effort)**: **Single chart per assistant message**. If multiple `visualization` events are emitted during one assistant response, the **latest one wins** (frontend overwrites `message.visualization`).

---

*Document created: 2026-02-01*
