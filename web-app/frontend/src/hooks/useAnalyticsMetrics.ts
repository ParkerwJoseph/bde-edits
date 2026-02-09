/**
 * useAnalyticsMetrics Hook
 *
 * Fetches metrics from the API and transforms them into formats
 * suitable for the Analytics dashboard cards (KPI, Gauge, Chart, etc.)
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { scoringApi, type MetricsResponse, type Metric, type BDEScoreResponse, type FlagsResponse, type BDEPillar, PILLAR_CONFIG } from '../api/scoringApi';

// Industry benchmark threshold (green = good)
const INDUSTRY_BENCHMARK_SCORE = 4.0; // Score of 4.0+ is considered "industry standard"
const MAX_SCORE = 5.0;

// ===== Types for Analytics Cards =====

export interface KPIData {
  value: string;
  numericValue: number | null;
  change: number;
  trend: 'up' | 'down' | 'neutral';
  unit: string | null;
  period: string | null;
  confidence: number;
}

export interface GaugeData {
  value: number;
  max: number;
  label: string;
  status: 'good' | 'warning' | 'critical';
}

export interface ChartDataPoint {
  label: string;
  value: number;
  unit?: string;
}

export interface ComparisonItem {
  label: string;
  value: number;
  color: string;
}

export interface TableItem {
  name: string;
  value: string;
  status: 'good' | 'warning' | 'critical';
}

export interface HeatmapCell {
  label: string;
  value: number;        // 0-100 normalized
  displayValue: string; // e.g. "3.2" or "75%"
  color: string;        // hex or hsl color
}

export interface HeatmapRow {
  rowLabel: string;
  cells: HeatmapCell[];
}

export interface HeatmapData {
  columnLabels: string[];
  rows: HeatmapRow[];
}

// ===== Metric Name Mappings =====

// Map card IDs to possible metric names in the database
const CARD_TO_METRIC_MAP: Record<string, string[]> = {
  // Financial KPIs
  'arr-card': ['ARR', 'Annual Recurring Revenue', 'annual_recurring_revenue'],
  'mrr-card': ['MRR', 'Monthly Recurring Revenue', 'monthly_recurring_revenue'],
  'nrr-card': ['NRR', 'Net Revenue Retention', 'net_revenue_retention', 'Net Dollar Retention'],
  'cac-card': ['CAC', 'Customer Acquisition Cost', 'customer_acquisition_cost'],
  'ltv-card': ['LTV', 'Lifetime Value', 'Customer Lifetime Value', 'lifetime_value', 'CLV'],
  'churn-card': ['Churn Rate', 'Monthly Churn', 'churn_rate', 'Customer Churn', 'Logo Churn', 'ChurnRatePct', 'LogoChurnRatePct', 'RevenueChurnRatePct'],

  // Customer Health Metrics
  'total-customers': ['TotalCustomers', 'Total Customers', 'CustomerCount', 'total_customers'],
  'active-customers': ['ActiveCustomers', 'Active Customers', 'active_customers'],
  'new-signups': ['NewSignups', 'New Signups', 'NewCustomers', 'new_signups', 'new_customers'],
  'churned-customers': ['ChurnedCustomers', 'Churned Customers', 'churned_customers', 'CustomersLost'],
  'renewal-rate': ['RenewalRate', 'Renewal Rate', 'renewal_rate'],
  'grr-card': ['GRR', 'Gross Revenue Retention', 'gross_revenue_retention'],
  'at-risk-customers': ['AtRiskCustomerCount', 'At Risk Customers', 'at_risk_customers'],

  // Gauges
  'health-gauge': ['BusinessHealthScore', 'Business Health Score', 'Health Score', 'Overall Health'],
  'runway-gauge': ['Runway', 'Cash Runway', 'Months of Runway', 'runway_months', 'RunwayMonths'],
  'pipeline-gauge': ['Pipeline Coverage', 'Pipeline Ratio', 'pipeline_coverage', 'PipelineCoverageRatio'],

  // Charts (time-series JSON metrics from database)
  'revenue-trend': ['RevenueTrend', 'Revenue Trend', 'Revenue', 'Total Revenue', 'Monthly Revenue'],
  'growth-chart': ['Revenue Growth', 'YoY Growth', 'Growth Rate', 'ARR Growth', 'RevenueGrowthRateYoY'],
  'cohort-chart': ['CohortRetentionTrend', 'ChurnTrend', 'CustomerCountTrend', 'ChurnedCustomersTrend', 'NewCustomersTrend'],
  'win-loss': ['Win Rate', 'Win/Loss Ratio', 'Deal Win Rate', 'WinRatePct'],
  'benchmark': ['Industry Benchmark', 'Peer Comparison'],

  // Table/List metrics (JSON arrays)
  'top-accounts': ['TopAccountsList', 'Top Accounts', 'top_accounts_list'],
  'at-risk': ['AtRiskAccountsList', 'At Risk Accounts', 'at_risk_accounts_list'],
  'recent-deals': ['RecentDealsList', 'Recent Deals', 'recent_deals_list'],
};

// ===== Helper Functions =====

/**
 * Format a numeric value with appropriate units
 */
function formatMetricValue(value: number | null, unit: string | null): string {
  if (value === null) return '—';

  // Handle percentage
  if (unit === '%') {
    return `${value.toFixed(1)}%`;
  }

  // Handle currency
  if (unit === '$' || unit === 'USD') {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(1)}M`;
    }
    if (value >= 1000) {
      return `$${(value / 1000).toFixed(0)}K`;
    }
    return `$${value.toFixed(0)}`;
  }

  // Handle months
  if (unit === 'months' || unit === 'mo') {
    return `${value.toFixed(0)} mo`;
  }

  // Handle multipliers
  if (unit === 'x') {
    return `${value.toFixed(1)}x`;
  }

  // Default formatting
  if (value >= 1000000) {
    return `${(value / 1000000).toFixed(1)}M`;
  }
  if (value >= 1000) {
    return `${(value / 1000).toFixed(1)}K`;
  }

  return value.toFixed(value % 1 === 0 ? 0 : 1);
}

/**
 * Determine trend based on metric name and value
 * In a real implementation, this would compare to historical data
 */
function determineTrend(_metricName: string, _value: number | null): 'up' | 'down' | 'neutral' {
  // For now, return neutral since we don't have historical data
  // This would be enhanced with actual trend calculation
  return 'neutral';
}

/**
 * Determine gauge status based on value and thresholds
 */
function determineGaugeStatus(cardId: string, value: number, max: number): 'good' | 'warning' | 'critical' {
  const percentage = (value / max) * 100;

  // Different thresholds for different gauges
  if (cardId === 'runway-gauge') {
    // Runway: < 6 months critical, < 12 months warning
    if (value < 6) return 'critical';
    if (value < 12) return 'warning';
    return 'good';
  }

  if (cardId === 'pipeline-gauge') {
    // Pipeline coverage: < 2x critical, < 3x warning
    if (value < 2) return 'critical';
    if (value < 3) return 'warning';
    return 'good';
  }

  // Default: < 40% critical, < 70% warning
  if (percentage < 40) return 'critical';
  if (percentage < 70) return 'warning';
  return 'good';
}

/**
 * Find a metric by checking multiple possible names
 * Uses flexible matching similar to AnalyticsPillarDetail for consistency
 */
function findMetric(metrics: Record<string, Metric>, possibleNames: string[]): Metric | null {
  for (const name of possibleNames) {
    // Try exact match
    if (metrics[name]) {
      return metrics[name];
    }
    // Try case-insensitive and partial matching
    const lowerName = name.toLowerCase();
    for (const [key, value] of Object.entries(metrics)) {
      const lowerKey = key.toLowerCase();
      if (
        lowerKey === lowerName ||
        lowerKey.includes(lowerName) ||
        lowerName.includes(lowerKey)
      ) {
        return value;
      }
    }
  }
  return null;
}

// ===== Main Hook =====

export interface AnalyticsMetricsData {
  kpiData: Record<string, KPIData>;
  gaugeData: Record<string, GaugeData>;
  chartData: Record<string, ChartDataPoint[]>;
  comparisonData: Record<string, { items: ComparisonItem[] }>;
  tableData: Record<string, { items: TableItem[] }>;
  heatmapData: Record<string, HeatmapData>;
  rawMetrics: MetricsResponse | null;
  bdeScore: BDEScoreResponse | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => Promise<void>;
}

export function useAnalyticsMetrics(companyId: string | null): AnalyticsMetricsData {
  const [rawMetrics, setRawMetrics] = useState<MetricsResponse | null>(null);
  const [bdeScore, setBdeScore] = useState<BDEScoreResponse | null>(null);
  const [flags, setFlags] = useState<FlagsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchMetrics = useCallback(async () => {
    if (!companyId) {
      setRawMetrics(null);
      setBdeScore(null);
      setFlags(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Fetch metrics, BDE score, and flags in parallel
      const [metricsResponse, bdeScoreResponse, flagsResponse] = await Promise.all([
        scoringApi.getMetrics(companyId),
        scoringApi.getBDEScore(companyId).catch(() => null), // Don't fail if no score yet
        scoringApi.getFlags(companyId).catch(() => null),    // Don't fail if no flags yet
      ]);
      setRawMetrics(metricsResponse);
      setBdeScore(bdeScoreResponse);
      setFlags(flagsResponse);
    } catch (err) {
      setError(err instanceof Error ? err : new Error('Failed to fetch metrics'));
      setRawMetrics(null);
      setBdeScore(null);
      setFlags(null);
    } finally {
      setIsLoading(false);
    }
  }, [companyId]);

  useEffect(() => {
    fetchMetrics();
  }, [fetchMetrics]);

  // Transform raw metrics into KPI card data
  const kpiData = useMemo(() => {
    const result: Record<string, KPIData> = {};
    if (!rawMetrics?.metrics) return result;

    // All KPI card IDs including financial and customer health metrics
    const kpiCardIds = [
      // Financial KPIs
      'arr-card', 'mrr-card', 'nrr-card', 'cac-card', 'ltv-card', 'churn-card',
      // Customer Health Metrics
      'total-customers', 'active-customers', 'new-signups', 'churned-customers',
      'renewal-rate', 'grr-card', 'at-risk-customers',
    ];

    for (const cardId of kpiCardIds) {
      const possibleNames = CARD_TO_METRIC_MAP[cardId] || [];
      const metric = findMetric(rawMetrics.metrics, possibleNames);

      if (metric) {
        const value = metric.current_value;
        result[cardId] = {
          value: formatMetricValue(value.numeric, value.unit),
          numericValue: value.numeric,
          change: 0, // Would need historical data for real change calculation
          trend: determineTrend(cardId, value.numeric),
          unit: value.unit,
          period: value.period,
          confidence: value.confidence,
        };
      }
    }

    return result;
  }, [rawMetrics]);

  // Transform raw metrics into Gauge card data
  const gaugeData = useMemo(() => {
    const result: Record<string, GaugeData> = {};
    if (!rawMetrics?.metrics) return result;

    // Health gauge - derived from overall metrics or specific health score
    const healthMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['health-gauge'] || []);
    if (healthMetric && healthMetric.current_value.numeric !== null) {
      const value = healthMetric.current_value.numeric;
      result['health-gauge'] = {
        value: value,
        max: 100,
        label: 'Score',
        status: determineGaugeStatus('health-gauge', value, 100),
      };
    }

    // Runway gauge
    const runwayMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['runway-gauge'] || []);
    if (runwayMetric && runwayMetric.current_value.numeric !== null) {
      const value = runwayMetric.current_value.numeric;
      result['runway-gauge'] = {
        value: value,
        max: 24, // 24 months as max
        label: 'months',
        status: determineGaugeStatus('runway-gauge', value, 24),
      };
    }

    // Pipeline coverage gauge
    const pipelineMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['pipeline-gauge'] || []);
    if (pipelineMetric && pipelineMetric.current_value.numeric !== null) {
      const value = pipelineMetric.current_value.numeric;
      result['pipeline-gauge'] = {
        value: value,
        max: 5, // 5x coverage as max
        label: 'x coverage',
        status: determineGaugeStatus('pipeline-gauge', value, 5),
      };
    }

    return result;
  }, [rawMetrics]);

  // Transform raw metrics into Chart data (time-series JSON metrics)
  const chartData = useMemo(() => {
    const result: Record<string, ChartDataPoint[]> = {};
    if (!rawMetrics?.metrics) return result;

    // Chart card IDs that map to time-series JSON metrics
    const chartCardIds = [
      'revenue-trend',
      'growth-chart',
      'cohort-chart',
    ];

    // Helper to parse JSON that might be multi-serialized
    const parseJson = (jsonValue: unknown): unknown => {
      if (!jsonValue) return null;
      let parsed = jsonValue;
      let iterations = 0;
      while (typeof parsed === 'string' && iterations < 5) {
        iterations++;
        try {
          parsed = JSON.parse(parsed);
        } catch {
          return null;
        }
      }
      return parsed;
    };

    // Helper to shorten month labels (e.g., "Dec 2023" → "Dec 23", "December 2023" → "Dec 23")
    const shortenLabel = (label: string): string => {
      // Try "Month YYYY" or "Mon YYYY" format
      const match = label.match(/^(\w+)\s+(\d{4})$/);
      if (match) {
        const month = match[1].substring(0, 3);
        const year = match[2].substring(2);
        return `${month} ${year}`;
      }
      // Already short or unknown format — return as-is
      return label;
    };

    for (const cardId of chartCardIds) {
      const possibleNames = CARD_TO_METRIC_MAP[cardId] || [];
      const metric = findMetric(rawMetrics.metrics, possibleNames);

      if (!metric?.current_value?.json) continue;

      const parsed = parseJson(metric.current_value.json);
      if (!parsed || typeof parsed !== 'object') continue;

      const jsonObj = parsed as Record<string, unknown>;

      // Handle time-series format: { type: "time_series", data: { "Dec 2023": 10995.80, ... }, total: N }
      // Also handle flat format: { "Dec 2023": 10995.80, ... }
      let dataObj: Record<string, unknown> | null = null;

      if (jsonObj.type === 'time_series' && jsonObj.data && typeof jsonObj.data === 'object') {
        dataObj = jsonObj.data as Record<string, unknown>;
      } else if (!jsonObj.type) {
        // Flat key-value format — use directly (skip non-numeric meta keys)
        dataObj = jsonObj;
      }

      if (!dataObj) continue;

      const metricUnit = metric.current_value.unit || undefined;
      const dataPoints: ChartDataPoint[] = [];
      for (const [key, val] of Object.entries(dataObj)) {
        // Skip metadata keys
        if (key === 'type' || key === 'frequency' || key === 'total' || key === 'unit') continue;
        const numVal = typeof val === 'number' ? val : parseFloat(String(val));
        if (!isNaN(numVal)) {
          dataPoints.push({ label: shortenLabel(key), value: numVal, unit: metricUnit });
        }
      }

      if (dataPoints.length > 0) {
        // Filter out "Total" entries and limit to 12 monthly periods
        // The API sometimes returns 13 periods including a "Total" column
        const filteredPoints = dataPoints.filter(point => {
          const lowerLabel = point.label.toLowerCase();
          return lowerLabel !== 'total' && !lowerLabel.includes('total');
        });

        // Sort by date to ensure chronological order, then take the last 12 periods
        // This handles cases where more than 12 monthly data points are returned
        const sortedPoints = filteredPoints.sort((a, b) => {
          // Parse month-year labels like "Jan 24", "Feb 24", etc.
          const monthOrder = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec'];
          const parseLabel = (label: string): { month: number; year: number } => {
            const parts = label.toLowerCase().split(/[\s-]+/);
            let month = 0, year = 2000;
            for (const part of parts) {
              const yearNum = parseInt(part);
              if (yearNum >= 0 && yearNum <= 99) {
                year = 2000 + yearNum;
              } else if (yearNum > 1900 && yearNum < 2100) {
                year = yearNum;
              } else {
                const idx = monthOrder.findIndex(m => part.startsWith(m));
                if (idx >= 0) month = idx;
              }
            }
            return { month, year };
          };
          const aParsed = parseLabel(a.label);
          const bParsed = parseLabel(b.label);
          if (aParsed.year !== bParsed.year) return aParsed.year - bParsed.year;
          return aParsed.month - bParsed.month;
        });

        // Take only the last 12 monthly periods
        const limitedPoints = sortedPoints.slice(-12);

        result[cardId] = limitedPoints;
      }
    }

    return result;
  }, [rawMetrics]);

  // Comparison data - includes win/loss and industry benchmark
  const comparisonData = useMemo(() => {
    const result: Record<string, { items: ComparisonItem[] }> = {};

    // Win/Loss from metrics if available
    const winRateMetric = findMetric(rawMetrics?.metrics || {}, CARD_TO_METRIC_MAP['win-loss'] || []);
    if (winRateMetric && winRateMetric.current_value.numeric !== null) {
      const winRate = winRateMetric.current_value.numeric;
      result['win-loss'] = {
        items: [
          { label: 'Won', value: winRate, color: 'hsl(var(--score-green))' },
          { label: 'Lost', value: 100 - winRate, color: 'hsl(var(--score-red))' },
        ],
      };
    }

    // Industry Benchmark - calculated from overall pillar scores average
    if (bdeScore?.pillar_scores) {
      const pillarScores = Object.values(bdeScore.pillar_scores);
      if (pillarScores.length > 0) {
        // Calculate average of all pillar scores
        const totalScore = pillarScores.reduce((sum, pillar) => sum + pillar.score, 0);
        const averageScore = totalScore / pillarScores.length;

        // Convert to percentage (score is 0-5 scale)
        const yourPercent = Math.round((averageScore / MAX_SCORE) * 100);
        const industryPercent = Math.round((INDUSTRY_BENCHMARK_SCORE / MAX_SCORE) * 100);

        result['benchmark'] = {
          items: [
            { label: 'You', value: yourPercent, color: 'hsl(var(--primary))' },
            { label: 'Industry', value: industryPercent, color: 'hsl(var(--muted-foreground) / 0.3)' },
          ],
        };
      }
    }

    return result;
  }, [rawMetrics, bdeScore]);

  // Table data - parsed from JSON list metrics
  const tableData = useMemo(() => {
    const result: Record<string, { items: TableItem[] }> = {};
    if (!rawMetrics?.metrics) return result;

    // Helper to format currency values
    const formatCurrency = (value: number): string => {
      if (value >= 1000000) return `$${(value / 1000000).toFixed(1)}M`;
      if (value >= 1000) return `$${(value / 1000).toFixed(0)}K`;
      return `$${value.toFixed(0)}`;
    };

    // Type definition for flexible metric data - handles any column names from the document
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    type MetricData = Record<string, any>;

    // Helper to parse JSON that might be multi-serialized (handles up to 5 levels)
    const parseJsonValue = <T>(jsonValue: unknown): T[] | null => {
      if (!jsonValue) return null;

      let parsed = jsonValue;

      // Keep parsing while it's a string (handles multiple levels of serialization)
      let iterations = 0;
      const maxIterations = 5;
      while (typeof parsed === 'string' && iterations < maxIterations) {
        iterations++;
        try {
          parsed = JSON.parse(parsed);
        } catch {
          console.warn('[useAnalyticsMetrics] Failed to parse JSON string at iteration', iterations);
          return null;
        }
      }

      if (iterations > 0) {
        console.log(`[useAnalyticsMetrics] Parsed JSON after ${iterations} iteration(s)`);
      }

      // If it's an array, return it
      if (Array.isArray(parsed)) {
        return parsed as T[];
      }

      return null;
    };

    // Helper to get the monetary value from an item (handles flexible column names)
    const getMonetaryValue = (item: MetricData): number => {
      // Priority order for monetary value fields (handles various column naming conventions)
      const monetaryKeys = [
        'arr', 'mrr', 'value', 'revenue', 'revenue_contribution', 'current_revenue',
        'deal_size', 'deal_value', 'amount', 'total', 'annual_revenue', 'monthly_revenue'
      ];

      for (const key of monetaryKeys) {
        if (typeof item[key] === 'number' && item[key] > 0) return item[key];
      }

      // Fallback: find any numeric field that looks like a monetary value (> 1000)
      for (const [key, val] of Object.entries(item)) {
        if (typeof val === 'number' && val > 1000 && !key.includes('pct') && !key.includes('percent')) {
          return val;
        }
      }

      return 0;
    };

    // Helper to get the display name from an item (handles flexible column names)
    const getDisplayName = (item: MetricData): string => {
      // Priority order for name fields
      const nameKeys = [
        'name', 'account_name', 'customer', 'customer_name', 'deal_name',
        'company', 'company_name', 'client', 'client_name'
      ];

      for (const key of nameKeys) {
        if (typeof item[key] === 'string' && item[key]) return item[key];
      }

      return 'Unknown';
    };

    // Helper to normalize status (handle various status formats from flexible extraction)
    const normalizeStatus = (item: MetricData, defaultStatus: 'good' | 'warning' | 'critical'): 'good' | 'warning' | 'critical' => {
      // Try to find status in various fields
      const statusFields = ['status', 'risk_level', 'health', 'state'];
      let statusValue: string | undefined;

      for (const field of statusFields) {
        if (typeof item[field] === 'string' && item[field]) {
          statusValue = item[field];
          break;
        }
      }

      if (!statusValue) return defaultStatus;

      const s = statusValue.toLowerCase();

      // Good indicators
      if (s === 'good' || s === 'won' || s === 'active' || s === 'healthy' ||
          s.includes('strong') || s.includes('stable') || s.includes('growth') ||
          s.includes('expanding') || s === 'low') {
        return 'good';
      }

      // Critical indicators
      if (s === 'critical' || s === 'lost' || s === 'high' || s === 'churned' ||
          s.includes('risk') || s.includes('delayed') || s.includes('dropped')) {
        return 'critical';
      }

      // Warning indicators (or anything else)
      if (s === 'warning' || s === 'pending' || s === 'medium' ||
          s.includes('renewing') || s.includes('upside')) {
        return 'warning';
      }

      return defaultStatus;
    };

    // Top Accounts (show top 3)
    const topAccountsMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['top-accounts'] || []);
    if (topAccountsMetric?.current_value?.json) {
      const jsonData = parseJsonValue<MetricData>(topAccountsMetric.current_value.json);
      if (jsonData && jsonData.length > 0) {
        result['top-accounts'] = {
          items: jsonData.slice(0, 3).map((item) => ({
            name: getDisplayName(item),
            value: formatCurrency(getMonetaryValue(item)),
            status: normalizeStatus(item, 'good'),
          })),
        };
      }
    }

    // At-Risk Accounts (show top 3)
    const atRiskMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['at-risk'] || []);
    if (atRiskMetric?.current_value?.json) {
      const jsonData = parseJsonValue<MetricData>(atRiskMetric.current_value.json);
      if (jsonData && jsonData.length > 0) {
        result['at-risk'] = {
          items: jsonData.slice(0, 3).map((item) => ({
            name: getDisplayName(item),
            value: formatCurrency(getMonetaryValue(item)),
            status: normalizeStatus(item, 'critical'),
          })),
        };
      }
    }

    // Recent Deals (show top 3)
    const recentDealsMetric = findMetric(rawMetrics.metrics, CARD_TO_METRIC_MAP['recent-deals'] || []);
    if (recentDealsMetric?.current_value?.json) {
      const jsonData = parseJsonValue<MetricData>(recentDealsMetric.current_value.json);
      if (jsonData && jsonData.length > 0) {
        result['recent-deals'] = {
          items: jsonData.slice(0, 3).map((item) => ({
            name: getDisplayName(item),
            value: formatCurrency(getMonetaryValue(item)),
            status: normalizeStatus(item, 'warning'),
          })),
        };
      }
    }

    return result;
  }, [rawMetrics]);

  // Build heatmap data from BDE pillar scores and flags
  const heatmapData = useMemo(() => {
    const result: Record<string, HeatmapData> = {};

    // Ordered pillar keys for consistent column ordering
    const pillarOrder: BDEPillar[] = [
      'financial_health',
      'gtm_engine',
      'customer_health',
      'product_technical',
      'operational_maturity',
      'leadership_transition',
      'ecosystem_dependency',
      'service_software_ratio',
    ];

    // Short pillar labels for column headers
    const pillarShortLabels: Record<BDEPillar, string> = {
      financial_health: 'Fin',
      gtm_engine: 'GTM',
      customer_health: 'Cust',
      product_technical: 'Prod',
      operational_maturity: 'Ops',
      leadership_transition: 'Lead',
      ecosystem_dependency: 'Eco',
      service_software_ratio: 'S2S',
    };

    // Helper: map a 0-100 value to a green-yellow-red color
    function valueToColor(value: number): string {
      if (value >= 70) return 'hsl(var(--kpi-strong))';
      if (value >= 40) return 'hsl(var(--kpi-at-risk))';
      return 'hsl(var(--kpi-high-risk))';
    }

    // --- Activity Heatmap: Customer Activity Over Time ---
    // Rows: Total, New, Churned, Churn%  |  Columns: Recent months
    // Uses time-series customer metrics from the database
    if (rawMetrics?.metrics) {
      // Helper to parse time-series JSON (handles multi-serialized JSON)
      const excludeKeys = ['type', 'frequency', 'total', 'unit', 'sum', 'average', 'avg'];

      const filterDataObject = (data: Record<string, unknown>): Record<string, number> => {
        const result: Record<string, number> = {};
        for (const [k, v] of Object.entries(data)) {
          // Case-insensitive check for excluded keys
          if (!excludeKeys.includes(k.toLowerCase())) {
            const numVal = typeof v === 'number' ? v : parseFloat(String(v));
            if (!isNaN(numVal) && v !== null) {
              result[k] = numVal;
            }
          }
        }
        return result;
      };

      const parseTimeSeries = (metric: Metric | null): Record<string, number> | null => {
        if (!metric?.current_value?.json) return null;
        let parsed = metric.current_value.json;
        let iterations = 0;
        while (typeof parsed === 'string' && iterations < 5) {
          iterations++;
          try { parsed = JSON.parse(parsed); } catch { return null; }
        }
        if (!parsed || typeof parsed !== 'object') return null;
        const obj = parsed as Record<string, unknown>;
        // Handle time_series format: { type: "time_series", data: {...} }
        if (obj.type === 'time_series' && obj.data && typeof obj.data === 'object') {
          const filtered = filterDataObject(obj.data as Record<string, unknown>);
          return Object.keys(filtered).length > 0 ? filtered : null;
        }
        // Handle flat format: { "Jan 2025": 100, ... }
        const filtered = filterDataObject(obj);
        return Object.keys(filtered).length > 0 ? filtered : null;
      };

      // Find customer time-series metrics - try multiple possible names
      const customerCountMetric = findMetric(rawMetrics.metrics, [
        'CustomerCountTrend', 'TotalCustomersTrend', 'Total Customers', 'CustomerCount'
      ]);
      const newCustomersMetric = findMetric(rawMetrics.metrics, [
        'NewCustomersTrend', 'NewSignupsTrend', 'New Customers', 'NewCustomers'
      ]);
      const churnedMetric = findMetric(rawMetrics.metrics, [
        'ChurnedCustomersTrend', 'Churned Customers', 'ChurnedCustomers', 'CustomersLost'
      ]);
      const churnRateMetric = findMetric(rawMetrics.metrics, [
        'ChurnTrend', 'ChurnRateTrend', 'Churn Rate', 'ChurnRate', 'CohortRetentionTrend'
      ]);

      const customerCountData = parseTimeSeries(customerCountMetric);
      const newCustomersData = parseTimeSeries(newCustomersMetric);
      const churnedData = parseTimeSeries(churnedMetric);
      const churnRateData = parseTimeSeries(churnRateMetric);

      // Collect all available month keys from any metric that has data
      // Exclude "Total" and similar aggregate keys (uses excludeKeys defined above)
      const allMonths = new Set<string>();
      [customerCountData, newCustomersData, churnedData, churnRateData].forEach(data => {
        if (data) {
          Object.keys(data).forEach(k => {
            if (!excludeKeys.includes(k.toLowerCase())) {
              allMonths.add(k);
            }
          });
        }
      });

      // Sort months chronologically and take last 6
      const monthAbbrevOrder = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const sortedMonths = Array.from(allMonths).sort((a, b) => {
        // Handle formats like "Jan 2025", "January 2025", "2025-01", etc.
        const parseMonth = (m: string): { month: number; year: number } => {
          const parts = m.split(/[\s-]+/);
          let month = 0, year = 2000;
          for (const part of parts) {
            const yearNum = parseInt(part);
            if (yearNum > 1900 && yearNum < 2100) {
              year = yearNum;
            } else {
              const idx = monthAbbrevOrder.findIndex(abbr => part.toLowerCase().startsWith(abbr.toLowerCase()));
              if (idx >= 0) month = idx;
            }
          }
          return { month, year };
        };
        const aParsed = parseMonth(a);
        const bParsed = parseMonth(b);
        if (aParsed.year !== bParsed.year) return aParsed.year - bParsed.year;
        return aParsed.month - bParsed.month;
      });
      const recentMonths = sortedMonths.slice(-6);

      if (recentMonths.length > 0) {
        // Shorten month labels for display (e.g., "January 2025" → "Jan")
        const columnLabels = recentMonths.map(m => {
          const parts = m.split(/[\s-]+/);
          for (const part of parts) {
            const idx = monthAbbrevOrder.findIndex(abbr => part.toLowerCase().startsWith(abbr.toLowerCase()));
            if (idx >= 0) return monthAbbrevOrder[idx];
          }
          return m.substring(0, 3); // Fallback
        });

        // Build row for a metric
        const buildRow = (
          data: Record<string, number> | null,
          rowLabel: string,
          colorFn: (val: number, max: number) => string
        ): HeatmapRow | null => {
          if (!data) return null;
          const values = recentMonths.map(m => data[m] ?? 0);
          // Skip row if all values are 0
          if (values.every(v => v === 0)) return null;
          const maxVal = Math.max(1, ...values);
          const cells: HeatmapCell[] = recentMonths.map((month, i) => {
            const val = values[i];
            return {
              label: month,
              value: (val / maxVal) * 100,
              displayValue: val >= 1000 ? `${(val / 1000).toFixed(1)}K` : String(Math.round(val)),
              color: colorFn(val, maxVal),
            };
          });
          return { rowLabel, cells };
        };

        const rows: HeatmapRow[] = [];

        // New Customers (green = good)
        const newRow = buildRow(newCustomersData, 'New', (val, max) => {
          const intensity = val / max;
          return intensity > 0.5 ? 'hsl(var(--kpi-strong))' : intensity > 0.2 ? 'hsl(142 71% 45% / 0.6)' : 'var(--bg-muted)';
        });
        if (newRow) rows.push(newRow);

        // Churned Customers (red = bad)
        const churnedRow = buildRow(churnedData, 'Churned', (val, max) => {
          const intensity = val / max;
          return intensity > 0.5 ? 'hsl(var(--kpi-high-risk))' : intensity > 0.2 ? 'hsl(0 84% 60% / 0.6)' : 'var(--bg-muted)';
        });
        if (churnedRow) rows.push(churnedRow);

        // Churn Rate (red = bad, percentage)
        const churnRow = buildRow(churnRateData, 'Churn %', (val, max) => {
          const intensity = val / max;
          return intensity > 0.5 ? 'hsl(var(--kpi-high-risk))' : intensity > 0.2 ? 'hsl(var(--kpi-at-risk))' : 'hsl(var(--kpi-strong))';
        });
        if (churnRow) rows.push(churnRow);

        if (rows.length > 0) {
          result['activity-heatmap'] = { columnLabels, rows };
        }
      }
    }

    // Fallback: If no customer time-series data, show pillar health data
    if (!result['activity-heatmap'] && bdeScore?.pillar_scores) {
      const columnLabels = pillarOrder.map(p => pillarShortLabels[p]);

      // Health status row
      const healthRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const pillar = bdeScore.pillar_scores[pillarId];
        if (!pillar) return { label: PILLAR_CONFIG[pillarId].label, value: 0, displayValue: '—', color: 'var(--bg-muted)' };
        const statusColor = pillar.health_status === 'green'
          ? 'hsl(var(--kpi-strong))'
          : pillar.health_status === 'yellow'
            ? 'hsl(var(--kpi-at-risk))'
            : 'hsl(var(--kpi-high-risk))';
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: pillar.health_status === 'green' ? 100 : pillar.health_status === 'yellow' ? 50 : 25,
          displayValue: pillar.score.toFixed(1),
          color: statusColor,
        };
      });

      // Coverage row
      const coverageRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const pillar = bdeScore.pillar_scores[pillarId];
        if (!pillar) return { label: PILLAR_CONFIG[pillarId].label, value: 0, displayValue: '—', color: 'var(--bg-muted)' };
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: pillar.data_coverage,
          displayValue: `${Math.round(pillar.data_coverage)}%`,
          color: valueToColor(pillar.data_coverage),
        };
      });

      // Confidence row
      const confidenceRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const pillar = bdeScore.pillar_scores[pillarId];
        if (!pillar) return { label: PILLAR_CONFIG[pillarId].label, value: 0, displayValue: '—', color: 'var(--bg-muted)' };
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: pillar.confidence,
          displayValue: `${Math.round(pillar.confidence)}%`,
          color: valueToColor(pillar.confidence),
        };
      });

      result['activity-heatmap'] = {
        columnLabels,
        rows: [
          { rowLabel: 'Score', cells: healthRow },
          { rowLabel: 'Coverage', cells: coverageRow },
          { rowLabel: 'Confidence', cells: confidenceRow },
        ],
      };
    }

    // --- Risk Heatmap: Flag Distribution by Pillar ---
    // Rows: Red Flags, Yellow Flags, Green Accelerants  |  Columns: 8 pillars
    if (flags) {
      const columnLabels = pillarOrder.map(p => pillarShortLabels[p]);

      // Count flags per pillar
      const countByPillar = (flagList: Array<{ pillar: string }>) => {
        const counts: Record<string, number> = {};
        flagList.forEach(f => {
          const key = f.pillar?.toLowerCase().replace(/\s+/g, '_') || 'unknown';
          counts[key] = (counts[key] || 0) + 1;
        });
        return counts;
      };

      const redCounts = countByPillar(flags.red_flags || []);
      const yellowCounts = countByPillar(flags.yellow_flags || []);
      const greenCounts = countByPillar(flags.green_accelerants || []);

      // Find max count for normalization
      const allCounts = [...Object.values(redCounts), ...Object.values(yellowCounts), ...Object.values(greenCounts)];
      const maxCount = Math.max(1, ...allCounts);

      const redRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const count = redCounts[pillarId] || 0;
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: (count / maxCount) * 100,
          displayValue: String(count),
          color: count > 0 ? 'hsl(var(--kpi-high-risk))' : 'var(--bg-muted)',
        };
      });

      const yellowRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const count = yellowCounts[pillarId] || 0;
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: (count / maxCount) * 100,
          displayValue: String(count),
          color: count > 0 ? 'hsl(var(--kpi-at-risk))' : 'var(--bg-muted)',
        };
      });

      const greenRow: HeatmapCell[] = pillarOrder.map(pillarId => {
        const count = greenCounts[pillarId] || 0;
        return {
          label: PILLAR_CONFIG[pillarId].label,
          value: (count / maxCount) * 100,
          displayValue: String(count),
          color: count > 0 ? 'hsl(var(--kpi-strong))' : 'var(--bg-muted)',
        };
      });

      result['risk-heatmap'] = {
        columnLabels,
        rows: [
          { rowLabel: 'Red Flags', cells: redRow },
          { rowLabel: 'Yellow Flags', cells: yellowRow },
          { rowLabel: 'Green', cells: greenRow },
        ],
      };
    }

    return result;
  }, [bdeScore, flags, rawMetrics]);

  return {
    kpiData,
    gaugeData,
    chartData,
    comparisonData,
    tableData,
    heatmapData,
    rawMetrics,
    bdeScore,
    isLoading,
    error,
    refetch: fetchMetrics,
  };
}

export default useAnalyticsMetrics;
