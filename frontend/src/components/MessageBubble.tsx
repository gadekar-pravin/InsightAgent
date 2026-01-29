/**
 * Chat message bubble component.
 */

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { ChatMessage } from '../types/api';

interface MessageBubbleProps {
  message: ChatMessage;
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  if (isUser) {
    return (
      <div className="flex gap-4 max-w-3xl ml-auto justify-end">
        <div className="flex flex-col gap-1.5 items-end">
          <p className="text-sm font-bold opacity-60">You</p>
          <div className="bg-blue-500/90 text-white p-4 rounded-xl rounded-tr-none shadow-sm">
            <p className="text-base leading-relaxed font-medium">{message.content}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-4 max-w-4xl">
      {/* AI Avatar */}
      <div className="size-10 rounded-lg bg-primary/10 dark:bg-primary/20 flex-shrink-0 flex items-center justify-center">
        <svg
          className="size-6 text-primary"
          fill="none"
          viewBox="0 0 48 48"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M6 6H42L36 24L42 42H6L12 24L6 6Z"
            fill="currentColor"
          />
        </svg>
      </div>
      {/* Message Content */}
      <div className="flex flex-col gap-1.5 flex-1 min-w-0">
        <p className="text-sm font-bold text-primary">InsightAgent</p>
        <div className="space-y-4 prose prose-slate dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom table styling
              table: ({ children }) => (
                <div className="overflow-hidden rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-[#1a2632] shadow-sm not-prose">
                  <table className="w-full text-left border-collapse">
                    {children}
                  </table>
                </div>
              ),
              thead: ({ children }) => (
                <thead className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-700">
                  {children}
                </thead>
              ),
              th: ({ children }) => (
                <th className="px-4 py-3 text-xs font-bold uppercase tracking-wider text-slate-500">
                  {children}
                </th>
              ),
              td: ({ children }) => (
                <td className="px-4 py-4 text-sm">{children}</td>
              ),
              tr: ({ children }) => (
                <tr className="border-t border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors">
                  {children}
                </tr>
              ),
              // Custom list styling
              ul: ({ children }) => (
                <ul className="space-y-1.5 list-none">{children}</ul>
              ),
              li: ({ children }) => (
                <li className="flex items-start gap-2 text-sm">
                  <span className="text-primary mt-1 text-xs">•</span>
                  <span>{children}</span>
                </li>
              ),
              // Custom paragraph styling
              p: ({ children }) => (
                <p className="text-base leading-relaxed">{children}</p>
              ),
              // Custom strong styling
              strong: ({ children }) => (
                <strong className="font-semibold">{children}</strong>
              ),
            }}
          >
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
}
