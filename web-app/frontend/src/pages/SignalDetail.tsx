/**
 * SignalDetail Page
 *
 * Displays detailed information about a specific signal from the Signal Map.
 * Shows insights, recommendations, and data sources for the signal.
 */

import { useMemo, useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import { PageLoader } from '../components/common/PageLoader';
import {
  ArrowLeft,
  FileText,
  Database,
  Globe,
  Mail,
  FileSpreadsheet,
  Calendar,
  ExternalLink,
  TrendingUp,
  Target,
  Shield,
  AlertTriangle,
  File,
} from 'lucide-react';
import { Button } from '../components/ui/Button';
import { useCompany } from '../contexts/CompanyContext';
import { useBDEScore, useFlags, usePillarDetail } from '../hooks/useScoring';
import {
  scoringApi,
  type BDEPillar,
  type DataSourcesResponse,
  PILLAR_CONFIG,
} from '../api/scoringApi';
import { cn } from '../lib/scorecard-utils';
import styles from '../styles/pages/SignalDetail.module.css';

// Map signal IDs to pillar IDs
const SIGNAL_TO_PILLAR: Record<string, BDEPillar> = {
  'financial-health': 'financial_health',
  'financial_health': 'financial_health',
  'fin': 'financial_health',
  'gtm-engine': 'gtm_engine',
  'gtm_engine': 'gtm_engine',
  'gtm-motion': 'gtm_engine',
  'gtm': 'gtm_engine',
  'customer-health': 'customer_health',
  'customer_health': 'customer_health',
  'cust': 'customer_health',
  'product-technical': 'product_technical',
  'product_technical': 'product_technical',
  'prod': 'product_technical',
  'operational-maturity': 'operational_maturity',
  'operational_maturity': 'operational_maturity',
  'ops': 'operational_maturity',
  'leadership-transition': 'leadership_transition',
  'leadership_transition': 'leadership_transition',
  'leadership-depth': 'leadership_transition',
  'lead': 'leadership_transition',
  'ecosystem-dependency': 'ecosystem_dependency',
  'ecosystem_dependency': 'ecosystem_dependency',
  'eco': 'ecosystem_dependency',
  'service-software-ratio': 'service_software_ratio',
  'service_software_ratio': 'service_software_ratio',
  's2s': 'service_software_ratio',
};

// Short names for pillars
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

// Status configuration
const STATUS_CONFIG = {
  protect: {
    label: 'Protect',
    description: 'High value, stable - maintain and leverage this strength',
    className: styles.statusProtect,
    badgeClass: styles.badgeProtect,
  },
  fix: {
    label: 'Fix',
    description: 'High value, fragile - prioritize fixing to preserve value',
    className: styles.statusFix,
    badgeClass: styles.badgeFix,
  },
  upside: {
    label: 'Upside',
    description: 'Growth potential - opportunity for value creation',
    className: styles.statusUpside,
    badgeClass: styles.badgeUpside,
  },
  risk: {
    label: 'Risk',
    description: 'Low value, fragile - address or mitigate',
    className: styles.statusRisk,
    badgeClass: styles.badgeRisk,
  },
};

// Source type icons
const SOURCE_TYPE_ICONS: Record<string, typeof FileText> = {
  pdf: FileText,
  spreadsheet: FileSpreadsheet,
  crm: Database,
  email: Mail,
  api: Globe,
  database: Database,
  default: File,
};

// Get file type from filename
function getFileType(filename: string): string {
  const ext = filename.toLowerCase().split('.').pop() || '';
  if (ext === 'pdf') return 'pdf';
  if (['xlsx', 'xls', 'csv'].includes(ext)) return 'spreadsheet';
  if (filename.toLowerCase().includes('api')) return 'api';
  if (filename.toLowerCase().includes('crm') || filename.toLowerCase().includes('salesforce')) return 'crm';
  return 'default';
}

// Format date to relative time
function formatRelativeDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  return date.toLocaleDateString();
}

export default function SignalDetail() {
  const { signalId } = useParams<{ signalId: string }>();
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();

  // Map signal ID to pillar ID
  const pillarId = signalId ? SIGNAL_TO_PILLAR[signalId.toLowerCase()] : null;

  // Fetch data from APIs
  const { data: score } = useBDEScore(selectedCompanyId);
  const { data: flags } = useFlags(selectedCompanyId);
  const { data: pillarDetail } = usePillarDetail(selectedCompanyId, pillarId);
  const [dataSources, setDataSources] = useState<DataSourcesResponse | null>(null);

  // Fetch data sources
  const fetchDataSources = useCallback(async () => {
    if (!selectedCompanyId) return;
    try {
      const sources = await scoringApi.getDataSources(selectedCompanyId);
      setDataSources(sources);
    } catch (err) {
      console.error('Failed to fetch data sources:', err);
    }
  }, [selectedCompanyId]);

  useEffect(() => {
    fetchDataSources();
  }, [fetchDataSources]);

  // Build signal data from API responses
  const signalData = useMemo(() => {
    if (!pillarId || !score?.pillar_scores) {
      return null;
    }

    const pillarScore = score.pillar_scores[pillarId];
    if (!pillarScore) return null;

    const config = PILLAR_CONFIG[pillarId];

    // Calculate value and stability for status determination
    const valueScore = (pillarScore.score / 5) * 100;
    const stabilityScore = (pillarScore.confidence + pillarScore.data_coverage) / 2;

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

    // Build insights from pillar detail and flags
    const insights: string[] = [];

    if (pillarDetail?.key_findings) {
      insights.push(...pillarDetail.key_findings.slice(0, 3));
    }

    // Add health-based insight
    if (pillarScore.health_status === 'green') {
      insights.push(`${config.label} is performing well with a score of ${pillarScore.score.toFixed(1)}/5`);
    } else if (pillarScore.health_status === 'yellow') {
      insights.push(`${config.label} needs attention - currently at ${pillarScore.score.toFixed(1)}/5`);
    } else {
      insights.push(`${config.label} is a critical concern at ${pillarScore.score.toFixed(1)}/5`);
    }

    // Add relevant flags as insights
    if (flags) {
      const relevantFlags = [...flags.red_flags, ...flags.yellow_flags]
        .filter(f => f.pillar === pillarId)
        .slice(0, 2);
      relevantFlags.forEach(f => insights.push(f.text));
    }

    // Build recommendations from pillar detail
    const recommendations: string[] = [];

    if (pillarDetail?.risks) {
      pillarDetail.risks.slice(0, 2).forEach(risk => {
        recommendations.push(`Address: ${risk}`);
      });
    }

    if (pillarDetail?.data_gaps) {
      pillarDetail.data_gaps.slice(0, 2).forEach(gap => {
        recommendations.push(`Fill data gap: ${gap}`);
      });
    }

    // Add status-based recommendations
    if (status === 'fix') {
      recommendations.push(`Prioritize stabilizing ${config.label} to preserve value`);
    } else if (status === 'risk') {
      recommendations.push(`Develop mitigation plan for ${config.label} risks`);
    } else if (status === 'protect') {
      recommendations.push(`Document ${config.label} strengths for buyer presentation`);
    } else if (status === 'upside') {
      recommendations.push(`Quantify growth opportunity in ${config.label}`);
    }

    // Build sources from data sources
    const sources = dataSources?.documents?.slice(0, 4).map((doc) => ({
      id: doc.id,
      name: doc.original_filename || doc.filename,
      type: getFileType(doc.original_filename || doc.filename),
      lastUpdated: doc.updated_at,
      confidence: doc.confidence ? Math.round(doc.confidence) : 85,
      extractedValues: [
        { label: 'Metrics Extracted', value: String(doc.metrics_count || 0) },
        { label: 'Data Chunks', value: String(doc.chunks_count || 0) },
      ],
    })) || [];

    return {
      name: config.label,
      shortName: PILLAR_SHORT_NAMES[pillarId],
      description: pillarDetail?.justification || `Assessment of ${config.label.toLowerCase()} for exit readiness`,
      status,
      value: `${pillarScore.score.toFixed(1)}/5`,
      xPosition: Math.round(valueScore),
      yPosition: Math.round(stabilityScore),
      insights: insights.slice(0, 5),
      recommendations: recommendations.slice(0, 4),
      sources,
      confidence: pillarScore.confidence,
      dataCoverage: pillarScore.data_coverage,
    };
  }, [pillarId, score, pillarDetail, flags, dataSources]);

  const handleBack = () => {
    navigate(-1);
  };

  // Show not found state
  if (!signalId || !pillarId) {
    return (
      <AppLayout title="Signal Not Found">
        <div className={styles.container}>
          <div className={styles.emptyState}>
            <AlertTriangle size={48} className={styles.emptyIcon} />
            <h2 className={styles.emptyTitle}>Signal Not Found</h2>
            <p className={styles.emptyText}>The requested signal could not be found.</p>
            <Button onClick={() => navigate('/analytics')}>Back to Analytics</Button>
          </div>
        </div>
      </AppLayout>
    );
  }

  // Show loading state
  if (!signalData) {
    return (
      <AppLayout title="Loading...">
        <PageLoader message="Loading signal data..." size="lg" />
      </AppLayout>
    );
  }

  const statusConfig = STATUS_CONFIG[signalData.status];

  return (
    <AppLayout title={signalData.name}>
      <div className={styles.container}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerInner}>
            <Button variant="ghost" size="sm" className={styles.backButton} onClick={handleBack}>
              <ArrowLeft size={16} />
              Back
            </Button>

            <div className={styles.headerContent}>
              <div className={styles.headerLeft}>
                <div className={cn(styles.signalIcon, statusConfig.className)}>
                  <span>{signalData.shortName}</span>
                </div>
                <div className={styles.headerInfo}>
                  <div className={styles.headerBadges}>
                    <span className={cn(styles.statusBadge, statusConfig.badgeClass)}>
                      {statusConfig.label}
                    </span>
                    <span className={styles.positionLabel}>
                      Position: ({signalData.xPosition}, {signalData.yPosition})
                    </span>
                  </div>
                  <h1 className={styles.title}>{signalData.name}</h1>
                  <p className={styles.description}>{signalData.description}</p>
                </div>
              </div>
              <div className={styles.headerRight}>
                <p className={styles.valueLabel}>Current Value</p>
                <p className={cn(styles.valueDisplay, statusConfig.className)}>{signalData.value}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className={styles.main}>
          {/* Status Context */}
          <section className={cn(styles.statusContext, statusConfig.className)}>
            <Shield size={20} className={styles.statusIcon} />
            <div>
              <h3 className={styles.statusTitle}>{statusConfig.label} Quadrant</h3>
              <p className={styles.statusDesc}>{statusConfig.description}</p>
            </div>
          </section>

          {/* Key Insights */}
          {signalData.insights.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                <TrendingUp size={16} />
                Key Insights
              </h2>
              <ul className={styles.insightsList}>
                {signalData.insights.map((insight, idx) => (
                  <li key={idx} className={styles.insightItem}>
                    <div className={styles.insightDot} />
                    <p>{insight}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Recommendations */}
          {signalData.recommendations.length > 0 && (
            <section className={styles.section}>
              <h2 className={styles.sectionTitle}>
                <Target size={16} />
                Recommendations
              </h2>
              <ul className={styles.recommendationsList}>
                {signalData.recommendations.map((rec, idx) => (
                  <li key={idx} className={styles.recommendationItem}>
                    <div className={styles.recommendationNumber}>{idx + 1}</div>
                    <p>{rec}</p>
                  </li>
                ))}
              </ul>
            </section>
          )}

          {/* Data Sources */}
          {signalData.sources.length > 0 && (
            <section className={styles.sourcesSection}>
              <h2 className={styles.sourcesSectionTitle}>
                Data Sources ({signalData.sources.length})
              </h2>
              <div className={styles.sourcesList}>
                {signalData.sources.map((source) => {
                  const Icon = SOURCE_TYPE_ICONS[source.type] || SOURCE_TYPE_ICONS.default;
                  return (
                    <div key={source.id} className={styles.sourceCard}>
                      <div className={styles.sourceHeader}>
                        <div className={styles.sourceInfo}>
                          <div className={cn(styles.sourceIcon, styles[`sourceType${source.type}`])}>
                            <Icon size={20} />
                          </div>
                          <div className={styles.sourceDetails}>
                            <p className={styles.sourceName}>{source.name}</p>
                            <div className={styles.sourceDate}>
                              <Calendar size={12} />
                              <span>Last updated: {formatRelativeDate(source.lastUpdated)}</span>
                            </div>
                          </div>
                        </div>
                        <div className={styles.sourceActions}>
                          <div className={styles.confidenceBlock}>
                            <p className={styles.confidenceLabel}>Confidence</p>
                            <p className={cn(
                              styles.confidenceValue,
                              source.confidence >= 95 ? styles.confidenceHigh :
                              source.confidence >= 85 ? styles.confidenceMedium :
                              styles.confidenceLow
                            )}>
                              {source.confidence}%
                            </p>
                          </div>
                          <button className={styles.externalButton}>
                            <ExternalLink size={16} />
                          </button>
                        </div>
                      </div>
                      <div className={styles.extractedSection}>
                        <p className={styles.extractedLabel}>Extracted Values</p>
                        <div className={styles.extractedGrid}>
                          {source.extractedValues.map((val, idx) => (
                            <div key={idx} className={styles.extractedItem}>
                              <p className={styles.extractedItemLabel}>{val.label}</p>
                              <p className={styles.extractedItemValue}>{val.value}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </section>
          )}

          {/* Data Quality Summary */}
          <section className={styles.summarySection}>
            <h2 className={styles.summaryTitle}>Data Quality Summary</h2>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>
                  {signalData.sources.length > 0
                    ? Math.round(signalData.sources.reduce((sum, s) => sum + s.confidence, 0) / signalData.sources.length)
                    : Math.round(signalData.confidence)}%
                </p>
                <p className={styles.summaryLabel}>Average Confidence</p>
              </div>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>
                  {signalData.sources.reduce((sum, s) => sum + s.extractedValues.length, 0)}
                </p>
                <p className={styles.summaryLabel}>Data Points</p>
              </div>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>{signalData.sources.length}</p>
                <p className={styles.summaryLabel}>Sources</p>
              </div>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>{Math.round(signalData.dataCoverage)}%</p>
                <p className={styles.summaryLabel}>Data Coverage</p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </AppLayout>
  );
}
