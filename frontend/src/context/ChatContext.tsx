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
  type SSECallback,
} from '../services/api';
import type {
  ChatMessage,
  ReasoningTrace,
  SessionResponse,
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
}

type ChatAction =
  | { type: 'SET_SESSION'; payload: SessionResponse }
  | { type: 'ADD_USER_MESSAGE'; payload: ChatMessage }
  | { type: 'ADD_ASSISTANT_MESSAGE'; payload: ChatMessage }
  | { type: 'UPDATE_ASSISTANT_CONTENT'; payload: string }
  | { type: 'ADD_REASONING_TRACE'; payload: ReasoningTrace }
  | { type: 'UPDATE_REASONING_TRACE'; payload: ReasoningTrace }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'SET_ERROR'; payload: string | null }
  | { type: 'SET_FOLLOWUPS'; payload: string[] }
  | { type: 'COMPLETE_MESSAGE' }
  | { type: 'CLEAR_TRACES' }
  | { type: 'RESET' };

// =============================================================================
// Reducer
// =============================================================================

function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case 'SET_SESSION':
      return {
        ...state,
        sessionId: action.payload.session_id,
        userId: action.payload.user_id,
        hasMemory: action.payload.has_memory,
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
          ? { ...t, ...action.payload }  // Merge to preserve input from started event
          : t
      );
      return { ...state, currentReasoningTraces: traces };
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
      return initialState;

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

  // Initialize session (guards against StrictMode double-invoke)
  const initSession = useCallback(async () => {
    // Prevent duplicate session creation in React StrictMode
    if (sessionInitRef.current || state.sessionId) return;
    sessionInitRef.current = true;

    try {
      const session = await createSession({ user_id: state.userId });
      dispatch({ type: 'SET_SESSION', payload: session });
    } catch (error) {
      sessionInitRef.current = false; // Allow retry on error
      dispatch({
        type: 'SET_ERROR',
        payload: error instanceof Error ? error.message : 'Failed to create session',
      });
    }
  }, [state.userId, state.sessionId]);

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
