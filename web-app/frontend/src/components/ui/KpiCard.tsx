/**
 * KpiCard Component
 *
 * A card component for displaying KPI metrics with value, label,
 * trend indicator, and optional icon.
 * Uses Tailwind CSS for styling (migrated from CSS Modules).
 */

import type { ReactNode, ElementType } from 'react';
import { cn, formatDelta, getHealthStatus } from '../../lib/scorecard-utils';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface KpiCardProps {
  /** KPI label/title */
  label: string;
  /** Main value to display */
  value: string | number;
  /** Change/delta from previous period */
  delta?: number;
  /** Whether delta is a percentage */
  deltaIsPercent?: boolean;
  /** Health status override (otherwise calculated from score) */
  status?: 'green' | 'yellow' | 'red' | 'neutral';
  /** Score value for automatic status calculation (0-5 scale) */
  score?: number;
  /** Icon component */
  icon?: ElementType;
  /** Additional content below the value */
  subtitle?: ReactNode;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class name */
  className?: string;
  /** Click handler */
  onClick?: () => void;
}

const iconColorMap: Record<string, string> = {
  green: 'bg-[hsl(var(--score-green)/0.1)] text-[hsl(var(--score-green))]',
  yellow: 'bg-[hsl(var(--score-yellow)/0.1)] text-[hsl(var(--score-yellow))]',
  red: 'bg-[hsl(var(--score-red)/0.1)] text-[hsl(var(--score-red))]',
  neutral: 'bg-muted text-muted-foreground',
};

const valueColorMap: Record<string, string> = {
  green: 'text-[hsl(var(--score-green))]',
  yellow: 'text-[hsl(var(--score-yellow))]',
  red: 'text-[hsl(var(--score-red))]',
  neutral: 'text-foreground',
};

const trendColorMap: Record<string, string> = {
  up: 'text-[hsl(var(--score-green))]',
  down: 'text-[hsl(var(--score-red))]',
  flat: 'text-muted-foreground',
};

const sizeStyles: Record<string, { card: string; label: string; value: string; icon: string; iconSize: number; trend?: string }> = {
  sm: {
    card: 'p-3 gap-1.5',
    label: 'text-[11px]',
    value: 'text-xl',
    icon: 'w-6 h-6',
    iconSize: 14,
  },
  md: {
    card: 'p-4 gap-2',
    label: 'text-xs',
    value: 'text-2xl',
    icon: 'w-7 h-7',
    iconSize: 16,
  },
  lg: {
    card: 'p-5 gap-3',
    label: 'text-[13px]',
    value: 'text-[32px]',
    icon: 'w-9 h-9',
    iconSize: 20,
    trend: 'text-sm',
  },
};

export function KpiCard({
  label,
  value,
  delta,
  deltaIsPercent = true,
  status,
  score,
  icon: Icon,
  subtitle,
  size = 'md',
  className,
  onClick,
}: KpiCardProps) {
  const statusColor = status || (score !== undefined ? getHealthStatus(score) : 'neutral');
  const trendDirection = delta === undefined || delta === 0 ? 'flat' : delta > 0 ? 'up' : 'down';
  const sizes = sizeStyles[size];

  const getTrendIcon = () => {
    if (delta === undefined || delta === 0) return Minus;
    return delta > 0 ? TrendingUp : TrendingDown;
  };

  const TrendIcon = getTrendIcon();

  return (
    <div
      className={cn(
        'flex flex-col rounded-lg border border-border bg-card transition-all duration-200',
        sizes.card,
        onClick && 'cursor-pointer hover:border-[hsl(var(--chart-1))] hover:shadow-md focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[hsl(var(--chart-1))]',
        className
      )}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
    >
      <div className="flex justify-between items-start">
        <span className={cn('font-medium text-muted-foreground uppercase tracking-[0.02em]', sizes.label)}>
          {label}
        </span>
        {Icon && (
          <div
            className={cn(
              'flex items-center justify-center rounded-md',
              sizes.icon,
              iconColorMap[statusColor]
            )}
          >
            <Icon size={sizes.iconSize} />
          </div>
        )}
      </div>

      <div className="flex items-baseline gap-2 flex-wrap">
        <span
          className={cn(
            'font-bold leading-none tabular-nums',
            sizes.value,
            valueColorMap[statusColor]
          )}
        >
          {value}
        </span>

        {delta !== undefined && (
          <div
            className={cn(
              'inline-flex items-center gap-0.5 text-xs font-medium',
              sizes.trend,
              trendColorMap[trendDirection]
            )}
          >
            <TrendIcon size={14} />
            <span>{formatDelta(delta, { unit: deltaIsPercent ? '%' : '' })}</span>
          </div>
        )}
      </div>

      {subtitle && (
        <div className="text-xs text-muted-foreground mt-1">
          {subtitle}
        </div>
      )}
    </div>
  );
}

export default KpiCard;
