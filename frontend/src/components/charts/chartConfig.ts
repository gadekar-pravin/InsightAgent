/**
 * Chart configuration and theme utilities.
 */

// Primary color palette matching Tailwind config
export const CHART_COLORS = [
  '#137fec',  // Primary blue
  '#10b981',  // Emerald
  '#f59e0b',  // Amber
  '#ef4444',  // Red
  '#8b5cf6',  // Violet
];

/**
 * Get theme-aware colors for chart elements.
 */
export const getThemeColors = (isDark: boolean) => ({
  axis: isDark ? '#94a3b8' : '#64748b',      // slate-400 / slate-500
  grid: isDark ? '#334155' : '#e2e8f0',      // slate-700 / slate-200
  bg: isDark ? '#1e293b' : '#ffffff',        // slate-800 / white
  border: isDark ? '#334155' : '#e2e8f0',    // slate-700 / slate-200
  text: isDark ? '#e2e8f0' : '#334155',      // slate-200 / slate-700
});

/**
 * Format large numbers for display on chart axes.
 */
export const formatValue = (value: number): string => {
  if (typeof value !== 'number') return String(value);

  if (Math.abs(value) >= 1000000) {
    return `$${(value / 1000000).toFixed(1)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `$${(value / 1000).toFixed(1)}K`;
  }
  return value.toLocaleString();
};
