/**
 * Main chat area component with messages, input, and followups.
 */

import { useEffect, useRef } from 'react';
import { MessageBubble } from './MessageBubble';
import { ChatInput } from './ChatInput';
import { SuggestedFollowups } from './SuggestedFollowups';
import { WelcomeScreen } from './WelcomeScreen';
import type { ChatMessage } from '../types/api';

interface ChatAreaProps {
  messages: ChatMessage[];
  suggestedFollowups: string[];
  isLoading: boolean;
  onSendMessage: (message: string) => void;
}

export function ChatArea({
  messages,
  suggestedFollowups,
  isLoading,
  onSendMessage,
}: ChatAreaProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const hasMessages = messages.length > 0;

  return (
    <main className="flex-1 flex flex-col relative overflow-hidden bg-slate-50 dark:bg-slate-900/20">
      {/* Messages area */}
      {hasMessages ? (
        <>
          <div className="flex-1 overflow-y-auto p-8 space-y-8 scroll-smooth">
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}
            <div ref={messagesEndRef} />
          </div>

          {/* Footer with chips and input - only for messages view */}
          <div className="p-4 pb-6 bg-white dark:bg-[#16222c] border-t border-slate-200 dark:border-slate-800 space-y-3 shrink-0">
            {suggestedFollowups.length > 0 && (
              <SuggestedFollowups
                followups={suggestedFollowups}
                onSelect={onSendMessage}
                disabled={isLoading}
              />
            )}
            <div className="max-w-[800px] mx-auto">
              <ChatInput
                onSend={onSendMessage}
                isLoading={isLoading}
                placeholder="Ask a follow-up question..."
              />
            </div>
          </div>
        </>
      ) : (
        /* Welcome screen with integrated input */
        <div className="flex-1 flex flex-col items-center justify-center overflow-y-auto px-4 py-8">
          <WelcomeScreen onQuestionClick={onSendMessage} />

          {/* Input integrated into welcome flow */}
          <div className="w-full max-w-[700px] px-6">
            <p className="text-center text-sm text-slate-500 dark:text-slate-400 mb-3 flex items-center justify-center gap-2">
              <span className="material-symbols-outlined text-base">keyboard</span>
              Or type your own question
            </p>
            <ChatInput
              onSend={onSendMessage}
              isLoading={isLoading}
              placeholder="Ask anything about your business data..."
            />
          </div>
        </div>
      )}
    </main>
  );
}
