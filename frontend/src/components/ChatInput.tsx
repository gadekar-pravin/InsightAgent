/**
 * Chat input component with send button and character counter.
 */

import { useState, useCallback, type KeyboardEvent, type ChangeEvent } from 'react';

interface ChatInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  placeholder?: string;
  maxLength?: number;
}

export function ChatInput({
  onSend,
  isLoading = false,
  placeholder = 'Ask InsightAgent a question about your sales data...',
  maxLength = 4000,
}: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      setInput(e.target.value);
    },
    []
  );

  const handleSend = useCallback(() => {
    const trimmed = input.trim();
    if (trimmed && !isLoading) {
      onSend(trimmed);
      setInput('');
    }
  }, [input, isLoading, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  return (
    <div className="relative">
      <div className="flex items-center gap-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-2 shadow-md">
        <input
          type="text"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          maxLength={maxLength}
          placeholder={placeholder}
          className="flex-1 bg-transparent border-none focus:ring-0 text-[#0d141b] dark:text-white placeholder:text-slate-400 py-3 px-3 text-base disabled:opacity-50"
        />
        <span className="text-xs text-slate-400 mr-2 whitespace-nowrap">
          {input.length.toLocaleString()} / {maxLength.toLocaleString()}
        </span>
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="bg-primary text-white p-3 rounded-lg flex items-center justify-center hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <span className="material-symbols-outlined animate-spin-slow">
              progress_activity
            </span>
          ) : (
            <span className="material-symbols-outlined">send</span>
          )}
        </button>
      </div>
      <p className="text-center text-[11px] text-slate-400 mt-3">
        InsightAgent can make mistakes. Check important info.
      </p>
    </div>
  );
}
