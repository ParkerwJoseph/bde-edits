/**
 * Analytics Components
 *
 * Barrel export for analytics page components
 */

// Card Registry
export {
  DEFAULT_ANALYTICS_CARDS,
  CATEGORY_LABELS,
  getCardGridSpan,
  getCardHeight,
  renderAnalyticsCard,
  KPICard,
  GaugeCard,
  ChartCard,
  ComparisonCard,
  HeatmapCard,
  TableCard,
  AnalyticsMetricsProvider,
} from './AnalyticsCardRegistry';
export type {
  AnalyticsCardConfig,
  CardCategory,
  CardSize,
  AnalyticsMetricsContextType,
} from './AnalyticsCardRegistry';

// Draggable Card
export { DraggableCard } from './DraggableCard';
export type { DraggableCardProps } from './DraggableCard';

// Analytics Customizer
export { AnalyticsCustomizer } from './AnalyticsCustomizer';
export type { AnalyticsCustomizerProps } from './AnalyticsCustomizer';

// Value Fragility Matrix (Signal Map)
export { ValueFragilityMatrix } from './ValueFragilityMatrix';
export type { ValueFragilityMatrixProps, Signal } from './ValueFragilityMatrix';

// Expandable Signal Map
export { ExpandableSignalMap } from './ExpandableSignalMap';
export type { ExpandableSignalMapProps } from './ExpandableSignalMap';

// Pillar Scorecard
export { PillarScorecard } from './PillarScorecard';
export type { PillarScorecardProps, PillarScore } from './PillarScorecard';
