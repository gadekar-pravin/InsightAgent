/**
 * Clickable question card for the welcome screen.
 */

interface QuestionCardProps {
  icon: string;
  title: string;
  description: string;
  onClick: () => void;
}

export function QuestionCard({
  icon,
  title,
  description,
  onClick,
}: QuestionCardProps) {
  return (
    <button
      onClick={onClick}
      className="group flex items-start gap-3 p-3 bg-white dark:bg-slate-800 rounded-lg shadow-sm hover:shadow-md hover:ring-2 hover:ring-primary/20 transition-all cursor-pointer text-left w-full"
    >
      <div className="w-9 h-9 bg-blue-50 dark:bg-blue-900/30 text-primary rounded-lg flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-colors shrink-0">
        <span className="material-symbols-outlined text-lg">{icon}</span>
      </div>
      <div className="min-w-0">
        <p className="text-[#0d141b] dark:text-white text-sm font-semibold leading-tight">
          {title}
        </p>
        <p className="text-slate-500 dark:text-slate-400 text-xs font-normal leading-normal mt-0.5 truncate">
          {description}
        </p>
      </div>
    </button>
  );
}
