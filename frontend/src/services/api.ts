/**
 * API service for InsightAgent backend communication.
 */

import type {
  SessionCreate,
  SessionResponse,
  MessageRequest,
  ConversationHistory,
  UserMemory,
  MemoryResetResponse,
  SSEEventType,
  ReasoningEvent,
  ContentEvent,
  MemoryEvent,
  DoneEvent,
  ErrorEvent,
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
const API_KEY = import.meta.env.VITE_API_KEY || '';

/**
 * Get common headers for API requests.
 */
function getHeaders(): HeadersInit {
  const headers: HeadersInit = {
    'Content-Type': 'application/json',
  };
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }
  return headers;
}

/**
 * Generic fetch wrapper with error handling.
 */
async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      ...getHeaders(),
      ...options.headers,
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Unknown error' }));
    throw new Error(error.detail || error.error || `HTTP ${response.status}`);
  }

  return response.json();
}

// =============================================================================
// Session API
// =============================================================================

export async function createSession(data: SessionCreate): Promise<SessionResponse> {
  return apiFetch<SessionResponse>('/chat/session', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// =============================================================================
// Chat API (SSE Streaming)
// =============================================================================

export type SSECallback = {
  onReasoning?: (event: ReasoningEvent) => void;
  onContent?: (event: ContentEvent) => void;
  onMemory?: (event: MemoryEvent) => void;
  onDone?: (event: DoneEvent) => void;
  onError?: (event: ErrorEvent) => void;
  onHeartbeat?: () => void;
};

/**
 * Send a chat message and receive SSE stream.
 * Returns an AbortController to cancel the stream.
 */
export function sendMessage(
  data: MessageRequest,
  callbacks: SSECallback
): AbortController {
  const controller = new AbortController();

  // Start the fetch request
  fetch(`${API_BASE}/chat/message`, {
    method: 'POST',
    headers: getHeaders(),
    body: JSON.stringify(data),
    signal: controller.signal,
  })
    .then(async (response) => {
      if (!response.ok) {
        const error = await response.json().catch(() => ({ error: 'Unknown error' }));
        callbacks.onError?.({
          error: error.detail || error.error || `HTTP ${response.status}`,
        });
        return;
      }

      // Check if response is SSE
      const contentType = response.headers.get('content-type');
      if (!contentType?.startsWith('text/event-stream')) {
        callbacks.onError?.({
          error: 'Expected SSE stream but received different content type',
        });
        return;
      }

      const reader = response.body?.getReader();
      if (!reader) {
        callbacks.onError?.({ error: 'No response body' });
        return;
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Process complete events (split by double newline)
        const events = buffer.split('\n\n');
        buffer = events.pop() || ''; // Keep incomplete event in buffer

        for (const eventStr of events) {
          if (!eventStr.trim()) continue;

          // Parse SSE format: "event: type\ndata: json"
          const lines = eventStr.split('\n');
          let eventType: SSEEventType | null = null;
          let eventData = '';

          for (const line of lines) {
            if (line.startsWith('event: ')) {
              eventType = line.slice(7).trim() as SSEEventType;
            } else if (line.startsWith('data: ')) {
              eventData = line.slice(6);
            }
          }

          if (!eventType || !eventData) continue;

          try {
            const data = JSON.parse(eventData);

            switch (eventType) {
              case 'reasoning':
                callbacks.onReasoning?.(data as ReasoningEvent);
                break;
              case 'content':
                callbacks.onContent?.(data as ContentEvent);
                break;
              case 'memory':
                callbacks.onMemory?.(data as MemoryEvent);
                break;
              case 'done':
                callbacks.onDone?.(data as DoneEvent);
                break;
              case 'error':
                callbacks.onError?.(data as ErrorEvent);
                break;
              case 'heartbeat':
                callbacks.onHeartbeat?.();
                break;
            }
          } catch (e) {
            console.error('Failed to parse SSE event:', e, eventData);
          }
        }
      }
    })
    .catch((error) => {
      if (error.name !== 'AbortError') {
        callbacks.onError?.({ error: error.message || 'Network error' });
      }
    });

  return controller;
}

// =============================================================================
// History API
// =============================================================================

export async function getConversationHistory(
  sessionId: string,
  userId: string
): Promise<ConversationHistory> {
  return apiFetch<ConversationHistory>(
    `/chat/history/${sessionId}?user_id=${encodeURIComponent(userId)}`
  );
}

// =============================================================================
// Memory API
// =============================================================================

export async function getUserMemory(userId: string): Promise<UserMemory> {
  return apiFetch<UserMemory>(`/user/memory?user_id=${encodeURIComponent(userId)}`);
}

export async function resetUserMemory(userId: string): Promise<MemoryResetResponse> {
  return apiFetch<MemoryResetResponse>(
    `/user/memory/reset?user_id=${encodeURIComponent(userId)}`,
    { method: 'DELETE' }
  );
}

// =============================================================================
// Health Check
// =============================================================================

export async function healthCheck(): Promise<{ status: string }> {
  const response = await fetch('/health');
  return response.json();
}
