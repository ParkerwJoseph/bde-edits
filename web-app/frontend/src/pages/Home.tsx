/**
 * Home Page (Exit Readiness Overview)
 *
 * New UI V2 home page with exit readiness score, pillar strip,
 * top risks, multiple improvers, and AI chat bar.
 */

import { useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import {
  ExitReadinessHero,
  PillarStrip,
  TopExitRisks,
  MultipleImprovers,
  MinimalChatBar,
  CustomerHealthGrid,
  RiskRadar,
} from '../components/home';
import { ExpandableSignalMap } from '../components/analytics';
import { Separator } from '../components/ui/Separator';
import { PageLoader } from '../components/common/PageLoader';
import { useCompany } from '../contexts/CompanyContext';
import { useHomePageData } from '../hooks/useScoring';
import {
  type BDEPillar,
  PILLAR_CONFIG,
} from '../api/scoringApi';
import {
  DollarSign,
  Target,
  Users,
  Cpu,
  Settings,
  Crown,
  Network,
  ArrowRightLeft,
  type LucideIcon,
} from 'lucide-react';
import styles from '../styles/pages/Home.module.css';

// Define pillar order explicitly (Object.entries doesn't guarantee order)
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

// Map BDE pillar IDs to icons
const PILLAR_ICONS: Record<BDEPillar, LucideIcon> = {
  financial_health: DollarSign,
  gtm_engine: Target,
  customer_health: Users,
  product_technical: Cpu,
  operational_maturity: Settings,
  leadership_transition: Crown,
  ecosystem_dependency: Network,
  service_software_ratio: ArrowRightLeft,
};

// Short names for pillar strip
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

export default function Home() {
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();
  const { score, flags, recommendation, isLoading } = useHomePageData(selectedCompanyId);

  const handleChatSubmit = (message: string) => {
    // Navigate to AI Analyst page with the prompt pre-filled
    navigate('/copilot', { state: { prompt: message } });
  };

  // Transform pillar scores for PillarStrip component
  const pillarData = useMemo(() => {
    if (!score?.pillar_scores) return undefined;

    // Use explicit ordering instead of Object.entries which doesn't guarantee order
    return PILLAR_ORDER.map((pillarId) => {
      const pillar = score.pillar_scores[pillarId];
      if (!pillar) return null;
      return {
        id: pillarId,
        name: PILLAR_CONFIG[pillarId].label,
        shortName: PILLAR_SHORT_NAMES[pillarId],
        icon: PILLAR_ICONS[pillarId],
        score: pillar.score, // Score is already 0-5 scale from the API
      };
    }).filter((p): p is NonNullable<typeof p> => p !== null);
  }, [score?.pillar_scores]);

  // Transform flags for TopExitRisks component
  const risksData = useMemo(() => {
    if (!flags) return undefined;

    // Combine red and yellow flags, limit to top 3
    const allFlags = [
      ...flags.red_flags.map((f) => ({ ...f, severity: 'critical' as const })),
      ...flags.yellow_flags.map((f) => ({ ...f, severity: 'high' as const })),
    ].slice(0, 3);

    return allFlags.map((flag, index) => {
      // Extract a short value from the flag text
      // Look for percentages, numbers, or key phrases
      const percentMatch = flag.text.match(/(\d+(?:\.\d+)?%)/);
      const dollarMatch = flag.text.match(/(\$[\d,.]+[KMB]?)/i);
      const numberMatch = flag.text.match(/(\d+(?:\.\d+)?x?)/);

      let displayValue = 'High Risk';
      if (percentMatch) {
        displayValue = percentMatch[1];
      } else if (dollarMatch) {
        displayValue = dollarMatch[1];
      } else if (numberMatch && flag.text.toLowerCase().includes('concentration')) {
        displayValue = numberMatch[1] + '%';
      } else if (flag.text.toLowerCase().includes('high')) {
        displayValue = 'High';
      } else if (flag.text.toLowerCase().includes('low')) {
        displayValue = 'Low';
      } else if (flag.text.toLowerCase().includes('critical')) {
        displayValue = 'Critical';
      }

      // Create a cleaner title from category
      const title = flag.category
        .replace(/_/g, ' ')
        .replace(/\b\w/g, (l) => l.toUpperCase());

      // Get pillar label for the delta badge
      const pillarLabel = flag.pillar
        ? PILLAR_CONFIG[flag.pillar as BDEPillar]?.label || flag.pillar
        : 'General';

      // Set deltaType based on severity - critical/high risks should show negative (red)
      const deltaType = flag.severity === 'critical' ? 'negative' :
                        flag.severity === 'high' ? 'negative' : 'neutral';

      return {
        id: String(index + 1),
        title: title,
        value: displayValue,
        delta: pillarLabel,
        deltaType: deltaType as 'positive' | 'negative' | 'neutral',
        severity: flag.severity,
      };
    });
  }, [flags]);

  // Build summary from recommendation - no fallback text, show empty if no data
  const summaryText = useMemo(() => {
    return recommendation?.rationale || '';
  }, [recommendation]);

  // Transform recommendation data for MultipleImprovers component
  const improversData = useMemo(() => {
    if (!recommendation) return undefined;

    // Combine value_drivers and 100_day_plan into improvers
    const improvers: Array<{
      id: string;
      action: string;
      impactLabel: string;
      progress: { current: number; total: number };
      status: 'critical' | 'warning' | 'good';
      categories: {
        impact: 'high' | 'medium' | 'low' | null;
        effort: 'high' | 'medium' | 'low' | null;
        priority: number | null;
      };
    }> = [];

    // Add value drivers as high-impact improvers
    // TODO: Replace hardcoded impact labels with API data when endpoint is available
    if (recommendation.value_drivers) {
      recommendation.value_drivers.slice(0, 2).forEach((driver, index) => {
        // Handle both string and object formats from API
        const actionText = typeof driver === 'string'
          ? driver
          : (driver as { action?: string }).action || String(driver);

        improvers.push({
          id: `driver-${index}`,
          action: actionText,
          impactLabel: index === 0 ? '+0.5x' : '+0.3x',
          progress: { current: index, total: 3 },
          status: index === 0 ? 'critical' : 'warning',
          categories: {
            impact: index === 0 ? 'high' : 'medium',
            effort: 'medium',
            priority: index + 1,
          },
        });
      });
    }

    // Add 100-day plan items as actionable improvers
    // TODO: Replace hardcoded impact label with API data when endpoint is available
    if (recommendation['100_day_plan']) {
      recommendation['100_day_plan'].slice(0, 1).forEach((plan, index) => {
        // Handle both string and object formats from API
        const actionText = typeof plan === 'string'
          ? plan
          : (plan as { action?: string }).action || String(plan);

        improvers.push({
          id: `plan-${index}`,
          action: actionText,
          impactLabel: '+0.2x',
          progress: { current: 2, total: 3 },
          status: 'good',
          categories: {
            impact: 'low',
            effort: 'low',
            priority: improvers.length + 1,
          },
        });
      });
    }

    return improvers.length > 0 ? improvers : undefined;
  }, [recommendation]);

  // Calculate last updated time
  const lastUpdated = useMemo(() => {
    if (score?.calculated_at) {
      const date = new Date(score.calculated_at);
      const now = new Date();
      const diffMs = now.getTime() - date.getTime();
      const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
      const diffDays = Math.floor(diffHours / 24);

      if (diffDays > 0) return `${diffDays}d ago`;
      if (diffHours > 0) return `${diffHours}h ago`;
      return 'Just now';
    }
    return 'Not analyzed';
  }, [score?.calculated_at]);

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
        x: Math.max(5, Math.min(95, valueScore)), // Clamp to keep in bounds
        y: Math.max(5, Math.min(95, stabilityScore)), // Clamp to keep in bounds
        status,
        value: displayValue,
        description: `${healthDesc} - ${Math.round(pillar.confidence)}% confidence`,
      });
    });

    return signals.length > 0 ? signals : undefined;
  }, [score?.pillar_scores]);

  // Show loading state while fetching data
  if (isLoading) {
    return (
      <AppLayout hideHeaderBell>
        <PageLoader message="Loading exit readiness data..." size="lg" />
      </AppLayout>
    );
  }

  return (
    <AppLayout hideHeaderBell>
      {/* Header with timestamp - full width with border */}
      <header className={styles.header}>
        <div className={styles.headerInner}>
          <nav className={styles.nav}>
            <button className={styles.navButtonActive}>Overview</button>
          </nav>
          <div className={styles.timestamp}>
            <span className={styles.timestampFull}>Last updated {lastUpdated}</span>
            <span className={styles.timestampShort}>{lastUpdated}</span>
          </div>
        </div>
      </header>

      <div className={styles.container}>

        {/* Main content */}
        <main className={styles.main}>
          {/* TIER 1: Hero Signal - Exit Readiness */}
          <section className={styles.section}>
            <ExitReadinessHero
              status={score?.overall_score && score.overall_score >= 71 ? 'ready' : score?.overall_score && score.overall_score >= 31 ? 'conditional' : 'not-ready'}
              headline={recommendation?.recommendation || 'The value is real, but concentration and founder dependency reduce multiple.'}
              summary={summaryText}
              confidenceScore={score?.overall_score || 0}
              hideScoreFactors
            />
          </section>

          {/* Pillar Strip */}
          <section className={styles.section}>
            <PillarStrip pillars={pillarData} />
          </section>

          {/* AI Chat Bar */}
          <section className={styles.section}>
            <MinimalChatBar
              onSubmit={handleChatSubmit}
              placeholder="Ask about exit readiness, risks, or valuation..."
            />
          </section>

          {/* TIER 2: Top Risks + Signal Map */}
          <section className={styles.section}>
            <div className={styles.twoColumnGrid}>
              <div className={styles.gridLeft}>
                <TopExitRisks risks={risksData} />
              </div>
              <div className={styles.gridDivider} />
              <div className={styles.gridRight}>
                <ExpandableSignalMap
                  defaultExpanded={true}
                  collapsible={false}
                  showFullscreen={false}
                  signals={signalMapData}
                />
              </div>
            </div>
          </section>

          <Separator />

          {/* TIER 3: Multiple Improvers */}
          <section className={styles.section}>
            <MultipleImprovers improvers={improversData} />
          </section>

          <Separator />

          {/* TIER 4: Detailed Metrics (Customer Health + Risk Radar) */}
          <section className={styles.section}>
            <h2 className={styles.detailedMetricsTitle}>Detailed Metrics</h2>
            <div className={styles.detailedMetricsGrid}>
              <div className={styles.detailedMetricsCard}>
                <CustomerHealthGrid />
              </div>
              <div className={styles.detailedMetricsCard}>
                <RiskRadar />
              </div>
            </div>
          </section>

          <Separator />

          {/* Footer */}
          <footer className={styles.footer}>
            <p className={styles.footerText}>
              Designed to help you understand what drives valuation and prepare for what buyers will ask.
            </p>
          </footer>
        </main>
      </div>
    </AppLayout>
  );
}
