/**
 * Top navigation header component.
 */

import type { GeminiSessionTotals } from '../types/api';

interface HeaderProps {
  hasMemory?: boolean;
  memorySavedCount?: number;
  geminiTotals?: GeminiSessionTotals;
  onNewChat?: () => void;
}

function formatCount(value: number | null | undefined): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—';
  return value.toLocaleString();
}

function formatLatency(ms: number, calls: number): string {
  if (!calls) return '—';
  if (!Number.isFinite(ms)) return '—';
  if (ms >= 1000) return `${(ms / 1000).toFixed(1)}s`;
  return `${Math.max(0, Math.trunc(ms))}ms`;
}

export function Header({
  hasMemory = false,
  memorySavedCount = 0,
  geminiTotals,
  onNewChat,
}: HeaderProps) {
  const usageTitle = geminiTotals
    ? [
        `Total tokens: ${formatCount(geminiTotals.total_token_count)}`,
        `Prompt: ${formatCount(geminiTotals.prompt_token_count)}`,
        `Candidates: ${formatCount(geminiTotals.candidates_token_count)}`,
        `Thoughts: ${formatCount(geminiTotals.thoughts_token_count)}`,
        `Tool prompt: ${formatCount(geminiTotals.tool_use_prompt_token_count)}`,
        `Cached: ${formatCount(geminiTotals.cached_content_token_count)}`,
        `Calls: ${formatCount(geminiTotals.calls)}`,
        `Latency: ${formatLatency(geminiTotals.total_latency_ms, geminiTotals.calls)}`,
      ].join('\n')
    : 'Gemini usage unavailable';

  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-[#16222c]/80 backdrop-blur-md flex items-center justify-between px-6 z-10 shrink-0">
      <div className="flex items-center gap-4">
        <button
          onClick={onNewChat}
          className="flex items-center gap-3 hover:opacity-80 transition-opacity"
          title="Back to home"
        >
          <img
            src="/assets/PGlogo.png"
            alt="P&G Logo"
            className="h-10 w-10 rounded-lg object-contain"
          />
          <h2 className="text-xl font-bold leading-tight tracking-tight">
            InsightAgent
          </h2>
        </button>
        <span className="text-xs font-medium px-2.5 py-1 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
          Internal Demo • LTIMindtree IMS
        </span>
      </div>
      <div className="flex items-center gap-3">
        {/* New Chat button */}
        {onNewChat && (
          <button
            onClick={onNewChat}
            className="flex items-center gap-1.5 px-3 py-1.5 text-sm font-semibold text-white bg-amber-500 hover:bg-amber-600 rounded-lg transition-colors shadow-sm"
            title="Start a new chat"
          >
            <span className="material-symbols-outlined text-base">add</span>
            <span className="hidden sm:inline">New Chat</span>
          </button>
        )}
        {/* Gemini usage (session total) */}
        <div
          className="hidden md:flex items-center gap-3 px-3 py-1.5 rounded-lg bg-slate-50 dark:bg-slate-900/40 border border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-200"
          title={usageTitle}
        >
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 dark:text-slate-400">Tokens</span>
            <span className="font-semibold">{formatCount(geminiTotals?.total_token_count ?? null)}</span>
          </div>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 dark:text-slate-400">Calls</span>
            <span className="font-semibold">{formatCount(geminiTotals?.calls ?? 0)}</span>
          </div>
          <span className="text-slate-300 dark:text-slate-700">|</span>
          <div className="flex items-center gap-1.5 text-xs">
            <span className="text-slate-500 dark:text-slate-400">Latency</span>
            <span className="font-semibold">
              {formatLatency(geminiTotals?.total_latency_ms ?? 0, geminiTotals?.calls ?? 0)}
            </span>
          </div>
        </div>

        {/* Memory indicator */}
        {hasMemory && (
          <button
            className="flex items-center gap-1.5 px-3 py-1.5 text-slate-600 dark:text-slate-400 rounded-lg text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            title={`${memorySavedCount} saved findings`}
          >
            <span className="material-symbols-outlined text-base">bookmark</span>
            <span className="hidden sm:inline text-xs">{memorySavedCount}</span>
            <span className="hidden md:inline text-xs">saved</span>
          </button>
        )}
        {/* History button */}
        <button
          className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          title="Session history"
        >
          <span className="material-symbols-outlined">history</span>
        </button>
        {/* User avatar */}
        <div
          className="h-10 w-10 rounded-full border-2 border-primary/20 bg-primary/10 flex items-center justify-center ml-2"
          title="Demo User"
        >
          <span className="material-symbols-outlined text-primary">person</span>
        </div>
      </div>
    </header>
  );
}
