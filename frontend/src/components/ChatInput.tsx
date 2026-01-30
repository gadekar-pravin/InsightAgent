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
      {/* Gradient glow effect behind input */}
      <div className="absolute -inset-1 bg-gradient-to-r from-primary/20 via-blue-500/20 to-primary/20 rounded-2xl blur-sm opacity-60 animate-pulse" />

      <div className="relative flex items-center gap-3 bg-white dark:bg-slate-800 rounded-xl border-2 border-primary/30 dark:border-primary/40 p-3 shadow-lg shadow-primary/10">
        <span className="material-symbols-outlined text-primary/60 ml-1">
          auto_awesome
        </span>
        <input
          type="text"
          value={input}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          disabled={isLoading}
          maxLength={maxLength}
          placeholder={placeholder}
          className="flex-1 bg-transparent border-none focus:ring-0 focus:outline-none text-[#0d141b] dark:text-white placeholder:text-slate-400 py-3 px-2 text-base disabled:opacity-50"
        />
        <span className="text-xs text-slate-400 mr-2 whitespace-nowrap hidden sm:inline">
          {input.length.toLocaleString()} / {maxLength.toLocaleString()}
        </span>
        <button
          onClick={handleSend}
          disabled={!input.trim() || isLoading}
          className="bg-primary text-white p-3 rounded-lg flex items-center justify-center hover:bg-primary/90 transition-all hover:scale-105 disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
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
