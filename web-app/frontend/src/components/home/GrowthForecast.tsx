/**
 * GrowthForecast Component
 *
 * Line chart showing growth vs fragility trend over time.
 */

import { useNavigate } from 'react-router-dom';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import { ChevronRight, Info } from 'lucide-react';
import styles from '../../styles/components/home/GrowthForecast.module.css';

interface DataPoint {
  month: string;
  growth: number | null;
  fragility: number | null;
  forecast?: number;
}

// Empty array - no fake default data
const EMPTY_DATA: DataPoint[] = [];

// Custom dot component for circle markers
const CircleDot = (props: {
  cx?: number;
  cy?: number;
  fill?: string;
  stroke?: string;
}) => {
  const { cx, cy, fill, stroke } = props;
  if (cx === undefined || cy === undefined) return null;
  return (
    <circle
      cx={cx}
      cy={cy}
      r={4}
      fill={fill}
      stroke={stroke || fill}
      strokeWidth={2}
    />
  );
};

export interface GrowthForecastProps {
  /** Optional class name */
  className?: string;
  /** Custom data */
  data?: DataPoint[];
  /** Dynamic insight text from API */
  insight?: string;
}

export function GrowthForecast({ className, data = EMPTY_DATA, insight }: GrowthForecastProps) {
  const navigate = useNavigate();
  const isEmpty = data.length === 0;

  const handleClick = () => {
    navigate('/metrics/growth-forecast');
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      navigate('/metrics/growth-forecast');
    }
  };

  return (
    <div
      className={`${styles.container} ${className || ''}`}
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={handleKeyDown}
    >
      {/* Header */}
      <div className={styles.header}>
        <span className={styles.title}>Growth vs. Fragility Trend</span>
        {!isEmpty && (
          <div className={styles.legend}>
            <span className={styles.legendItem}>
              <span className={styles.legendLineGrowth} />
              <span className={styles.legendDotGrowth} />
              <span>Growth Signal</span>
            </span>
            <span className={styles.legendItem}>
              <span className={styles.legendLineFragility} />
              <span className={styles.legendDotFragility} />
              <span>Fragility Index</span>
            </span>
            <ChevronRight className={styles.chevron} size={16} />
          </div>
        )}
      </div>

      {/* Empty State */}
      {isEmpty ? (
        <div className={styles.emptyState}>
          <Info size={24} className={styles.emptyIcon} />
          <p className={styles.emptyText}>No trend data available</p>
          <p className={styles.emptySubtext}>Upload documents to see growth trends</p>
        </div>
      ) : (
        <>
          {/* Chart area */}
          <div className={styles.chartContainer}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data} margin={{ top: 24, right: 30, left: 10, bottom: 10 }}>
                <CartesianGrid
                  strokeDasharray="4 4"
                  stroke="var(--border-default)"
                  strokeWidth={0.5}
                  horizontal={true}
                  vertical={false}
                />
                <ReferenceLine
                  y={0}
                  stroke="var(--border-default)"
                  strokeWidth={1}
                  strokeDasharray="4 4"
                />
                <XAxis
                  dataKey="month"
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                  axisLine={{ stroke: 'var(--border-default)' }}
                  tickLine={false}
                  dy={8}
                />
                <YAxis
                  tick={{ fill: 'var(--text-muted)', fontSize: 11 }}
                  axisLine={false}
                  tickLine={false}
                  tickFormatter={(value) => `${value > 0 ? '+' : ''}${value}%`}
                  domain={[-10, 20]}
                  ticks={[-10, 0, 10, 20]}
                  dx={-5}
                />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'var(--bg-card)',
                    border: '1px solid var(--border-default)',
                    borderRadius: '6px',
                    fontSize: '12px',
                    boxShadow: 'var(--shadow-md)',
                  }}
                  labelStyle={{ color: 'var(--text-foreground)', fontWeight: 500 }}
                  formatter={(value, name) => {
                    const numValue = typeof value === 'number' ? value : 0;
                    return [
                      `${numValue > 0 ? '+' : ''}${numValue}%`,
                      name === 'growth'
                        ? 'Growth Signal'
                        : name === 'fragility'
                          ? 'Fragility Index'
                          : 'Forecast',
                    ];
                  }}
                />
                {/* Growth Signal - solid green line with circle markers */}
                <Line
                  type="monotone"
                  dataKey="growth"
                  stroke="var(--score-green)"
                  strokeWidth={2}
                  dot={<CircleDot fill="var(--score-green)" />}
                  activeDot={{ r: 5, fill: 'var(--score-green)', stroke: 'white', strokeWidth: 2 }}
                  connectNulls={false}
                />
                {/* Fragility Index - solid gray line with circle markers */}
                <Line
                  type="monotone"
                  dataKey="fragility"
                  stroke="var(--text-muted)"
                  strokeWidth={1.5}
                  dot={<CircleDot fill="var(--text-muted)" />}
                  connectNulls={false}
                />
                {/* Forecast - dashed blue line */}
                <Line
                  type="monotone"
                  dataKey="forecast"
                  stroke="var(--chart-1)"
                  strokeWidth={2}
                  strokeDasharray="6 4"
                  dot={<CircleDot fill="var(--chart-1)" />}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Footer insight - only shown if provided via props */}
          {insight && <p className={styles.insight}>{insight}</p>}
        </>
      )}
    </div>
  );
}

export default GrowthForecast;
