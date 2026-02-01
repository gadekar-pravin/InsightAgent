/**
 * Skeleton placeholder that mimics the MessageBubble layout for assistant messages.
 * Displays while waiting for the AI to start responding.
 */

export function MessageSkeleton() {
  return (
    <div className="flex gap-4 max-w-4xl animate-pulse">
      {/* Avatar placeholder */}
      <div className="size-10 rounded-lg bg-slate-200 dark:bg-slate-700 flex-shrink-0" />

      {/* Content placeholder */}
      <div className="flex flex-col gap-3 flex-1 min-w-0">
        {/* Name placeholder */}
        <div className="h-4 w-24 bg-slate-200 dark:bg-slate-700 rounded" />

        {/* Text line placeholders */}
        <div className="space-y-2.5">
          <div className="h-4 w-full bg-slate-200 dark:bg-slate-700 rounded" />
          <div className="h-4 w-[85%] bg-slate-200 dark:bg-slate-700 rounded" />
          <div className="h-4 w-[60%] bg-slate-200 dark:bg-slate-700 rounded" />
        </div>
      </div>
    </div>
  );
}
