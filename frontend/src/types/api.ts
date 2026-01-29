/**
 * API types for InsightAgent frontend.
 * Mirrors backend Pydantic models.
 */

// =============================================================================
// Session Types
// =============================================================================

export interface SessionCreate {
  user_id: string;
}

export interface SessionResponse {
  session_id: string;
  user_id: string;
  created_at: string;
  has_memory: boolean;
}

// =============================================================================
// Message Types
// =============================================================================

export interface MessageRequest {
  session_id: string;
  user_id: string;
  content: string;
}

export interface MessageResponse {
  session_id: string;
  content: string;
  reasoning_trace: ReasoningTrace[];
  memory_saved: MemorySave[];
  suggested_followups: string[];
}

// =============================================================================
// SSE Event Types
// =============================================================================

export type SSEEventType = 'reasoning' | 'content' | 'memory' | 'heartbeat' | 'done' | 'error';

export interface ReasoningEvent {
  seq: number;
  trace_id: string;
  tool_name: string;
  status: 'started' | 'completed' | 'error';
  summary?: string;
  error?: string;
}

export interface ContentEvent {
  seq: number;
  delta: string;
}

export interface MemoryEvent {
  seq: number;
  memory_type: string;
  key: string;
  value: string;
}

export interface DoneEvent {
  seq: number;
  suggested_followups: string[];
}

export interface ErrorEvent {
  error: string;
  detail?: string;
}

// =============================================================================
// History Types
// =============================================================================

export interface HistoryMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  reasoning_trace?: ReasoningTrace[];
}

export interface ConversationHistory {
  session_id: string;
  user_id: string;
  messages: HistoryMessage[];
  created_at: string;
  last_updated: string;
}

// =============================================================================
// Memory Types
// =============================================================================

export interface MemoryItem {
  key: string;
  value: string;
  memory_type: 'finding' | 'preference' | 'context';
  created_at: string;
  session_id?: string;
}

export interface UserMemory {
  user_id: string;
  summary?: string;
  preferences: Record<string, unknown>;
  findings: Record<string, unknown>;
  recent_sessions: Array<Record<string, unknown>>;
  last_updated?: string;
}

export interface MemoryResetResponse {
  success: boolean;
  message: string;
}

// =============================================================================
// Internal UI Types
// =============================================================================

export interface ReasoningTrace {
  trace_id: string;
  tool_name: string;
  status: 'started' | 'completed' | 'error';
  summary?: string;
  error?: string;
  timestamp: number;
}

export interface MemorySave {
  memory_type: string;
  key: string;
  value: string;
}

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  reasoning_trace?: ReasoningTrace[];
  isStreaming?: boolean;
}

export interface ChatState {
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  suggestedFollowups: string[];
  currentReasoningTraces: ReasoningTrace[];
}
