/**
 * AcronymTooltip Component
 *
 * Displays business acronyms with hover tooltips showing their full meaning.
 * Can wrap individual acronyms or automatically detect and wrap acronyms in text.
 * Uses Tailwind CSS + Radix Tooltip (migrated from CSS Modules).
 */

import { Fragment, type ReactNode } from 'react';
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
} from './Tooltip';
import { cn } from '../../lib/scorecard-utils';
import {
  getAcronymDefinition,
  createAcronymPattern,
  type AcronymDefinition,
} from '../../lib/acronyms';

export interface AcronymTooltipProps {
  /** The acronym to display (e.g., "ARR", "NRR") */
  acronym: string;
  /** Optional custom definition (overrides built-in) */
  definition?: AcronymDefinition;
  /** Whether to show the acronym with underline styling */
  showUnderline?: boolean;
  /** Additional class name */
  className?: string;
}

/**
 * Single acronym with tooltip
 */
export function AcronymTooltip({
  acronym,
  definition: customDefinition,
  showUnderline = true,
  className,
}: AcronymTooltipProps) {
  const definition = customDefinition || getAcronymDefinition(acronym);

  if (!definition) {
    return <span className={className}>{acronym}</span>;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              'cursor-help font-medium',
              showUnderline && 'underline decoration-dotted decoration-muted-foreground underline-offset-2',
              'hover:text-primary',
              className
            )}
          >
            {acronym}
          </span>
        </TooltipTrigger>
        <TooltipContent className="max-w-[300px] p-3" side="top">
          <div className="flex flex-col gap-2">
            <div className="flex flex-col gap-0.5">
              <span className="text-sm font-bold text-popover-foreground">
                {definition.acronym}
              </span>
              <span className="text-[13px] font-medium text-muted-foreground">
                {definition.fullName}
              </span>
            </div>
            <p className="m-0 text-xs leading-relaxed text-muted-foreground">
              {definition.description}
            </p>
            <span className="inline-block self-start rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wider text-muted-foreground">
              {definition.category}
            </span>
          </div>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * Props for AcronymText component
 */
export interface AcronymTextProps {
  /** Text that may contain acronyms */
  children: string;
  /** Whether to show underline on acronyms */
  showUnderline?: boolean;
  /** Additional class name for the wrapper */
  className?: string;
  /** Additional class name for acronym spans */
  acronymClassName?: string;
}

/**
 * Automatically detect and wrap acronyms in text
 *
 * Usage:
 * ```tsx
 * <AcronymText>
 *   Revenue quality is strong with 115% NRR. Customer ARR grew 24% YoY.
 * </AcronymText>
 * ```
 */
export function AcronymText({
  children,
  showUnderline = true,
  className,
  acronymClassName,
}: AcronymTextProps) {
  const pattern = createAcronymPattern();
  const parts: ReactNode[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  pattern.lastIndex = 0;

  while ((match = pattern.exec(children)) !== null) {
    if (match.index > lastIndex) {
      parts.push(children.slice(lastIndex, match.index));
    }

    const acronym = match[1];
    parts.push(
      <AcronymTooltip
        key={`${acronym}-${match.index}`}
        acronym={acronym}
        showUnderline={showUnderline}
        className={acronymClassName}
      />
    );

    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < children.length) {
    parts.push(children.slice(lastIndex));
  }

  if (parts.length === 0) {
    return <span className={className}>{children}</span>;
  }

  return (
    <span className={className}>
      {parts.map((part, index) => (
        <Fragment key={index}>{part}</Fragment>
      ))}
    </span>
  );
}

/**
 * Hook to check if text contains known acronyms
 */
export function useHasAcronyms(text: string): boolean {
  const pattern = createAcronymPattern();
  return pattern.test(text);
}

export default AcronymTooltip;
