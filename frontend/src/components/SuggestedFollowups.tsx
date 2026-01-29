/**
 * Suggested follow-up question chips.
 */

interface SuggestedFollowupsProps {
  followups: string[];
  onSelect: (question: string) => void;
  disabled?: boolean;
}

// Icon mapping for common question patterns
function getChipIcon(text: string): string {
  const lower = text.toLowerCase();
  if (lower.includes('drill') || lower.includes('detail')) return 'filter_list';
  if (lower.includes('compare')) return 'compare_arrows';
  if (lower.includes('save') || lower.includes('bookmark')) return 'bookmark_border';
  if (lower.includes('trend') || lower.includes('over time')) return 'trending_up';
  if (lower.includes('breakdown') || lower.includes('by')) return 'pie_chart';
  if (lower.includes('why') || lower.includes('reason')) return 'lightbulb';
  return 'arrow_forward';
}

export function SuggestedFollowups({
  followups,
  onSelect,
  disabled = false,
}: SuggestedFollowupsProps) {
  if (followups.length === 0) return null;

  return (
    <div className="flex gap-2 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-hide">
      {followups.map((followup, idx) => (
        <button
          key={idx}
          onClick={() => onSelect(followup)}
          disabled={disabled}
          className="px-3 py-1.5 rounded-full border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-xs font-medium hover:border-primary hover:text-primary transition-all flex items-center gap-1.5 whitespace-nowrap flex-shrink-0 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span className="material-symbols-outlined text-sm">
            {getChipIcon(followup)}
          </span>
          {followup}
        </button>
      ))}
    </div>
  );
}
