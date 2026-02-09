/**
 * AnalyticsCardRegistry
 *
 * Card configuration, default cards, and renderer components for the Analytics dashboard.
 * Contains 6 card types: KPI, Gauge, Chart, Comparison, Heatmap, Table
 *
 * Cards receive data through the AnalyticsMetricsContext provider.
 */

import { createContext, useContext, type ReactNode } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  ResponsiveContainer,
  Tooltip,
  CartesianGrid,
  Cell,
} from 'recharts';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Gauge,
  LineChart,
  Activity,
  BarChart3,
  ThermometerSun,
  GitCompare,
  Info,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import type {
  KPIData,
  GaugeData,
  ChartDataPoint,
  ComparisonItem,
  TableItem,
  HeatmapData,
} from '../../hooks/useAnalyticsMetrics';
import styles from '../../styles/components/analytics/AnalyticsCardRegistry.module.css';

// ===== Card Configuration Interface =====

export type CardCategory = 'kpi' | 'chart' | 'gauge' | 'table' | 'heatmap' | 'comparison';
export type CardSize = 'sm' | 'md' | 'lg' | 'xl';

export interface AnalyticsCardConfig {
  id: string;
  title: string;
  description: string;
  category: CardCategory;
  size: CardSize;
  enabled: boolean;
  order: number;
}

// ===== Default Analytics Cards =====

export const DEFAULT_ANALYTICS_CARDS: AnalyticsCardConfig[] = [
  // KPI Cards (size: sm)
  { id: 'arr-card', title: 'ARR', description: 'Annual Recurring Revenue', category: 'kpi', size: 'sm', enabled: true, order: 0 },
  { id: 'mrr-card', title: 'MRR', description: 'Monthly Recurring Revenue', category: 'kpi', size: 'sm', enabled: true, order: 1 },
  { id: 'nrr-card', title: 'NRR', description: 'Net Revenue Retention', category: 'kpi', size: 'sm', enabled: true, order: 2 },
  { id: 'cac-card', title: 'CAC', description: 'Customer Acquisition Cost', category: 'kpi', size: 'sm', enabled: true, order: 3 },
  { id: 'ltv-card', title: 'LTV', description: 'Lifetime Value', category: 'kpi', size: 'sm', enabled: false, order: 4 },
  { id: 'churn-card', title: 'Churn Rate', description: 'Monthly churn percentage', category: 'kpi', size: 'sm', enabled: true, order: 5 },

  // Gauge Cards (size: md)
  { id: 'health-gauge', title: 'Business Health', description: 'Overall health score', category: 'gauge', size: 'md', enabled: true, order: 6 },
  { id: 'runway-gauge', title: 'Runway', description: 'Months of cash remaining', category: 'gauge', size: 'md', enabled: true, order: 7 },
  { id: 'pipeline-gauge', title: 'Pipeline Coverage', description: 'Pipeline vs quota ratio', category: 'gauge', size: 'md', enabled: false, order: 8 },

  // Chart Cards (size: lg)
  { id: 'revenue-trend', title: 'Revenue Trend', description: '12-month revenue history', category: 'chart', size: 'lg', enabled: true, order: 9 },
  { id: 'growth-chart', title: 'Growth Trajectory', description: 'YoY growth comparison', category: 'chart', size: 'lg', enabled: true, order: 10 },
  { id: 'cohort-chart', title: 'Cohort Retention', description: 'Customer cohort analysis', category: 'chart', size: 'lg', enabled: true, order: 11 },

  // Comparison Cards (size: md)
  { id: 'win-loss', title: 'Win/Loss Ratio', description: 'Deal outcomes breakdown', category: 'comparison', size: 'md', enabled: true, order: 12 },
  { id: 'benchmark', title: 'Industry Benchmark', description: 'Performance vs peers', category: 'comparison', size: 'md', enabled: true, order: 13 },

  // Heatmap Cards (size: lg)
  { id: 'activity-heatmap', title: 'Activity Heatmap', description: 'Pillar health & data coverage', category: 'heatmap', size: 'lg', enabled: true, order: 14 },
  { id: 'risk-heatmap', title: 'Risk Distribution', description: 'Risk concentration by pillar', category: 'heatmap', size: 'lg', enabled: true, order: 15 },

  // Table Cards (size: lg)
  { id: 'top-accounts', title: 'Top Accounts', description: 'Highest value customers', category: 'table', size: 'lg', enabled: true, order: 16 },
  { id: 'at-risk', title: 'At-Risk Accounts', description: 'Accounts needing attention', category: 'table', size: 'lg', enabled: true, order: 17 },
  { id: 'recent-deals', title: 'Recent Deals', description: 'Latest closed opportunities', category: 'table', size: 'lg', enabled: false, order: 18 },
];

// ===== Card Size Helpers =====

export function getCardGridSpan(size: CardSize): string {
  switch (size) {
    case 'sm': return styles.colSpan1;
    case 'md': return styles.colSpan2;
    case 'lg': return styles.colSpan2;
    case 'xl': return styles.colSpan2;
    default: return styles.colSpan1;
  }
}

export function getCardHeight(size: CardSize): string {
  switch (size) {
    case 'sm': return styles.heightSm;
    case 'md': return styles.heightMd;
    case 'lg': return styles.heightLg;
    case 'xl': return styles.heightXl;
    default: return styles.heightSm;
  }
}

// ===== Category Labels =====

export const CATEGORY_LABELS: Record<CardCategory, { label: string; icon: LucideIcon }> = {
  kpi: { label: 'KPI Metrics', icon: Gauge },
  chart: { label: 'Charts', icon: LineChart },
  gauge: { label: 'Gauges', icon: Activity },
  table: { label: 'Tables', icon: BarChart3 },
  heatmap: { label: 'Heatmaps', icon: ThermometerSun },
  comparison: { label: 'Comparisons', icon: GitCompare },
};

// ===== Analytics Metrics Context =====

export interface AnalyticsMetricsContextType {
  kpiData: Record<string, KPIData>;
  gaugeData: Record<string, GaugeData>;
  chartData: Record<string, ChartDataPoint[]>;
  comparisonData: Record<string, { items: ComparisonItem[] }>;
  tableData: Record<string, { items: TableItem[] }>;
  heatmapData: Record<string, HeatmapData>;
  isLoading: boolean;
}

const defaultContextValue: AnalyticsMetricsContextType = {
  kpiData: {},
  gaugeData: {},
  chartData: {},
  comparisonData: {},
  tableData: {},
  heatmapData: {},
  isLoading: false,
};

const AnalyticsMetricsContext = createContext<AnalyticsMetricsContextType>(defaultContextValue);

export function AnalyticsMetricsProvider({
  children,
  value,
}: {
  children: ReactNode;
  value: AnalyticsMetricsContextType;
}) {
  return (
    <AnalyticsMetricsContext.Provider value={value}>
      {children}
    </AnalyticsMetricsContext.Provider>
  );
}

function useAnalyticsMetricsContext() {
  return useContext(AnalyticsMetricsContext);
}

// ===== Card Renderer Components =====

// KPI Card
export function KPICard({ id }: { id: string }) {
  const { kpiData, isLoading } = useAnalyticsMetricsContext();
  const data = kpiData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data;

  if (isLoading) {
    return (
      <div className={styles.kpiCard}>
        <div className={styles.kpiHeader}>
          <span className={styles.kpiTitle}>{config?.title || id}</span>
        </div>
        <div className={styles.cardEmptyState}>
          <span className={styles.emptyValue}>...</span>
          <span className={styles.emptyLabel}>Loading</span>
        </div>
      </div>
    );
  }

  if (isEmpty) {
    return (
      <div className={styles.kpiCard}>
        <div className={styles.kpiHeader}>
          <span className={styles.kpiTitle}>{config?.title || id}</span>
        </div>
        <div className={styles.cardEmptyState}>
          <span className={styles.emptyValue}>—</span>
          <span className={styles.emptyLabel}>No data</span>
        </div>
      </div>
    );
  }

  const TrendIcon = data.trend === 'up' ? TrendingUp : data.trend === 'down' ? TrendingDown : Minus;
  const showTrend = data.change !== 0;

  return (
    <div className={styles.kpiCard}>
      <div className={styles.kpiHeader}>
        <span className={styles.kpiTitle}>{config?.title || id}</span>
        {showTrend && (
          <div className={cn(
            styles.kpiTrend,
            data.trend === 'up' && styles.trendUp,
            data.trend === 'down' && styles.trendDown
          )}>
            <TrendIcon size={12} />
            <span>{Math.abs(data.change)}%</span>
          </div>
        )}
      </div>
      <div className={styles.kpiValue}>{data.value}</div>
      {config?.description && (
        <div className={styles.kpiDescription}>{config.description}</div>
      )}
    </div>
  );
}

// Gauge Card
function getGaugeColor(status: string): string {
  if (status === 'good') return 'hsl(var(--kpi-strong))';
  if (status === 'warning') return 'hsl(var(--kpi-at-risk))';
  return 'hsl(var(--kpi-high-risk))';
}

export function GaugeCard({ id }: { id: string }) {
  const { gaugeData, isLoading } = useAnalyticsMetricsContext();
  const data = gaugeData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data;

  if (isLoading || isEmpty) {
    return (
      <div className={styles.gaugeCard}>
        <span className={styles.gaugeHeader}>{config?.title || id}</span>
        <div className={styles.gaugeWrapper}>
          <div className={styles.gaugeRing}>
            <svg className={styles.gaugeSvg} viewBox="0 0 100 100">
              <circle
                cx="50"
                cy="50"
                r="40"
                stroke="currentColor"
                strokeWidth="8"
                fill="none"
                className={styles.gaugeTrack}
              />
            </svg>
            <div className={styles.gaugeCenter}>
              <span className={styles.gaugeValue}>{isLoading ? '...' : '—'}</span>
              <span className={styles.gaugeLabel}>{isLoading ? 'Loading' : 'No data'}</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const percentage = (data.value / data.max) * 100;

  return (
    <div className={styles.gaugeCard}>
      <span className={styles.gaugeHeader}>{config?.title || id}</span>
      <div className={styles.gaugeWrapper}>
        <div className={styles.gaugeRing}>
          <svg className={styles.gaugeSvg} viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r="40"
              stroke="currentColor"
              strokeWidth="8"
              fill="none"
              className={styles.gaugeTrack}
            />
            <circle
              cx="50"
              cy="50"
              r="40"
              stroke={getGaugeColor(data.status)}
              strokeWidth="8"
              fill="none"
              strokeDasharray={`${percentage * 2.51} 251`}
              strokeLinecap="round"
              className={styles.gaugeProgress}
            />
          </svg>
          <div className={styles.gaugeCenter}>
            <span className={styles.gaugeValue}>{data.value}</span>
            <span className={styles.gaugeLabel}>{data.label}</span>
          </div>
        </div>
      </div>
    </div>
  );
}

// ===== Chart Formatting Helpers =====

// Format value based on unit from the metric
function formatChartValue(value: number, unit?: string): string {
  // Percentage
  if (unit === '%') return `${value.toFixed(1)}%`;
  // Currency
  if (unit === '$' || unit === 'USD') {
    if (value < 0) {
      const abs = Math.abs(value);
      if (abs >= 1000000) return `-$${(abs / 1000000).toFixed(1)}M`;
      if (abs >= 1000) return `-$${(abs / 1000).toFixed(0)}K`;
      return `-$${abs.toFixed(0)}`;
    }
    if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
    if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
    return `$${value.toFixed(0)}`;
  }
  // Plain number (count)
  if (value >= 1000000) return `${(value / 1000000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}K`;
  return value % 1 === 0 ? value.toFixed(0) : value.toFixed(1);
}

// Custom tooltip for charts
function ChartTooltipContent({ active, payload, label, unit }: {
  active?: boolean;
  payload?: Array<{ value: number; payload?: ChartDataPoint }>;
  label?: string;
  unit?: string;
}) {
  if (!active || !payload || !payload.length) return null;
  const dataUnit = unit || payload[0].payload?.unit;
  return (
    <div className={styles.chartTooltip}>
      <p className={styles.chartTooltipLabel}>{label}</p>
      <p className={styles.chartTooltipValue}>
        {formatChartValue(payload[0].value, dataUnit)}
      </p>
    </div>
  );
}

// Compute summary headline for a chart card
function getChartSummary(data: ChartDataPoint[], unit?: string): { value: string; label: string } {
  if (unit === '%') {
    const avg = data.reduce((s, d) => s + d.value, 0) / data.length;
    return { value: formatChartValue(avg, unit), label: 'Avg' };
  }
  const total = data.reduce((s, d) => s + d.value, 0);
  return { value: formatChartValue(total, unit), label: 'Total' };
}

// Shared X/Y axis config
function chartXAxisProps(dataLength: number) {
  return {
    dataKey: 'label' as const,
    tick: { fill: 'var(--text-muted)', fontSize: 10 },
    axisLine: { stroke: 'var(--border-default)' },
    tickLine: false,
    interval: dataLength > 8 ? 1 : 0,
    angle: dataLength > 6 ? -45 : 0,
    textAnchor: (dataLength > 6 ? 'end' : 'middle') as 'end' | 'middle',
    height: dataLength > 6 ? 40 : 24,
  };
}

// ===== Chart Card =====
// Renders as a Bar chart. Formatting adapts to the metric unit ($ / % / plain number).

export function ChartCard({ id }: { id: string }) {
  const { chartData, isLoading } = useAnalyticsMetricsContext();
  const data = chartData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data || data.length === 0;

  if (isLoading || isEmpty) {
    return (
      <div className={styles.chartCard}>
        <div className={styles.chartHeader}>{config?.title || id}</div>
        <div className={styles.chartEmptyState}>
          <Info size={20} className={styles.emptyIcon} />
          <span className={styles.emptyLabel}>
            {isLoading ? 'Loading chart data...' : 'No chart data available'}
          </span>
        </div>
      </div>
    );
  }

  // Detect unit from the first data point (all points share the same unit)
  const dataUnit = data[0]?.unit;
  const summary = getChartSummary(data, dataUnit);

  return (
    <div className={styles.chartCard}>
      <div className={styles.chartHeaderRow}>
        <div>
          <div className={styles.chartHeader}>{config?.title || id}</div>
          <div className={styles.chartTotal}>{summary.value}</div>
        </div>
        <div className={styles.chartPeriodGroup}>
          <span className={styles.chartPeriodLabel}>{summary.label}</span>
          <span className={styles.chartPeriod}>{data.length} periods</span>
        </div>
      </div>
      <div className={styles.chartContainer}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-default)" strokeWidth={0.5} vertical={false} />
            <XAxis {...chartXAxisProps(data.length)} />
            <YAxis
              tick={{ fill: 'var(--text-muted)', fontSize: 10 }}
              axisLine={false}
              tickLine={false}
              tickFormatter={(v) => formatChartValue(v, dataUnit)}
              width={45}
            />
            <Tooltip content={<ChartTooltipContent unit={dataUnit} />} cursor={{ fill: 'var(--bg-muted)', opacity: 0.5 }} />
            <Bar dataKey="value" radius={[3, 3, 0, 0]} maxBarSize={32}>
              {data.map((_entry, index) => (
                <Cell key={`cell-${index}`} fill="var(--color-primary)" opacity={0.85} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

// Comparison Card
export function ComparisonCard({ id }: { id: string }) {
  const { comparisonData, isLoading } = useAnalyticsMetricsContext();
  const data = comparisonData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data || data.items.length === 0;

  if (isLoading || isEmpty) {
    return (
      <div className={styles.comparisonCard}>
        <div className={styles.comparisonHeader}>{config?.title || id}</div>
        <div className={styles.chartEmptyState}>
          <Info size={20} className={styles.emptyIcon} />
          <span className={styles.emptyLabel}>
            {isLoading ? 'Loading...' : 'No comparison data'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.comparisonCard}>
      <div className={styles.comparisonHeader}>{config?.title || id}</div>
      <div className={styles.comparisonBars}>
        {data.items.map((item, index) => (
          <div key={index} className={styles.comparisonItem}>
            <div className={styles.comparisonLabel}>
              <span>{item.label}</span>
              <span>{item.value}%</span>
            </div>
            <div className={styles.comparisonTrack}>
              <div
                className={styles.comparisonFill}
                style={{ width: `${item.value}%`, backgroundColor: item.color }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// Heatmap Card
// Helper to get heatmap cell background with proper alpha for smooth gradient
function getHeatmapCellStyle(cell: { color: string; value: number }): React.CSSProperties {
  // Calculate intensity (0.2 to 1.0) based on value (0-100)
  // Higher minimum ensures cells are always visible
  const intensity = 0.2 + (cell.value / 100) * 0.8;

  // For CSS variable colors like "hsl(var(--kpi-strong))", we add alpha using the / syntax
  // This works with modern CSS: hsl(var(--kpi-strong) / 0.8)
  if (cell.color.includes('var(--')) {
    // Extract the var reference and wrap with alpha
    const varMatch = cell.color.match(/hsl\((var\([^)]+\))\)/);
    if (varMatch) {
      return {
        backgroundColor: `hsl(${varMatch[1]} / ${intensity})`,
      };
    }
    // If it's just a var reference without hsl wrapper
    if (cell.color.startsWith('var(')) {
      return {
        backgroundColor: cell.color,
        opacity: intensity,
      };
    }
  }

  // For inline hsl values like "hsl(142 71% 45%)" or "hsl(142, 71%, 45%)"
  if (cell.color.startsWith('hsl(') && !cell.color.includes('var(')) {
    // Extract HSL values and add alpha
    const hslContent = cell.color.slice(4, -1); // Remove "hsl(" and ")"
    return {
      backgroundColor: `hsl(${hslContent} / ${intensity})`,
    };
  }

  // Fallback: use opacity for any other color format
  return {
    backgroundColor: cell.color,
    opacity: intensity,
  };
}

export function HeatmapCard({ id }: { id: string }) {
  const { heatmapData, isLoading } = useAnalyticsMetricsContext();
  const data = heatmapData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data || data.rows.length === 0;

  if (isLoading || isEmpty) {
    return (
      <div className={styles.heatmapCard}>
        <div className={styles.heatmapHeader}>{config?.title || id}</div>
        <div className={styles.chartEmptyState}>
          <Info size={20} className={styles.emptyIcon} />
          <span className={styles.emptyLabel}>
            {isLoading ? 'Loading...' : 'No heatmap data'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.heatmapCard}>
      <div className={styles.heatmapHeader}>{config?.title || id}</div>
      <div className={styles.heatmapTableWrapper}>
        {/* Column headers (pillar short names) */}
        <div className={styles.heatmapColHeaders}>
          <div className={styles.heatmapRowLabel} />
          {data.columnLabels.map((col) => (
            <div key={col} className={styles.heatmapColLabel}>{col}</div>
          ))}
        </div>
        {/* Data rows */}
        {data.rows.map((row) => (
          <div key={row.rowLabel} className={styles.heatmapDataRow}>
            <div className={styles.heatmapRowLabel}>{row.rowLabel}</div>
            {row.cells.map((cell, cellIdx) => (
              <div
                key={cellIdx}
                className={styles.heatmapDataCell}
                style={getHeatmapCellStyle(cell)}
                title={`${cell.label}: ${cell.displayValue}`}
              >
                <span className={styles.heatmapCellValue}>{cell.displayValue}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

// Table Card
export function TableCard({ id }: { id: string }) {
  const { tableData, isLoading } = useAnalyticsMetricsContext();
  const data = tableData[id];
  const config = DEFAULT_ANALYTICS_CARDS.find(c => c.id === id);
  const isEmpty = !data || data.items.length === 0;

  if (isLoading || isEmpty) {
    return (
      <div className={styles.tableCard}>
        <div className={styles.tableHeader}>{config?.title || id}</div>
        <div className={styles.chartEmptyState}>
          <Info size={20} className={styles.emptyIcon} />
          <span className={styles.emptyLabel}>
            {isLoading ? 'Loading...' : 'No data available'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.tableCard}>
      <div className={styles.tableHeader}>{config?.title || id}</div>
      <div className={styles.tableList}>
        {data.items.map((item, index) => (
          <div key={index} className={styles.tableRow}>
            <div className={styles.tableRowLeft}>
              <span
                className={cn(
                  styles.tableStatus,
                  item.status === 'good' && styles.statusGood,
                  item.status === 'warning' && styles.statusWarning,
                  item.status === 'critical' && styles.statusCritical
                )}
              />
              <span className={styles.tableName}>{item.name}</span>
            </div>
            <span className={styles.tableValue}>{item.value}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ===== Main Renderer Factory =====

export function renderAnalyticsCard(config: AnalyticsCardConfig) {
  switch (config.category) {
    case 'kpi':
      return <KPICard id={config.id} />;
    case 'gauge':
      return <GaugeCard id={config.id} />;
    case 'chart':
      return <ChartCard id={config.id} />;
    case 'comparison':
      return <ComparisonCard id={config.id} />;
    case 'heatmap':
      return <HeatmapCard id={config.id} />;
    case 'table':
      return <TableCard id={config.id} />;
    default:
      return null;
  }
}

export default {
  DEFAULT_ANALYTICS_CARDS,
  CATEGORY_LABELS,
  getCardGridSpan,
  getCardHeight,
  renderAnalyticsCard,
  AnalyticsMetricsProvider,
};
