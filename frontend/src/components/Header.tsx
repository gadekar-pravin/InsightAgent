/**
 * Top navigation header component.
 */

interface HeaderProps {
  hasMemory?: boolean;
  memorySavedCount?: number;
}

export function Header({ hasMemory = false, memorySavedCount = 0 }: HeaderProps) {
  return (
    <header className="h-16 border-b border-slate-200 dark:border-slate-800 bg-white/80 dark:bg-[#16222c]/80 backdrop-blur-md flex items-center justify-between px-6 z-10 shrink-0">
      <div className="flex items-center gap-4">
        <img
          src="/assets/PGlogo.png"
          alt="P&G Logo"
          className="h-10 w-10 rounded-lg object-contain"
        />
        <h2 className="text-xl font-bold leading-tight tracking-tight">
          InsightAgent
        </h2>
        <span className="text-slate-400 dark:text-slate-500 mx-2">|</span>
        <span className="text-sm font-medium text-slate-600 dark:text-slate-300">
          Internal Demo by LTI
        </span>
      </div>
      <div className="flex items-center gap-3">
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
