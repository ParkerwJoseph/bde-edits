/**
 * BDE UI V2 - Scorecard Utility Functions
 *
 * Helper functions for score calculations, color determination,
 * formatting, and other scorecard-related utilities.
 */

import {
  SCORE_THRESHOLDS,
  CONFIDENCE_THRESHOLDS,
  EXIT_READINESS_THRESHOLDS,
  VALUATION_BANDS,
  SCORE_COLORS,
  type ScoreColor,
  type TrendDirection,
  type ValuationBand,
} from './constants';

// ===== Score Color Functions =====

/**
 * Get health status color from a 0-5 scale score
 */
export function getHealthStatus(score: number): ScoreColor {
  if (score >= SCORE_THRESHOLDS.green.min) return 'green';
  if (score >= SCORE_THRESHOLDS.yellow.min) return 'yellow';
  return 'red';
}

/**
 * Get score color configuration
 */
export function getScoreColorConfig(color: ScoreColor) {
  return SCORE_COLORS[color];
}

/**
 * Get CSS variable name for a score color
 */
export function getScoreCssVar(score: number): string {
  const color = getHealthStatus(score);
  return `var(--score-${color})`;
}

/**
 * Get the label for a health status
 */
export function getHealthLabel(score: number): string {
  if (score >= SCORE_THRESHOLDS.green.min) return 'Strong';
  if (score >= SCORE_THRESHOLDS.yellow.min) return 'Moderate';
  return 'At Risk';
}

// ===== Confidence Functions =====

/**
 * Get confidence level from percentage (0-100)
 */
export function getConfidenceLevel(confidence: number): 'high' | 'medium' | 'low' {
  if (confidence >= CONFIDENCE_THRESHOLDS.high.min) return 'high';
  if (confidence >= CONFIDENCE_THRESHOLDS.medium.min) return 'medium';
  return 'low';
}

/**
 * Get confidence color
 */
export function getConfidenceColor(confidence: number): ScoreColor {
  const level = getConfidenceLevel(confidence);
  if (level === 'high') return 'green';
  if (level === 'medium') return 'yellow';
  return 'red';
}

/**
 * Get confidence label
 */
export function getConfidenceLabel(confidence: number): string {
  const level = getConfidenceLevel(confidence);
  if (level === 'high') return 'High Confidence';
  if (level === 'medium') return 'Moderate Confidence';
  return 'Low Confidence';
}

// ===== Exit Readiness Functions =====

/**
 * Get exit readiness status from confidence score (0-100)
 */
export function getExitReadinessStatus(confidenceScore: number): 'ready' | 'conditional' | 'not-ready' {
  if (confidenceScore >= EXIT_READINESS_THRESHOLDS.ready.min) return 'ready';
  if (confidenceScore >= EXIT_READINESS_THRESHOLDS.conditional.min) return 'conditional';
  return 'not-ready';
}

/**
 * Get exit readiness configuration for UI rendering
 */
export function getExitReadinessConfig(confidenceScore: number) {
  const status = getExitReadinessStatus(confidenceScore);

  const configs = {
    ready: {
      label: 'Exit Ready',
      color: '#22c55e',
      bgColor: 'rgba(34, 197, 94, 0.1)',
      borderColor: 'rgba(34, 197, 94, 0.3)',
      glowColor: 'rgba(34, 197, 94, 0.3)',
    },
    conditional: {
      label: 'Conditional',
      color: '#f59e0b',
      bgColor: 'rgba(245, 158, 11, 0.1)',
      borderColor: 'rgba(245, 158, 11, 0.3)',
      glowColor: 'rgba(245, 158, 11, 0.3)',
    },
    'not-ready': {
      label: 'Not Ready',
      color: '#ef4444',
      bgColor: 'rgba(239, 68, 68, 0.1)',
      borderColor: 'rgba(239, 68, 68, 0.3)',
      glowColor: 'rgba(239, 68, 68, 0.3)',
    },
  };

  return configs[status];
}

// ===== Valuation Functions =====

/**
 * Get valuation band from score (0-5)
 */
export function getValuationBand(score: number): ValuationBand {
  for (const band of VALUATION_BANDS) {
    if (score >= band.minScore) return band;
  }
  return VALUATION_BANDS[VALUATION_BANDS.length - 1];
}

/**
 * Calculate valuation range from score and ARR
 */
export function calculateValuationRange(
  score: number,
  arr: number
): { low: number; high: number; band: string } {
  const band = getValuationBand(score);
  return {
    low: arr * band.multiples.low,
    high: arr * band.multiples.high,
    band: band.band,
  };
}

// ===== Score Conversion Functions =====

/**
 * Convert 0-100 score to 0-5 scale
 */
export function to5Scale(score100: number): number {
  return (score100 / 100) * 5;
}

/**
 * Convert 0-5 score to 0-100 scale
 */
export function to100Scale(score5: number): number {
  return (score5 / 5) * 100;
}

/**
 * Round score to one decimal place
 */
export function roundScore(score: number, decimals: number = 1): number {
  const factor = Math.pow(10, decimals);
  return Math.round(score * factor) / factor;
}

// ===== Trend Functions =====

/**
 * Calculate trend direction from delta
 */
export function getTrendDirection(delta: number, threshold: number = 0): TrendDirection {
  if (delta > threshold) return 'up';
  if (delta < -threshold) return 'down';
  return 'flat';
}

/**
 * Get trend color
 * Note: For metrics like churn or CAC, lower is better (invertColors = true)
 */
export function getTrendColor(
  delta: number,
  invertColors: boolean = false
): ScoreColor {
  const direction = getTrendDirection(delta);

  if (direction === 'flat') return 'yellow';

  if (invertColors) {
    // Lower is better (churn, CAC, etc.)
    return direction === 'down' ? 'green' : 'red';
  }

  // Higher is better (ARR, NRR, etc.)
  return direction === 'up' ? 'green' : 'red';
}

// ===== Formatting Functions =====

/**
 * Format a number as currency
 */
export function formatCurrency(
  value: number,
  options: { compact?: boolean; decimals?: number } = {}
): string {
  const { compact = true, decimals = 0 } = options;

  if (compact) {
    if (value >= 1_000_000_000) {
      return `$${(value / 1_000_000_000).toFixed(1)}B`;
    }
    if (value >= 1_000_000) {
      return `$${(value / 1_000_000).toFixed(1)}M`;
    }
    if (value >= 1_000) {
      return `$${(value / 1_000).toFixed(decimals)}K`;
    }
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format a number as percentage
 */
export function formatPercentage(
  value: number,
  options: { decimals?: number; includeSign?: boolean } = {}
): string {
  const { decimals = 0, includeSign = false } = options;
  const formatted = value.toFixed(decimals);
  const sign = includeSign && value > 0 ? '+' : '';
  return `${sign}${formatted}%`;
}

/**
 * Format delta/change value
 */
export function formatDelta(
  value: number,
  options: { decimals?: number; unit?: string } = {}
): string {
  const { decimals = 1, unit = '%' } = options;
  const sign = value > 0 ? '+' : '';
  return `${sign}${value.toFixed(decimals)}${unit}`;
}

/**
 * Format a metric value with appropriate unit
 */
export function formatMetricValue(
  value: number,
  unit?: string
): string {
  if (!unit) return value.toLocaleString();

  switch (unit.toLowerCase()) {
    case '$':
    case 'usd':
    case 'currency':
      return formatCurrency(value);
    case '%':
    case 'percent':
    case 'percentage':
      return formatPercentage(value);
    case 'days':
    case 'd':
      return `${value}d`;
    case 'months':
    case 'mo':
      return `${value}mo`;
    case 'x':
    case 'times':
    case 'multiple':
      return `${value.toFixed(1)}×`;
    default:
      return `${value.toLocaleString()} ${unit}`;
  }
}

/**
 * Format a large number with K/M/B suffixes
 */
export function formatCompactNumber(value: number): string {
  if (value >= 1_000_000_000) {
    return `${(value / 1_000_000_000).toFixed(1)}B`;
  }
  if (value >= 1_000_000) {
    return `${(value / 1_000_000).toFixed(1)}M`;
  }
  if (value >= 1_000) {
    return `${(value / 1_000).toFixed(1)}K`;
  }
  return value.toString();
}

// ===== Date/Time Functions =====

/**
 * Format a date for display
 */
export function formatDate(
  date: Date | string,
  options: Intl.DateTimeFormatOptions = {}
): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    ...options,
  });
}

/**
 * Get relative time string (e.g., "2 hours ago")
 */
export function getRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diffMs = now.getTime() - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMins / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  if (diffHours < 24) return `${diffHours}h ago`;
  if (diffDays < 7) return `${diffDays}d ago`;

  return formatDate(d);
}

// ===== Utility: cn (classnames helper) =====

// cn is now exported from utils.ts (uses clsx + tailwind-merge)
export { cn } from './utils';

// ===== Utility: Clamp =====

/**
 * Clamp a value between min and max
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

// ===== Utility: Calculate Ring Gauge Values =====

/**
 * Calculate SVG ring gauge values for a score
 */
export function calculateRingGaugeValues(
  score: number,
  maxScore: number = 100,
  radius: number = 40,
  strokeWidth: number = 8
) {
  const circumference = 2 * Math.PI * radius;
  const percentage = clamp(score / maxScore, 0, 1);
  const offset = circumference - percentage * circumference;

  return {
    circumference,
    offset,
    percentage,
    radius,
    strokeWidth,
    viewBox: `0 0 ${(radius + strokeWidth) * 2} ${(radius + strokeWidth) * 2}`,
    center: radius + strokeWidth,
  };
}
