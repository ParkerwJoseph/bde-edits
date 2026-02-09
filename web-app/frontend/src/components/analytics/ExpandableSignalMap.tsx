/**
 * ExpandableSignalMap Component
 *
 * Signal Map visualization showing value vs stability for business signals.
 * Matches reference UI with SVG-based matrix, hover tooltips, and modal expansion.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronRight, Expand, LayoutGrid, Waypoints, AlertCircle } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../ui/Dialog';
import styles from '../../styles/components/analytics/ExpandableSignalMap.module.css';

interface MatrixItem {
  id: string;
  signalId: string;
  name: string;
  shortName: string;
  x: number; // Value (0-100)
  y: number; // Stability (0-100)
  status: 'protect' | 'fix' | 'upside' | 'risk';
  
  value: string;
  description: string;
}


const QUADRANT_LABELS = [
  { label: 'Fix', x: 25, y: 75, desc: 'High value, fragile' },
  { label: 'Protect', x: 75, y: 75, desc: 'High value, stable' },
  { label: 'Risk', x: 25, y: 25, desc: 'Low value, fragile' },
  { label: 'Upside', x: 75, y: 25, desc: 'Growth potential' },
];

const LEGEND_ITEMS = [
  { status: 'protect', label: 'Protect', desc: 'High value, stable' },
  { status: 'fix', label: 'Fix', desc: 'High value, fragile' },
  { status: 'upside', label: 'Upside', desc: 'Growth potential' },
  { status: 'risk', label: 'Risk', desc: 'Low value, fragile' },
];

const getStatusColor = (status: string) => {
  switch (status) {
    case 'protect':
      return { fill: 'hsl(var(--kpi-strong))', glow: 'hsl(var(--kpi-strong) / 0.35)' };
    case 'fix':
      return { fill: 'hsl(var(--kpi-at-risk))', glow: 'hsl(var(--kpi-at-risk) / 0.35)' };
    case 'upside':
      return { fill: 'hsl(var(--primary))', glow: 'hsl(var(--primary) / 0.35)' };
    case 'risk':
      return { fill: 'hsl(var(--kpi-high-risk))', glow: 'hsl(var(--kpi-high-risk) / 0.35)' };
    default:
      return { fill: 'hsl(var(--chart-default))', glow: 'transparent' };
  }
};

type ComputedMatrixItem = MatrixItem & { cx: number; cy: number };

export interface ExpandableSignalMapProps {
  className?: string;
  defaultExpanded?: boolean;
  collapsible?: boolean;
  showFullscreen?: boolean;
  signals?: MatrixItem[];
  isLoading?: boolean;
}

export function ExpandableSignalMap({
  className,
  signals,
}: ExpandableSignalMapProps) {
  const navigate = useNavigate();
  // Only use provided signals - no fallback to mock data
  const displaySignals = signals && signals.length > 0 ? signals : [];
  const hasData = displaySignals.length > 0;
  const [isExpanded, setIsExpanded] = useState(false);
  const [hoveredItem, setHoveredItem] = useState<ComputedMatrixItem | null>(null);
  const [viewMode, setViewMode] = useState<'matrix' | 'cards'>('matrix');

  // Handle signal click - navigate to signal detail page
  const handleSignalClick = (signalId: string) => {
    setIsExpanded(false);
    navigate(`/signals/${signalId}`);
  };

  const containerRef = useRef<HTMLDivElement | null>(null);
  const [containerWidth, setContainerWidth] = useState<number>(0);

  useEffect(() => {
    if (viewMode !== 'matrix') return;
    if (!containerRef.current) return;

    const el = containerRef.current;
    const ro = new ResizeObserver((entries) => {
      const w = entries[0]?.contentRect?.width ?? 0;
      setContainerWidth(w);
    });

    ro.observe(el);
    setContainerWidth(el.getBoundingClientRect().width);

    return () => ro.disconnect();
  }, [viewMode]);

  const compactSize = useMemo(() => {
    const max = 320;
    const min = 248;
    const available = Math.max(0, containerWidth - 8);
    if (!available) return max;
    return Math.max(min, Math.min(max, Math.floor(available)));
  }, [containerWidth]);

  // Compact view settings
  const chartSize = compactSize;
  const padding = Math.max(18, Math.round(chartSize * 0.075));
  const innerSize = chartSize - padding * 2;

  // Modal view settings
  const modalSize = 500;
  const modalPadding = 50;
  const modalInner = modalSize - modalPadding * 2;

  const items: ComputedMatrixItem[] = useMemo(() => {
    return displaySignals.map(item => ({
      ...item,
      cx: padding + (item.x / 100) * innerSize,
      cy: padding + ((100 - item.y) / 100) * innerSize,
    }));
  }, [displaySignals, padding, innerSize]);

  const modalItems: ComputedMatrixItem[] = useMemo(() => {
    return displaySignals.map(item => ({
      ...item,
      cx: modalPadding + (item.x / 100) * modalInner,
      cy: modalPadding + ((100 - item.y) / 100) * modalInner,
    }));
  }, [displaySignals, modalPadding, modalInner]);

  const renderMatrix = (size: number, padSize: number, inner: number, computedItems: ComputedMatrixItem[], isModal: boolean) => (
    <div className={styles.matrixContainer}>
      {/* Tooltip */}
      {hoveredItem && (
        <div
          className={styles.tooltip}
          style={{
            left: hoveredItem.cx > size / 2 ? 'auto' : hoveredItem.cx + 20,
            right: hoveredItem.cx > size / 2 ? size - hoveredItem.cx + 20 : 'auto',
            top: hoveredItem.cy - 10,
          }}
        >
          <div className={styles.tooltipHeader}>
            <div
              className={styles.tooltipDot}
              style={{ backgroundColor: getStatusColor(hoveredItem.status).fill }}
            />
            <span className={styles.tooltipName}>{hoveredItem.name}</span>
          </div>
          <div className={styles.tooltipBody}>
            <div className={styles.tooltipRow}>
              <span className={styles.tooltipLabel}>Value</span>
              <span className={styles.tooltipValue}>{hoveredItem.value}</span>
            </div>
            <p className={styles.tooltipDesc}>{hoveredItem.description}</p>
            {isModal && (
              <p className={styles.tooltipAction}>Click to view details</p>
            )}
          </div>
        </div>
      )}

      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className={styles.svgMatrix}
      >
        <defs>
          {/* Grid pattern */}
          <pattern id={`smallGrid-${isModal ? 'modal' : 'card'}`} width="10" height="10" patternUnits="userSpaceOnUse">
            <path d="M 10 0 L 0 0 0 10" fill="none" stroke="hsl(var(--border))" strokeWidth="0.3" opacity="0.5"/>
          </pattern>
          <pattern id={`grid-${isModal ? 'modal' : 'card'}`} width="52" height="52" patternUnits="userSpaceOnUse">
            <rect width="52" height="52" fill={`url(#smallGrid-${isModal ? 'modal' : 'card'})`}/>
            <path d="M 52 0 L 0 0 0 52" fill="none" stroke="hsl(var(--border))" strokeWidth="0.5"/>
          </pattern>
        </defs>

        {/* Background grid */}
        <rect x={padSize} y={padSize} width={inner} height={inner} fill={`url(#grid-${isModal ? 'modal' : 'card'})`} opacity="0.6" />

        {/* Quadrant backgrounds - color-coded */}
        <rect x={padSize} y={padSize} width={inner / 2} height={inner / 2}
          fill="hsl(var(--kpi-at-risk))" fillOpacity="0.08" />
        <rect x={padSize + inner / 2} y={padSize} width={inner / 2} height={inner / 2}
          fill="hsl(var(--kpi-strong))" fillOpacity="0.08" />
        <rect x={padSize} y={padSize + inner / 2} width={inner / 2} height={inner / 2}
          fill="hsl(var(--kpi-high-risk))" fillOpacity="0.08" />
        <rect x={padSize + inner / 2} y={padSize + inner / 2} width={inner / 2} height={inner / 2}
          fill="hsl(var(--primary))" fillOpacity="0.08" />

        {/* Axis lines */}
        <line x1={padSize} y1={padSize + inner / 2} x2={padSize + inner} y2={padSize + inner / 2}
          stroke="hsl(var(--border))" strokeWidth="1" strokeDasharray="4 4" />
        <line x1={padSize + inner / 2} y1={padSize} x2={padSize + inner / 2} y2={padSize + inner}
          stroke="hsl(var(--border))" strokeWidth="1" strokeDasharray="4 4" />

        {/* Outer border */}
        <rect x={padSize} y={padSize} width={inner} height={inner}
          fill="none" stroke="hsl(var(--border))" strokeWidth="1" />

        {/* Axis labels */}
        <text x={size / 2} y={size - 8} textAnchor="middle" className={styles.axisLabel}>
          VALUE
        </text>
        <text x={12} y={size / 2} textAnchor="middle" className={styles.axisLabelVertical}
          style={{ transform: `rotate(-90deg)`, transformOrigin: `12px ${size / 2}px` }}>
          STABILITY
        </text>

        {/* Quadrant labels */}
        {QUADRANT_LABELS.map((q, i) => (
          <text
            key={i}
            x={padSize + (q.x / 100) * inner}
            y={padSize + ((100 - q.y) / 100) * inner}
            textAnchor="middle"
            dominantBaseline="middle"
            className={styles.quadrantLabel}
          >
            {q.label}
          </text>
        ))}

        {/* Data points with hover effects */}
        {computedItems.map((item, index) => {
          const colors = getStatusColor(item.status);
          const isHovered = hoveredItem?.id === item.id;
          const dotSize = isModal ? 22 : 16;

          return (
            <g
              key={item.id}
              className={styles.signalGroup}
              style={{
                animationDelay: `${index * 60}ms`,
              }}
              onMouseEnter={() => setHoveredItem(item)}
              onMouseLeave={() => setHoveredItem(null)}
              onClick={() => isModal && handleSignalClick(item.signalId)}
            >
              {/* Glow ring on hover */}
              {isHovered && (
                <circle
                  cx={item.cx}
                  cy={item.cy}
                  r={dotSize + 8}
                  fill="none"
                  stroke={colors.fill}
                  strokeWidth="2"
                  opacity="0.4"
                  style={{ filter: 'blur(4px)' }}
                />
              )}

              {/* Outer ring */}
              <circle
                cx={item.cx}
                cy={item.cy}
                r={isHovered ? dotSize + 3 : dotSize}
                fill={colors.fill}
                style={{
                  transition: 'all 0.15s ease-out',
                  filter: isHovered ? `drop-shadow(0 0 12px ${colors.glow})` : 'none',
                }}
              />

              {/* Label */}
              <text
                x={item.cx}
                y={item.cy}
                textAnchor="middle"
                dominantBaseline="middle"
                fill="white"
                className={cn(styles.signalLabel, isHovered && styles.signalLabelHovered)}
                style={{ fontSize: isModal ? (isHovered ? '10px' : '9px') : (isHovered ? '8px' : '7px') }}
              >
                {item.shortName}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );

  // Card Grid View
  const renderCardGrid = () => (
    <div className={styles.cardGrid}>
      {displaySignals.map((signal) => {
        const colors = getStatusColor(signal.status);
        return (
          <div key={signal.id} className={styles.signalCard}>
            <div className={styles.signalCardHeader}>
              <div
                className={styles.signalCardIcon}
                style={{ backgroundColor: colors.fill }}
              >
                <span>{signal.shortName}</span>
              </div>
            </div>
            <div className={styles.signalCardBody}>
              <p className={styles.signalCardName}>{signal.name}</p>
              <p className={styles.signalCardValue}>{signal.value}</p>
              <p className={styles.signalCardDesc}>{signal.description}</p>
            </div>
          </div>
        );
      })}
    </div>
  );

  return (
    <>
      <div
        className={cn(
          styles.container,
          viewMode === 'matrix' && hasData && styles.containerClickable,
          className
        )}
        onClick={() => viewMode === 'matrix' && hasData && setIsExpanded(true)}
      >
        {/* Header */}
        <div className={styles.header}>
          <div className={styles.headerLeft}>
            <h3 className={styles.title}>Signal Map</h3>
            <p className={styles.subtitle}>Value vs. stability positioning</p>
          </div>
          <div className={styles.headerRight}>
            {hasData && (
              <>
                {/* View Toggle */}
                <div className={styles.viewToggle}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setViewMode('matrix');
                    }}
                    className={cn(styles.toggleBtn, viewMode === 'matrix' && styles.toggleBtnActive)}
                    title="Matrix View"
                  >
                    <Waypoints size={14} />
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      setViewMode('cards');
                    }}
                    className={cn(styles.toggleBtn, viewMode === 'cards' && styles.toggleBtnActive)}
                    title="Card View"
                  >
                    <LayoutGrid size={14} />
                  </button>
                </div>
                <span className={styles.signalCount}>{displaySignals.length} signals</span>
                {viewMode === 'matrix' && (
                  <Expand size={16} className={styles.expandIcon} />
                )}
              </>
            )}
          </div>
        </div>

        {/* Conditional View Render */}
        {!hasData ? (
          <div className={styles.emptyState}>
            <AlertCircle size={40} className={styles.emptyIcon} />
            <h4 className={styles.emptyTitle}>No Signal Data</h4>
            <p className={styles.emptyText}>
              Run an analysis to generate signal data for this company.
            </p>
          </div>
        ) : viewMode === 'matrix' ? (
          <>
            <div ref={containerRef} className={styles.matrixWrapper}>
              {renderMatrix(chartSize, padding, innerSize, items, false)}
            </div>

            {/* Legend */}
            <div className={styles.legend}>
              {LEGEND_ITEMS.map((item) => (
                <div key={item.status} className={styles.legendItem}>
                  <div
                    className={styles.legendDot}
                    style={{ backgroundColor: getStatusColor(item.status).fill }}
                  />
                  <span className={styles.legendLabel}>{item.label}</span>
                </div>
              ))}
            </div>
          </>
        ) : (
          renderCardGrid()
        )}
      </div>

      {/* Expanded Modal View - only render when there's data */}
      {hasData && (
        <Dialog open={isExpanded} onOpenChange={setIsExpanded}>
          <DialogContent className={styles.modalContent}>
            <DialogHeader>
              <DialogTitle>Signal Map</DialogTitle>
              <p className={styles.modalSubtitle}>
                Click on any signal bubble to view related documents and detailed analysis
              </p>
            </DialogHeader>

            <div className={styles.modalMatrixWrapper}>
              {renderMatrix(modalSize, modalPadding, modalInner, modalItems, true)}
            </div>

            {/* Legend with descriptions */}
            <div className={styles.modalLegend}>
              {LEGEND_ITEMS.map((item) => (
                <div key={item.status} className={styles.modalLegendItem}>
                  <div
                    className={styles.modalLegendDot}
                    style={{ backgroundColor: getStatusColor(item.status).fill }}
                  />
                  <div>
                    <span className={styles.modalLegendLabel}>{item.label}</span>
                    <p className={styles.modalLegendDesc}>{item.desc}</p>
                  </div>
                </div>
              ))}
            </div>

            {/* Signal List */}
            <div className={styles.modalSignalList}>
              <p className={styles.modalSignalListTitle}>All Signals</p>
              <div className={styles.modalSignalGrid}>
                {displaySignals.map((signal) => {
                  const colors = getStatusColor(signal.status);
                  return (
                    <button
                      key={signal.id}
                      className={styles.modalSignalItem}
                      onClick={() => handleSignalClick(signal.signalId)}
                    >
                      <div
                        className={styles.modalSignalIcon}
                        style={{ backgroundColor: colors.fill }}
                      >
                        <span>{signal.shortName}</span>
                      </div>
                      <div className={styles.modalSignalContent}>
                        <p className={styles.modalSignalName}>{signal.name}</p>
                        <p className={styles.modalSignalValue}>{signal.value}</p>
                      </div>
                      <ChevronRight size={16} className={styles.modalSignalChevron} />
                    </button>
                  );
                })}
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
}

export default ExpandableSignalMap;
