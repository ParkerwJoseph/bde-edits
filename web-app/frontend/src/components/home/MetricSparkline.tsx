/**
 * MetricSparkline Component
 *
 * A mini area chart for displaying metric trends inline.
 * Uses recharts for smooth area visualization.
 */

import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { useMemo } from 'react';

export interface MetricSparklineProps {
  /** Array of numeric values to display */
  data: number[];
  /** Color for the line and gradient fill */
  color?: string;
  /** Height of the chart in pixels */
  height?: number;
}

export function MetricSparkline({
  data,
  color = 'var(--primary)',
  height = 40,
}: MetricSparklineProps) {
  const chartData = useMemo(
    () => data.map((value, index) => ({ value, index })),
    [data]
  );

  // Generate unique gradient ID to avoid conflicts
  const gradientId = useMemo(
    () => `sparkline-gradient-${Math.random().toString(36).substr(2, 9)}`,
    []
  );

  if (data.length === 0) {
    return <div style={{ height }} />;
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={chartData} margin={{ top: 0, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.25} />
            <stop offset="100%" stopColor={color} stopOpacity={0.02} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={2}
          strokeLinecap="round"
          fill={`url(#${gradientId})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export default MetricSparkline;
