/**
 * Reasoning trace panel showing AI tool calls in real-time.
 */

import type { ReasoningTrace } from '../types/api';

interface ReasoningPanelProps {
  traces: ReasoningTrace[];
  isProcessing?: boolean;
}

// Tool name to friendly label mapping
const TOOL_LABELS: Record<string, { label: string; icon: string }> = {
  query_bigquery: { label: 'Querying BigQuery', icon: 'database' },
  search_knowledge_base: { label: 'Searching knowledge base', icon: 'search' },
  get_conversation_context: { label: 'Loading context', icon: 'memory' },
  save_to_memory: { label: 'Saving insight', icon: 'bookmark' },
};

function getToolDisplay(toolName: string) {
  return (
    TOOL_LABELS[toolName] || { label: toolName.replace(/_/g, ' '), icon: 'smart_toy' }
  );
}

function ReasoningTraceItem({ trace, isLast }: { trace: ReasoningTrace; isLast: boolean }) {
  const { label, icon } = getToolDisplay(trace.tool_name);
  const isActive = trace.status === 'started';
  const isError = trace.status === 'error';
  const isComplete = trace.status === 'completed';

  // Check if input looks like SQL
  const isSqlInput = trace.tool_name === 'query_bigquery' && trace.input;

  return (
    <div className="relative flex gap-4">
      {/* Connector line */}
      {!isLast && <div className="reasoning-line" />}

      {/* Status icon */}
      <div
        className={`relative z-10 size-6 rounded-full flex items-center justify-center shrink-0 ${
          isError
            ? 'bg-red-500 text-white'
            : isComplete
            ? 'bg-green-500 text-white'
            : 'bg-primary/20 text-primary'
        }`}
      >
        {isActive ? (
          <span className="material-symbols-outlined text-base animate-spin-slow">
            progress_activity
          </span>
        ) : isError ? (
          <span className="material-symbols-outlined text-base">close</span>
        ) : (
          <span className="material-symbols-outlined text-base">check</span>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-6 min-w-0">
        <h4
          className={`text-xs font-bold ${
            isActive
              ? 'text-primary'
              : isError
              ? 'text-red-500'
              : 'text-[#0d141b] dark:text-slate-100'
          }`}
        >
          <span className="material-symbols-outlined text-sm mr-1 align-middle">
            {icon}
          </span>
          {label}
        </h4>

        {/* Input display - SQL or search query */}
        {trace.input && (
          <div className={`mt-2 ${isSqlInput ? 'bg-slate-900 dark:bg-slate-950' : 'bg-slate-100 dark:bg-slate-800'} rounded-md p-2 overflow-hidden`}>
            <pre className={`text-[10px] font-mono whitespace-pre-wrap break-all ${isSqlInput ? 'text-green-400' : 'text-slate-600 dark:text-slate-300'}`}>
              {trace.input}
            </pre>
          </div>
        )}

        {/* Summary on completion */}
        {trace.summary && isComplete && (
          <div className="mt-2 flex items-start gap-1.5">
            <span className="material-symbols-outlined text-green-500 text-sm shrink-0">
              arrow_forward
            </span>
            <p className="text-[11px] text-slate-600 dark:text-slate-400">
              {trace.summary}
            </p>
          </div>
        )}

        {/* Error message */}
        {trace.error && (
          <div className="mt-2 flex items-start gap-1.5">
            <span className="material-symbols-outlined text-red-500 text-sm shrink-0">
              error
            </span>
            <p className="text-[11px] text-red-500">{trace.error}</p>
          </div>
        )}

        {/* Progress bar for active */}
        {isActive && (
          <div className="mt-2 w-full bg-slate-200 dark:bg-slate-700 h-1 rounded-full overflow-hidden">
            <div
              className="bg-primary h-full rounded-full animate-[pulse_1.5s_ease-in-out_infinite]"
              style={{ width: '70%' }}
            />
          </div>
        )}
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center p-6 text-center">
      <div className="w-full flex flex-col items-center gap-5 rounded-2xl bg-slate-50/50 dark:bg-slate-800/30 px-6 py-12">
        <div className="w-14 h-14 bg-primary/10 rounded-full flex items-center justify-center text-primary">
          <span className="material-symbols-outlined text-3xl">psychology</span>
        </div>
        <div className="flex max-w-[280px] flex-col items-center gap-3">
          <p className="text-[#0d141b] dark:text-slate-200 text-base font-bold leading-tight tracking-tight">
            Step-by-step analysis
          </p>
          <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal">
            Watch the AI work in real-time:
          </p>
          <ul className="text-left text-xs text-slate-500 dark:text-slate-400 space-y-1.5 mt-1">
            <li className="flex items-center gap-2">
              <span className="material-symbols-outlined text-green-500 text-sm">
                check_circle
              </span>
              <span>Query your sales database</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="material-symbols-outlined text-green-500 text-sm">
                check_circle
              </span>
              <span>Search company policies</span>
            </li>
            <li className="flex items-center gap-2">
              <span className="material-symbols-outlined text-green-500 text-sm">
                check_circle
              </span>
              <span>Generate insights</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export function ReasoningPanel({ traces, isProcessing = false }: ReasoningPanelProps) {
  const hasTraces = traces.length > 0;

  return (
    <aside className="w-80 border-l border-slate-200 dark:border-slate-800 bg-white dark:bg-[#16222c] flex-col hidden lg:flex h-full">
      {/* Header */}
      <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex justify-between items-center shrink-0">
        <h3 className="font-bold text-sm tracking-tight flex items-center gap-2">
          <span className="material-symbols-outlined text-primary text-lg">
            psychology
          </span>
          Reasoning Trace
        </h3>
        {isProcessing && (
          <span className="material-symbols-outlined text-primary text-lg animate-spin-slow">
            progress_activity
          </span>
        )}
      </div>

      {/* Trace content */}
      {hasTraces ? (
        <div className="flex-1 overflow-y-auto p-6 space-y-0 relative">
          {traces.map((trace, idx) => (
            <ReasoningTraceItem
              key={trace.trace_id}
              trace={trace}
              isLast={idx === traces.length - 1}
            />
          ))}
        </div>
      ) : (
        <EmptyState />
      )}

      {/* Footer */}
      <div className="p-4 bg-slate-50 dark:bg-slate-900/50 border-t border-slate-200 dark:border-slate-800 shrink-0">
        <div className="flex items-start gap-3">
          <span className="material-symbols-outlined text-slate-400">
            auto_awesome
          </span>
          <div>
            <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
              AI Transparency
            </p>
            <p className="text-xs text-slate-400 mt-1">
              This panel shows which SQL queries were executed and how the AI
              interpreted the raw data results.
            </p>
          </div>
        </div>
      </div>
    </aside>
  );
}
