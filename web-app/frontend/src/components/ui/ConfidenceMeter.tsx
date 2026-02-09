/**
 * ConfidenceMeter Component
 *
 * Displays a confidence level indicator with a filled bar and label.
 * Uses Tailwind CSS for styling (migrated from CSS Modules).
 */

import { useMemo } from 'react';
import { cn, getConfidenceColor, getConfidenceLabel } from '../../lib/scorecard-utils';

export interface ConfidenceMeterProps {
  /** Confidence value (0-100) */
  value: number;
  /** Show the percentage label */
  showLabel?: boolean;
  /** Show the status text (High, Medium, Low) */
  showStatus?: boolean;
  /** Size variant */
  size?: 'sm' | 'md' | 'lg';
  /** Additional class name */
  className?: string;
}

const fillColorMap: Record<string, string> = {
  green: 'bg-[hsl(var(--score-green))]',
  yellow: 'bg-[hsl(var(--score-yellow))]',
  red: 'bg-[hsl(var(--score-red))]',
};

const textColorMap: Record<string, string> = {
  green: 'text-[hsl(var(--score-green))]',
  yellow: 'text-[hsl(var(--score-yellow))]',
  red: 'text-[hsl(var(--score-red))]',
};

const trackHeightMap: Record<string, string> = {
  sm: 'h-1',
  md: 'h-1.5',
  lg: 'h-2',
};

const labelSizeMap: Record<string, string> = {
  sm: 'text-[10px] min-w-7',
  md: 'text-xs min-w-9',
  lg: 'text-sm min-w-11',
};

const statusSizeMap: Record<string, string> = {
  sm: 'text-[10px]',
  md: 'text-[11px]',
  lg: 'text-xs',
};

export function ConfidenceMeter({
  value,
  showLabel = true,
  showStatus = false,
  size = 'md',
  className,
}: ConfidenceMeterProps) {
  const clampedValue = Math.max(0, Math.min(100, value));

  const { level, color } = useMemo(() => {
    const colorStr = getConfidenceColor(clampedValue);
    const labelStr = getConfidenceLabel(clampedValue);
    return { level: labelStr, color: colorStr };
  }, [clampedValue]);

  return (
    <div className={cn('flex flex-col gap-1', className)}>
      <div className="flex items-center gap-2">
        <div
          className={cn(
            'flex-1 rounded-full overflow-hidden bg-muted',
            trackHeightMap[size]
          )}
        >
          <div
            className={cn(
              'h-full rounded-full transition-[width] duration-300 ease-in-out',
              fillColorMap[color]
            )}
            style={{ width: `${clampedValue}%` }}
          />
        </div>
        {showLabel && (
          <span
            className={cn(
              'font-semibold tabular-nums text-right',
              labelSizeMap[size],
              textColorMap[color]
            )}
          >
            {clampedValue}%
          </span>
        )}
      </div>
      {showStatus && (
        <span
          className={cn(
            'font-medium uppercase tracking-wide',
            statusSizeMap[size],
            textColorMap[color]
          )}
        >
          {level}
        </span>
      )}
    </div>
  );
}

export default ConfidenceMeter;
