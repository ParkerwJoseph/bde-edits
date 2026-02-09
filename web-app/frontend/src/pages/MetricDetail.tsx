/**
 * MetricDetail Page
 *
 * Displays data sources, extracted values, and confidence metrics
 * for a specific metric (e.g., top-risks, exit-hero, signal-map).
 */

import { useMemo, useCallback, useState, useEffect } from 'react';
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
  File,
  type LucideIcon,
} from 'lucide-react';
import { useCompany } from '../contexts/CompanyContext';
import { scoringApi, type DataSourcesResponse } from '../api/scoringApi';
import { useFlags, useBDEScore } from '../hooks/useScoring';
import styles from '../styles/pages/MetricDetail.module.css';

interface SourceFile {
  id: string;
  name: string;
  type: 'pdf' | 'spreadsheet' | 'crm' | 'email' | 'api' | 'database';
  lastUpdated: string;
  confidence: number;
  extractedValues: { label: string; value: string; page?: number }[];
}

interface MetricConfig {
  title: string;
  description: string;
  category: string;
  sources: SourceFile[];
}

const sourceTypeIcons: Record<string, LucideIcon> = {
  pdf: FileText,
  spreadsheet: FileSpreadsheet,
  crm: Database,
  email: Mail,
  api: Globe,
  database: Database,
  default: File,
};

const sourceTypeColors: Record<string, { bg: string; text: string }> = {
  pdf: { bg: 'rgba(239, 68, 68, 0.1)', text: '#ef4444' },
  spreadsheet: { bg: 'rgba(34, 197, 94, 0.1)', text: '#22c55e' },
  crm: { bg: 'rgba(59, 130, 246, 0.1)', text: '#3b82f6' },
  email: { bg: 'rgba(139, 92, 246, 0.1)', text: '#8b5cf6' },
  api: { bg: 'rgba(249, 115, 22, 0.1)', text: '#f97316' },
  database: { bg: 'rgba(6, 182, 212, 0.1)', text: '#06b6d4' },
  default: { bg: 'rgba(107, 114, 128, 0.1)', text: '#6b7280' },
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

// Mock data configurations for different metric types
const metricsConfig: Record<string, Omit<MetricConfig, 'sources'>> = {
  'top-risks': {
    title: 'Top Exit Risks',
    description: 'Critical risks that buyers will evaluate during due diligence',
    category: 'Strategic Signals',
  },
  'exit-hero': {
    title: 'Exit Readiness Score',
    description: 'Overall assessment of company\'s readiness for acquisition or exit',
    category: 'Strategic Signals',
  },
  'signal-map': {
    title: 'Signal Map',
    description: 'Value vs. fragility positioning of key business signals',
    category: 'Strategic Signals',
  },
  'multiple-improvers': {
    title: 'Multiple Improvers',
    description: 'Actions that directly improve company valuation multiple',
    category: 'Strategic Signals',
  },
  'pillar-scores': {
    title: 'Pillar Scores',
    description: 'Health scores across 8 business pillars',
    category: 'Metrics & KPIs',
  },
  'customer-health': {
    title: 'Customer Health',
    description: 'Customer acquisition, retention, and expansion metrics',
    category: 'Metrics & KPIs',
  },
  'risk-radar': {
    title: 'Risk Radar',
    description: 'Active business risks by severity',
    category: 'Insights & Priorities',
  },
  'quick-stats': {
    title: 'Quick Stats',
    description: 'Key financial metrics and business indicators',
    category: 'Metrics & KPIs',
  },
};

export default function MetricDetail() {
  const { metricId } = useParams<{ metricId: string }>();
  const navigate = useNavigate();
  const { selectedCompanyId } = useCompany();

  // Fetch real data from APIs
  const { data: flags, isLoading: flagsLoading } = useFlags(selectedCompanyId);
  const { data: score, isLoading: scoreLoading } = useBDEScore(selectedCompanyId);
  const [dataSources, setDataSources] = useState<DataSourcesResponse | null>(null);
  const [dataSourcesLoading, setDataSourcesLoading] = useState(true);

  // Fetch data sources (documents)
  const fetchDataSources = useCallback(async () => {
    if (!selectedCompanyId) {
      setDataSourcesLoading(false);
      return;
    }
    try {
      setDataSourcesLoading(true);
      const sources = await scoringApi.getDataSources(selectedCompanyId);
      setDataSources(sources);
    } catch (err) {
      console.error('Failed to fetch data sources:', err);
    } finally {
      setDataSourcesLoading(false);
    }
  }, [selectedCompanyId]);

  useEffect(() => {
    fetchDataSources();
  }, [fetchDataSources]);

  // Build metric data from real API data
  const metric = useMemo(() => {
    const config = metricsConfig[metricId || ''] || {
      title: 'Metric Details',
      description: 'Detailed view of this metric',
      category: 'Unknown',
    };

    // Build sources from actual data sources (documents)
    const sources: SourceFile[] = [];

    if (dataSources?.documents) {
      dataSources.documents.slice(0, 3).forEach((doc, index) => {
        const displayName = doc.original_filename || doc.filename;
        const fileType = getFileType(displayName);
        const extractedValues: { label: string; value: string; page?: number }[] = [];

        // Add basic document info
        extractedValues.push(
          { label: 'Metrics Count', value: String(doc.metrics_count || 0) },
          { label: 'Chunks', value: String(doc.chunks_count || 0) }
        );

        // Add metric-specific extracted values based on metricId
        if (metricId === 'top-risks' && flags) {
          if (index === 0 && flags.red_flags.length > 0) {
            extractedValues.push(
              { label: 'Critical Risks', value: String(flags.red_flags.length) },
              { label: 'High Risks', value: String(flags.yellow_flags.length) }
            );
          }
        }

        if (metricId === 'exit-hero' && score) {
          if (index === 0) {
            extractedValues.push(
              { label: 'Overall Score', value: String(score.overall_score) },
              { label: 'Confidence', value: `${Math.round(score.confidence)}%` }
            );
          }
        }

        if (metricId === 'pillar-scores' && score?.pillar_scores) {
          const pillarEntries = Object.entries(score.pillar_scores).slice(0, 3);
          pillarEntries.forEach(([pillar, pillarData]) => {
            extractedValues.push({
              label: pillar.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()),
              value: `${pillarData.score}/5`,
            });
          });
        }

        sources.push({
          id: doc.id,
          name: displayName,
          type: fileType as SourceFile['type'],
          lastUpdated: doc.updated_at,
          confidence: doc.confidence ? Math.round(doc.confidence) : 85,
          extractedValues: extractedValues,
        });
      });
    }

    // Add database source for computed scores
    if (score && (metricId === 'exit-hero' || metricId === 'pillar-scores')) {
      sources.push({
        id: 'db-scores',
        name: 'pillar_scores',
        type: 'database',
        lastUpdated: score.calculated_at || new Date().toISOString(),
        confidence: 100,
        extractedValues: [
          { label: 'Weighted Score', value: String(score.overall_score) },
          { label: 'Documents Analyzed', value: String(dataSources?.documents?.length || 0) },
        ],
      });
    }

    // If no real data, add placeholder
    if (sources.length === 0) {
      sources.push({
        id: 'placeholder',
        name: 'No documents available',
        type: 'database',
        lastUpdated: new Date().toISOString(),
        confidence: 0,
        extractedValues: [
          { label: 'Status', value: 'Upload documents to see data sources' },
        ],
      });
    }

    return {
      ...config,
      sources,
    };
  }, [metricId, dataSources, flags, score]);

  const handleBack = () => {
    navigate(-1);
  };

  const getConfidenceClass = (confidence: number): string => {
    if (confidence >= 95) return styles.confidenceHigh;
    if (confidence >= 85) return styles.confidenceMedium;
    return styles.confidenceLow;
  };

  // Combined loading state
  const isLoading = flagsLoading || scoreLoading || dataSourcesLoading;

  if (isLoading) {
    return (
      <AppLayout title="Loading..." subtitle="">
        <PageLoader message="Loading metric details..." size="lg" />
      </AppLayout>
    );
  }

  return (
    <AppLayout title={metric.title} subtitle={metric.description}>
      <div className={styles.container}>
        {/* Header */}
        <header className={styles.header}>
          <div className={styles.headerInner}>
            <button className={styles.backButton} onClick={handleBack}>
              <ArrowLeft size={16} />
              Back to Dashboard
            </button>

            <div className={styles.headerContent}>
              <div className={styles.headerLeft}>
                <span className={styles.categoryBadge}>{metric.category}</span>
                <h1 className={styles.title}>{metric.title}</h1>
                <p className={styles.description}>{metric.description}</p>
              </div>
              <div className={styles.headerRight}>
                <p className={styles.sourcesLabel}>Sources</p>
                <p className={styles.sourcesCount}>{metric.sources.length}</p>
              </div>
            </div>
          </div>
        </header>

        {/* Content */}
        <main className={styles.main}>
          {/* Data Sources */}
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>Data Sources</h2>
            <div className={styles.sourcesList}>
              {metric.sources.map((source) => {
                const Icon = sourceTypeIcons[source.type] || sourceTypeIcons.default;
                const colors = sourceTypeColors[source.type] || sourceTypeColors.default;

                return (
                  <div key={source.id} className={styles.sourceCard}>
                    {/* Source Header */}
                    <div className={styles.sourceHeader}>
                      <div className={styles.sourceInfo}>
                        <div
                          className={styles.sourceIcon}
                          style={{ backgroundColor: colors.bg, color: colors.text }}
                        >
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
                          <p className={`${styles.confidenceValue} ${getConfidenceClass(source.confidence)}`}>
                            {source.confidence}%
                          </p>
                        </div>
                        <button className={styles.externalButton}>
                          <ExternalLink size={16} />
                        </button>
                      </div>
                    </div>

                    {/* Extracted Values */}
                    <div className={styles.extractedSection}>
                      <p className={styles.extractedLabel}>Extracted Values</p>
                      <div className={styles.extractedGrid}>
                        {source.extractedValues.map((val, idx) => (
                          <div key={idx} className={styles.extractedItem}>
                            <p className={styles.extractedItemLabel}>
                              {val.label}
                              {val.page && (
                                <span className={styles.pageRef}>(p.{val.page})</span>
                              )}
                            </p>
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

          {/* Data Lineage */}
          <section className={styles.lineageSection}>
            <h2 className={styles.lineageSectionTitle}>Data Lineage</h2>
            <div className={styles.lineageFlow}>
              {metric.sources.map((source, idx) => {
                const Icon = sourceTypeIcons[source.type] || sourceTypeIcons.default;
                const colors = sourceTypeColors[source.type] || sourceTypeColors.default;

                return (
                  <div key={source.id} className={styles.lineageItem}>
                    <div
                      className={styles.lineagePill}
                      style={{ backgroundColor: colors.bg, color: colors.text }}
                    >
                      <Icon size={12} />
                      <span>{source.name.split('.')[0]}</span>
                    </div>
                    {idx < metric.sources.length - 1 && (
                      <span className={styles.lineageArrow}>→</span>
                    )}
                  </div>
                );
              })}
              <span className={styles.lineageArrow}>→</span>
              <div className={styles.lineagePillDashboard}>
                <Database size={12} />
                <span>Dashboard</span>
              </div>
            </div>
          </section>

          {/* Confidence Summary */}
          <section className={styles.summarySection}>
            <h2 className={styles.summarySectionTitle}>Confidence Summary</h2>
            <div className={styles.summaryGrid}>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>
                  {Math.round(
                    metric.sources.reduce((sum, s) => sum + s.confidence, 0) /
                      (metric.sources.length || 1)
                  )}%
                </p>
                <p className={styles.summaryLabel}>Average Confidence</p>
              </div>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>
                  {metric.sources.reduce((sum, s) => sum + s.extractedValues.length, 0)}
                </p>
                <p className={styles.summaryLabel}>Data Points</p>
              </div>
              <div className={styles.summaryItem}>
                <p className={styles.summaryValue}>{metric.sources.length}</p>
                <p className={styles.summaryLabel}>Sources</p>
              </div>
            </div>
          </section>
        </main>
      </div>
    </AppLayout>
  );
}
