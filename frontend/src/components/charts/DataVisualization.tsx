/**
 * Data visualization component that renders appropriate chart type.
 */

import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts';
import type { VisualizationData } from '../../types/api';
import { CHART_COLORS, getThemeColors, formatValue } from './chartConfig';

interface DataVisualizationProps {
  data: VisualizationData;
}

export function DataVisualization({ data }: DataVisualizationProps) {
  // Detect dark mode from document class
  const isDark = document.documentElement.classList.contains('dark');
  const theme = getThemeColors(isDark);

  const commonChartProps = {
    data: data.data,
    margin: { top: 20, right: 30, left: 20, bottom: 5 },
  };

  const tooltipStyle = {
    backgroundColor: theme.bg,
    border: `1px solid ${theme.border}`,
    borderRadius: '8px',
    padding: '8px 12px',
  };

  const renderChart = () => {
    switch (data.chart_type) {
      case 'bar':
        return (
          <BarChart {...commonChartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis
              dataKey={data.x_axis}
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
            />
            <YAxis
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Bar
              dataKey={data.y_axis}
              fill={CHART_COLORS[0]}
              radius={[4, 4, 0, 0]}
            />
          </BarChart>
        );

      case 'line':
        return (
          <LineChart {...commonChartProps}>
            <CartesianGrid strokeDasharray="3 3" stroke={theme.grid} />
            <XAxis
              dataKey={data.x_axis}
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
            />
            <YAxis
              tick={{ fill: theme.axis, fontSize: 12 }}
              axisLine={{ stroke: theme.grid }}
              tickLine={{ stroke: theme.grid }}
              tickFormatter={formatValue}
            />
            <Tooltip contentStyle={tooltipStyle} />
            <Line
              type="monotone"
              dataKey={data.y_axis}
              stroke={CHART_COLORS[0]}
              strokeWidth={2}
              dot={{ fill: CHART_COLORS[0], strokeWidth: 2 }}
              activeDot={{ r: 6, fill: CHART_COLORS[0] }}
            />
          </LineChart>
        );

      case 'pie':
        return (
          <PieChart>
            <Pie
              data={data.data}
              dataKey={data.y_axis}
              nameKey={data.x_axis}
              cx="50%"
              cy="50%"
              outerRadius={100}
              label={({ name, percent }) =>
                `${name}: ${((percent ?? 0) * 100).toFixed(0)}%`
              }
              labelLine={{ stroke: theme.axis }}
            >
              {data.data.map((_, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={CHART_COLORS[index % CHART_COLORS.length]}
                />
              ))}
            </Pie>
            <Tooltip contentStyle={tooltipStyle} />
            <Legend
              wrapperStyle={{ color: theme.text }}
            />
          </PieChart>
        );

      default:
        return null;
    }
  };

  return (
    <div className="my-4 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm">
      {data.title && (
        <h4 className="text-sm font-semibold text-slate-700 dark:text-slate-200 mb-4">
          {data.title}
        </h4>
      )}
      <ResponsiveContainer width="100%" height={280}>
        {renderChart()}
      </ResponsiveContainer>
    </div>
  );
}
