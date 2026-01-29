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
      className="group flex flex-col gap-4 p-5 bg-white dark:bg-slate-800 rounded-xl shadow-sm hover:shadow-md hover:ring-2 hover:ring-primary/20 transition-all cursor-pointer text-left w-full"
    >
      <div className="w-11 h-11 bg-blue-50 dark:bg-blue-900/30 text-primary rounded-lg flex items-center justify-center group-hover:bg-primary group-hover:text-white transition-colors">
        <span className="material-symbols-outlined text-xl">{icon}</span>
      </div>
      <div>
        <p className="text-[#0d141b] dark:text-white text-base font-bold leading-normal">
          {title}
        </p>
        <p className="text-slate-500 dark:text-slate-400 text-sm font-normal leading-normal mt-1">
          {description}
        </p>
      </div>
    </button>
  );
}
