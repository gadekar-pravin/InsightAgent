/**
 * Chat context for managing global chat state.
 */

import {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useRef,
  type ReactNode,
} from 'react';
import { v4 as uuidv4 } from 'uuid';
import {
  createSession,
  sendMessage,
  getConversationHistory,
  type SSECallback,
} from '../services/api';
import type {
  ChatMessage,
  ReasoningTrace,
  SessionResponse,
  GeminiUsageSummary,
  GeminiUsageCall,
  GeminiSessionTotals,
} from '../types/api';

// =============================================================================
// State Types
// =============================================================================

interface ChatState {
  sessionId: string | null;
  userId: string;
  hasMemory: boolean;
  messages: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  suggestedFollowups: string[];
  currentReasoningTraces: ReasoningTrace[];
  geminiTotals: GeminiSessionTotals;
  seenGeminiCallKeys: Set<string>;
}

type ChatAction =
  | { type: 'SET_SESSION'; payload: SessionResponse }
  | { type: 'RESUME_SESSION'; payload: { sessionId: string; userId: string } }
  | { type: 'LOAD_HISTORY'; payload: { messages: ChatMessage[]; geminiTotals: GeminiSessionTotals; seenGeminiCallKeys: Set<string> } }
  | { type: 'ADD_USER_MESSAGE'; payload: ChatMessage }
  | { type: 'ADD_ASSISTANT_MESSAGE'; payload: ChatMessage }
  | { type: 'UPDATE_ASSISTANT_CONTENT'; payload: string }
  | { type: 'ADD_REASONING_TRACE'; payload: ReasoningTrace }
  | { type: 'UPDATE_REASONING_TRACE'; payload: ReasoningTrace }
  | { type: 'APPLY_GEMINI_USAGE'; payload: GeminiUsageSummary | undefined }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_FOLLOWUPS'; payload: string[] }
  | { type: 'COMPLETE_MESSAGE' }
  | { type: 'CLEAR_TRACES' }
  | { type: 'RESET' };

// =============================================================================
// Reducer
// =============================================================================

const EMPTY_GEMINI_TOTALS: GeminiSessionTotals = {
  calls: 0,
  total_latency_ms: 0,
  prompt_token_count: null,
  candidates_token_count: null,
  total_token_count: null,
  thoughts_token_count: null,
  cached_content_token_count: null,
  tool_use_prompt_token_count: null,
};

function getGeminiCallKey(call: GeminiUsageCall): string {
  if (call.response_id) return call.response_id;
  return `${call.model_version || 'unknown'}:${call.iteration}`;
}

function sumMaybe(current: number | null, incoming: unknown): number | null {
  if (typeof incoming !== 'number' || !Number.isFinite(incoming)) return current;
  const value = Math.trunc(incoming);
  return (current ?? 0) + value;
}

function applyGeminiUsage(
  totals: GeminiSessionTotals,
  seenKeys: Set<string>,
  usage: GeminiUsageSummary
): { totals: GeminiSessionTotals; seenKeys: Set<string> } {
  if (!usage?.per_call || !Array.isArray(usage.per_call)) {
    return { totals, seenKeys };
  }

  let nextTotals = totals;
  let nextSeen = seenKeys;

  for (const call of usage.per_call) {
    const key = getGeminiCallKey(call);
    if (nextSeen.has(key)) continue;

    nextSeen = new Set(nextSeen);
    nextSeen.add(key);

    const callUsage = call.usage || {};
    nextTotals = {
      calls: nextTotals.calls + 1,
      total_latency_ms: nextTotals.total_latency_ms + (call.latency_ms || 0),
      prompt_token_count: sumMaybe(nextTotals.prompt_token_count, callUsage.prompt_token_count),
      candidates_token_count: sumMaybe(nextTotals.candidates_token_count, callUsage.candidates_token_count),
      total_token_count: sumMaybe(nextTotals.total_token_count, callUsage.total_token_count),
      thoughts_token_count: sumMaybe(nextTotals.thoughts_token_count, callUsage.thoughts_token_count),
      cached_content_token_count: sumMaybe(nextTotals.cached_content_token_count, callUsage.cached_content_token_count),
      tool_use_prompt_token_count: sumMaybe(nextTotals.tool_use_prompt_token_count, callUsage.tool_use_prompt_token_count),
    };
  }

  return { totals: nextTotals, seenKeys: nextSeen };
}

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_SESSION':
      return {
        ...state,
        sessionId: action.payload.session_id,
        userId: action.payload.user_id,
        hasMemory: action.payload.has_memory,
      };

    case 'RESUME_SESSION':
      return {
        ...state,
        sessionId: action.payload.sessionId,
        userId: action.payload.userId,
      };

    case 'LOAD_HISTORY':
      return {
        ...state,
        messages: action.payload.messages,
        isLoading: false,
        error: null,
        suggestedFollowups: [],
        currentReasoningTraces: [],
        geminiTotals: action.payload.geminiTotals,
        seenGeminiCallKeys: action.payload.seenGeminiCallKeys,
      };

    case 'ADD_USER_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
        isLoading: true,
        error: null,
        suggestedFollowups: [],
        currentReasoningTraces: [],
      };

    case 'ADD_ASSISTANT_MESSAGE':
      return {
        ...state,
        messages: [...state.messages, action.payload],
      };

    case 'UPDATE_ASSISTANT_CONTENT': {
      const messages = [...state.messages];
      const lastMessage = messages[messages.length - 1];
      if (lastMessage?.role === 'assistant') {
        messages[messages.length - 1] = {
          ...lastMessage,
          content: lastMessage.content + action.payload,
        };
      }
      return { ...state, messages };
    }

    case 'ADD_REASONING_TRACE':
      return {
        ...state,
        currentReasoningTraces: [...state.currentReasoningTraces, action.payload],
      };

    case 'UPDATE_REASONING_TRACE': {
      const traces = state.currentReasoningTraces.map((t) =>
        t.trace_id === action.payload.trace_id
          ? { ...t, ...action.payload, input: action.payload.input ?? t.input }  // Preserve input from started event
          : t
      );
      return { ...state, currentReasoningTraces: traces };
    }

    case 'APPLY_GEMINI_USAGE': {
      if (!action.payload) return state;
      const { totals, seenKeys } = applyGeminiUsage(state.geminiTotals, state.seenGeminiCallKeys, action.payload);
      return { ...state, geminiTotals: totals, seenGeminiCallKeys: seenKeys };
    }

    case 'SET_LOADING':
      return { ...state, isLoading: action.payload };

    case 'SET_ERROR':
      return { ...state, error: action.payload, isLoading: false };

    case 'SET_FOLLOWUPS':
      return { ...state, suggestedFollowups: action.payload };

    case 'COMPLETE_MESSAGE': {
      const messages = [...state.messages];
      const lastMessage = messages[messages.length - 1];
      if (lastMessage?.role === 'assistant') {
        messages[messages.length - 1] = {
          ...lastMessage,
          isStreaming: false,
          // Use current state traces, not stale closure value
          reasoning_trace: state.currentReasoningTraces,
        };
      }
      return {
        ...state,
        messages,
        isLoading: false,
      };
    }

    case 'CLEAR_TRACES':
      return { ...state, currentReasoningTraces: [] };

    case 'RESET':
      return {
        ...initialState,
        userId: state.userId,
      };

    default:
      return state;
  }
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: ChatState = {
  sessionId: null,
  userId: 'demo_user', // Default user for demo
  hasMemory: false,
  messages: [],
  isLoading: false,
  error: null,
  suggestedFollowups: [],
  currentReasoningTraces: [],
  geminiTotals: EMPTY_GEMINI_TOTALS,
  seenGeminiCallKeys: new Set<string>(),
};

// =============================================================================
// Context
// =============================================================================

interface ChatContextValue extends ChatState {
  initSession: () => Promise<void>;
  sendChatMessage: (content: string) => void;
  cancelStream: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

export function ChatProvider({ children }: { children: ReactNode }) {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const abortControllerRef = useRef<AbortController | null>(null);
  const sessionInitRef = useRef(false);

  const sessionStorageKey = `insightagent_session_id:${state.userId}`;

  // Initialize session (guards against StrictMode double-invoke)
  const initSession = useCallback(async () => {
    // Prevent duplicate session creation in React StrictMode
    if (sessionInitRef.current || state.sessionId) return;
    sessionInitRef.current = true;

    try {
      const storedSessionId = window.localStorage.getItem(sessionStorageKey);
      if (storedSessionId) {
        try {
          const history = await getConversationHistory(storedSessionId, state.userId);

          const messages: ChatMessage[] = history.messages.map((m) => ({
            id: m.message_id || uuidv4(),
            role: m.role,
            content: m.content,
            timestamp: new Date(m.timestamp),
            reasoning_trace: m.reasoning_trace,
            isStreaming: false,
          }));

          let geminiTotals: GeminiSessionTotals = EMPTY_GEMINI_TOTALS;
          let seenGeminiCallKeys = new Set<string>();

          for (const m of history.messages) {
            const usage = m.metadata?.gemini_usage;
            if (!usage || !Array.isArray(usage.per_call)) continue;
            const merged = applyGeminiUsage(geminiTotals, seenGeminiCallKeys, usage);
            geminiTotals = merged.totals;
            seenGeminiCallKeys = merged.seenKeys;
          }

          dispatch({ type: 'RESUME_SESSION', payload: { sessionId: storedSessionId, userId: state.userId } });
          dispatch({ type: 'LOAD_HISTORY', payload: { messages, geminiTotals, seenGeminiCallKeys } });
          return;
        } catch {
          window.localStorage.removeItem(sessionStorageKey);
        }
      }

      const session = await createSession({ user_id: state.userId });
      window.localStorage.setItem(sessionStorageKey, session.session_id);
      dispatch({ type: 'SET_SESSION', payload: session });
    } catch (error) {
      sessionInitRef.current = false; // Allow retry on error
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Failed to create session',
      });
    }
  }, [state.userId, state.sessionId, sessionStorageKey]);

  // Send chat message with SSE streaming
  const sendChatMessage = useCallback(
    (content: string) => {
      if (!state.sessionId || state.isLoading) return;

      // Add user message
      const userMessage: ChatMessage = {
        id: uuidv4(),
        role: 'user',
        content,
        timestamp: new Date(),
      };
      dispatch({ type: 'ADD_USER_MESSAGE', payload: userMessage });

      // Add empty assistant message for streaming
      const assistantMessage: ChatMessage = {
        id: uuidv4(),
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      };
      dispatch({ type: 'ADD_ASSISTANT_MESSAGE', payload: assistantMessage });

      // SSE callbacks
      const callbacks: SSECallback = {
        onReasoning: (event) => {
          if (event.status === 'started') {
            dispatch({
              type: 'ADD_REASONING_TRACE',
              payload: {
                trace_id: event.trace_id,
                tool_name: event.tool_name,
                status: event.status,
                input: event.input,
                timestamp: Date.now(),
              },
            });
          } else {
            dispatch({
              type: 'UPDATE_REASONING_TRACE',
              payload: {
                trace_id: event.trace_id,
                tool_name: event.tool_name,
                status: event.status,
                input: event.input,
                summary: event.summary,
                error: event.error,
                timestamp: Date.now(),
              },
            });
          }
        },
        onContent: (event) => {
          dispatch({ type: 'UPDATE_ASSISTANT_CONTENT', payload: event.delta });
        },
        onMemory: () => {
          // Could show toast notification here
        },
        onDone: (event) => {
          dispatch({ type: 'APPLY_GEMINI_USAGE', payload: event.gemini_usage });
          dispatch({ type: 'SET_FOLLOWUPS', payload: event.suggested_followups });
          dispatch({ type: 'COMPLETE_MESSAGE' });
        },
        onError: (event) => {
          dispatch({ type: 'SET_ERROR', payload: event.error });
        },
        onHeartbeat: () => {
          // Connection is alive
        },
      };

      // Start SSE stream
      abortControllerRef.current = sendMessage(
        {
          session_id: state.sessionId,
          user_id: state.userId,
          content,
        },
        callbacks
      );
    },
    [state.sessionId, state.userId, state.isLoading]
  );

  // Cancel ongoing stream
  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
    dispatch({ type: 'SET_LOADING', payload: false });
  }, []);

  const value: ChatContextValue = {
    ...state,
    initSession,
    sendChatMessage,
    cancelStream,
  };

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error('useChat must be used within a ChatProvider');
  }
  return context;
}
