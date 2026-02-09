/**
 * Analytics Page
 *
 * Customizable analytics dashboard with:
 * - 8-pillar scorecard grid
 * - Signal Map visualization
 * - Trend Analysis (Growth Forecast + Revenue Concentration)
 * - Drag-and-drop customizable card grid
 * - Analytics customizer panel
 */

import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  BarChart3,
  Boxes,
  Pencil,
  Check,
  LayoutGrid,
} from 'lucide-react';
import { AppLayout } from '../components/layout/AppLayout';
import { Button } from '../components/ui/Button';
import { PageLoader } from '../components/common/PageLoader';
import { GrowthForecast, RevenueConcentration } from '../components/home';
import {
  DraggableCard,
  AnalyticsCustomizer,
  ExpandableSignalMap,
  PillarScorecard,
  type PillarScore,
  AnalyticsMetricsProvider,
} from '../components/analytics';
import { useAnalyticsLayout } from '../hooks/useAnalyticsLayout';
import { useCompany } from '../contexts/CompanyContext';
import { useBDEScore, useFlags } from '../hooks/useScoring';
import { useAnalyticsMetrics } from '../hooks/useAnalyticsMetrics';
import { type BDEPillar, PILLAR_CONFIG } from '../api/scoringApi';
import styles from '../styles/pages/Analytics.module.css';

// Define pillar order explicitly
const PILLAR_ORDER: BDEPillar[] = [
  'financial_health',
  'gtm_engine',
  'customer_health',
  'product_technical',
  'operational_maturity',
  'leadership_transition',
  'ecosystem_dependency',
  'service_software_ratio',
];

// Short names for signal map
const PILLAR_SHORT_NAMES: Record<BDEPillar, string> = {
  financial_health: 'Fin',
  gtm_engine: 'GTM',
  customer_health: 'Cust',
  product_technical: 'Prod',
  operational_maturity: 'Ops',
  leadership_transition: 'Lead',
  ecosystem_dependency: 'Eco',
  service_software_ratio: 'S2S',
};

export default function Analytics() {
  const navigate = useNavigate();
  const [isEditMode, setIsEditMode] = useState(false);
  const { selectedCompanyId } = useCompany();
  const { data: score, isLoading: scoreLoading } = useBDEScore(selectedCompanyId);
  const { data: flags, isLoading: flagsLoading } = useFlags(selectedCompanyId);

  // Fetch metrics data for analytics cards
  const {
    kpiData,
    gaugeData,
    chartData,
    comparisonData,
    tableData,
    heatmapData,
    isLoading: metricsLoading,
  } = useAnalyticsMetrics(selectedCompanyId);

  const {
    cards,
    enabledCards,
    updateCards,
    toggleCard,
    resetToDefaults,
    moveCard,
  } = useAnalyticsLayout();

  // Transform pillar scores for PillarScorecard component
  const pillarScores = useMemo(() => {
    if (!score?.pillar_scores) return undefined;

    const result: Record<BDEPillar, PillarScore> = {} as Record<BDEPillar, PillarScore>;

    Object.entries(score.pillar_scores).forEach(([key, pillar]) => {
      // Derive trend from health status until historical data is available
      const trend: 'up' | 'down' | 'flat' =
        pillar.health_status === 'green' ? 'up' :
        pillar.health_status === 'red' ? 'down' : 'flat';

      result[key as BDEPillar] = {
        score: pillar.score,
        health_status: pillar.health_status,
        confidence: pillar.confidence, // Already 0-100 from API
        data_coverage: pillar.data_coverage, // Already 0-100 from API
        trend,
      };
    });

    return result;
  }, [score?.pillar_scores]);

  // Calculate pillar stats
  const pillarStats = useMemo(() => {
    if (!score?.pillar_scores) {
      return { strong: 0, moderate: 0, atRisk: 0 };
    }

    let strong = 0;
    let moderate = 0;
    let atRisk = 0;

    Object.values(score.pillar_scores).forEach((pillar) => {
      if (pillar.health_status === 'green') strong++;
      else if (pillar.health_status === 'yellow') moderate++;
      else if (pillar.health_status === 'red') atRisk++;
    });

    return { strong, moderate, atRisk };
  }, [score?.pillar_scores]);

  // Transform pillar scores and flags into Signal Map data
  const signalMapData = useMemo(() => {
    if (!score?.pillar_scores) return undefined;

    const signals: Array<{
      id: string;
      signalId: string;
      name: string;
      shortName: string;
      x: number;
      y: number;
      status: 'protect' | 'fix' | 'upside' | 'risk';
      value: string;
      description: string;
    }> = [];

    // Transform pillar scores into signals
    PILLAR_ORDER.forEach((pillarId, index) => {
      const pillar = score.pillar_scores[pillarId];
      if (!pillar) return;

      const config = PILLAR_CONFIG[pillarId];

      // X-axis: VALUE based on score (0-5 scale → 0-100)
      const valueScore = (pillar.score / 5) * 100;

      // Y-axis: STABILITY based on confidence and data coverage
      const stabilityScore = ((pillar.confidence + pillar.data_coverage) / 2);

      // Determine status based on quadrant
      let status: 'protect' | 'fix' | 'upside' | 'risk';
      if (valueScore >= 50 && stabilityScore >= 50) {
        status = 'protect';
      } else if (valueScore >= 50 && stabilityScore < 50) {
        status = 'fix';
      } else if (valueScore < 50 && stabilityScore >= 50) {
        status = 'upside';
      } else {
        status = 'risk';
      }

      // Create display value
      const displayValue = `${pillar.score.toFixed(1)}/5`;

      // Create description based on health status
      const healthDesc = pillar.health_status === 'green'
        ? 'Performing well'
        : pillar.health_status === 'yellow'
        ? 'Needs attention'
        : 'Critical concern';

      signals.push({
        id: String(index + 1),
        signalId: pillarId,
        name: config.label,
        shortName: PILLAR_SHORT_NAMES[pillarId],
        x: Math.max(5, Math.min(95, valueScore)),
        y: Math.max(5, Math.min(95, stabilityScore)),
        status,
        value: displayValue,
        description: `${healthDesc} - ${Math.round(pillar.confidence)}% confidence`,
      });
    });

    return signals.length > 0 ? signals : undefined;
  }, [score?.pillar_scores]);

  // GrowthForecast data - requires historical time-series endpoint (not available)
  // Will show empty state until API endpoint is implemented
  const growthForecastData = undefined;

  // RevenueConcentration data - calculated from TopAccountsList metric
  const revenueConcentrationData = useMemo(() => {
    // Get TopAccountsList from tableData
    const topAccountsItems = tableData['top-accounts']?.items;
    if (!topAccountsItems || topAccountsItems.length === 0) {
      return undefined;
    }

    // Parse numeric values from the items (remove $ and K/M suffixes)
    const parseValue = (valueStr: string): number => {
      const cleaned = valueStr.replace(/[$,]/g, '');
      if (cleaned.includes('M')) {
        return parseFloat(cleaned.replace('M', '')) * 1000000;
      }
      if (cleaned.includes('K')) {
        return parseFloat(cleaned.replace('K', '')) * 1000;
      }
      return parseFloat(cleaned) || 0;
    };

    // Get revenue values for each account
    const revenueValues = topAccountsItems.map(item => parseValue(item.value));
    const totalRevenue = revenueValues.reduce((sum, val) => sum + val, 0);

    if (totalRevenue === 0) {
      return undefined;
    }

    // Calculate concentration tiers
    const top1Revenue = revenueValues[0] || 0;
    const top2to5Revenue = revenueValues.slice(1, 5).reduce((sum, val) => sum + val, 0);
    const remainingRevenue = revenueValues.slice(5).reduce((sum, val) => sum + val, 0);

    // If we only have top accounts data, calculate remaining as what's left to make 100%
    // Assuming TopAccountsList represents some concentration percentage
    const top1Pct = (top1Revenue / totalRevenue) * 100;
    const top2to5Pct = (top2to5Revenue / totalRevenue) * 100;
    const remainingPct = 100 - top1Pct - top2to5Pct;

    return {
      top1Pct: Math.round(top1Pct * 10) / 10,
      top2to5Pct: Math.round(top2to5Pct * 10) / 10,
      remainingPct: Math.max(0, Math.round(remainingPct * 10) / 10),
    };
  }, [tableData]);

  // Handle card removal (disable card)
  const handleRemoveCard = (cardId: string) => {
    toggleCard(cardId);
  };

  // Handle pillar click
  const handlePillarClick = (pillarId: string) => {
    navigate(`/analytics/pillar/${pillarId}`);
  };

  // Combined loading state
  const isLoading = scoreLoading || flagsLoading || metricsLoading;

  // Show loading state while fetching initial data
  if (isLoading && !score && !flags) {
    return (
      <AppLayout title="Analytics">
        <PageLoader message="Loading analytics data..." size="lg" />
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Analytics">
      <div className={styles.container}>
        {/* Header — full width border-bottom, inner content max-width constrained */}
        <header className={styles.header}>
          <div className={styles.headerContent}>
            <div className={styles.headerRow}>
              <div className={styles.headerLeft}>
                <p className={styles.headerSubtitle}>The Intelligence Layer</p>
                <h1 className={styles.pageTitle}>Analytics & Metrics</h1>
              </div>
              <div className={styles.headerActions}>
                <div className={styles.headerBadges}>
                  <div className={styles.headerBadge}>
                    <BarChart3 size={16} />
                    <span>{enabledCards.length} Cards</span>
                  </div>
                  <div className={styles.headerBadge}>
                    <Boxes size={16} />
                    <span>8 Pillars</span>
                  </div>
                </div>
                <Button
                  variant={isEditMode ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setIsEditMode(!isEditMode)}
                  className={styles.editButton}
                >
                  {isEditMode ? (
                    <>
                      <Check size={16} />
                      <span className={styles.editButtonText}>Done</span>
                    </>
                  ) : (
                    <>
                      <Pencil size={16} />
                      <span className={styles.editButtonText}>Edit Layout</span>
                    </>
                  )}
                </Button>
                <AnalyticsCustomizer
                  cards={cards}
                  onCardsChange={updateCards}
                  onReset={resetToDefaults}
                />
              </div>
            </div>

            {/* Edit Mode Banner */}
            {isEditMode && (
              <div className={styles.editBanner}>
                <LayoutGrid size={20} className={styles.editBannerIcon} />
                <div className={styles.editBannerContent}>
                  <p className={styles.editBannerTitle}>Edit Mode Active</p>
                  <p className={styles.editBannerText}>
                    Drag cards to reorder, click × to remove, or use the Customize panel to add more cards
                  </p>
                </div>
                <Button variant="ghost" size="sm" onClick={() => setIsEditMode(false)}>
                  Done Editing
                </Button>
              </div>
            )}
          </div>
        </header>

        {/* Main content sections — matches reference px-6 lg:px-8 py-8 */}
        <div className={styles.sectionsWrapper}>
          <div className={styles.sectionsContent}>
        {/* 8-Pillar Scorecard Grid */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleWrapper}>
              <div className={styles.sectionIndicator} />
              <h2 className={styles.sectionTitle}>8-Pillar Scorecard</h2>
            </div>
            <div className={styles.sectionStats}>
              <span className={styles.statStrong}>{pillarStats.strong} Strong</span>
              <span className={styles.statSeparator}>•</span>
              <span className={styles.statModerate}>{pillarStats.moderate} Moderate</span>
              <span className={styles.statSeparator}>•</span>
              <span className={styles.statAtRisk}>{pillarStats.atRisk} At Risk</span>
            </div>
          </div>
          <PillarScorecard pillarScores={pillarScores} onPillarClick={handlePillarClick} />
        </section>

        {/* Signal Map & Trend Analysis - Side by side */}
        <section className={styles.twoColumnSection}>
          <div className={styles.twoColumnItem}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitleWrapper}>
                <div className={styles.sectionIndicator} />
                <h2 className={styles.sectionTitle}>Signal Map</h2>
              </div>
            </div>
            <ExpandableSignalMap
              defaultExpanded={true}
              collapsible={false}
              showFullscreen={true}
              signals={signalMapData}
            />
          </div>

          <div className={styles.twoColumnItem}>
            <div className={styles.sectionHeader}>
              <div className={styles.sectionTitleWrapper}>
                <div className={styles.sectionIndicator} />
                <h2 className={styles.sectionTitle}>Trend Analysis</h2>
              </div>
            </div>
            <div className={styles.trendAnalysisContent}>
              <GrowthForecast data={growthForecastData} />
              <RevenueConcentration concentrationData={revenueConcentrationData} />
            </div>
          </div>
        </section>

        {/* Customizable Cards Grid */}
        <section className={styles.section}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionTitleWrapper}>
              <div className={styles.sectionIndicator} />
              <h2 className={styles.sectionTitle}>Custom Dashboard</h2>
            </div>
            <span className={styles.sectionHint}>
              {enabledCards.length} of {cards.length} cards visible
            </span>
          </div>

          <AnalyticsMetricsProvider
            value={{
              kpiData,
              gaugeData,
              chartData,
              comparisonData,
              tableData,
              heatmapData,
              isLoading: metricsLoading,
            }}
          >
            {enabledCards.length === 0 ? (
              <div className={styles.emptyState}>
                <LayoutGrid size={48} className={styles.emptyIcon} />
                <h4 className={styles.emptyTitle}>No cards enabled</h4>
                <p className={styles.emptyText}>
                  Click "Customize" to add cards to your dashboard.
                </p>
              </div>
            ) : (
              <div className={styles.cardsGrid}>
                {enabledCards.map((card, index) => (
                  <DraggableCard
                    key={card.id}
                    card={card}
                    index={index}
                    onMove={moveCard}
                    onRemove={handleRemoveCard}
                    isEditMode={isEditMode}
                  />
                ))}
              </div>
            )}
          </AnalyticsMetricsProvider>
        </section>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
