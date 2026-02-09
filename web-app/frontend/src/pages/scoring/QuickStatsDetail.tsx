import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import commonStyles from '../../styles/scoring/common.module.css';
import styles from '../../styles/scoring/QuickStatsDetail.module.css';
import { scoringApi, formatCurrency } from '../../api/scoringApi';
import type { MetricsWithSourcesResponse, SourceDocumentInfo, MetricWithSource } from '../../api/scoringApi';

// Helper to get metrics that came from a specific document
function getMetricsFromDocument(
  metrics: Record<string, MetricWithSource>,
  documentId: string
): { name: string; value: string; pages: number[] }[] {
  const result: { name: string; value: string; pages: number[] }[] = [];

  for (const [name, metric] of Object.entries(metrics)) {
    const sourceDoc = metric.source_documents?.find(sd => sd.document_id === documentId);
    if (sourceDoc) {
      let value = 'N/A';
      if (metric.current_value.numeric !== null) {
        if (metric.current_value.unit === '$') {
          value = formatCurrency(metric.current_value.numeric);
        } else if (metric.current_value.unit === '%') {
          value = `${metric.current_value.numeric}%`;
        } else {
          value = `${metric.current_value.numeric}${metric.current_value.unit || ''}`;
        }
      } else if (metric.current_value.text) {
        value = metric.current_value.text;
      }
      result.push({ name, value, pages: sourceDoc.page_numbers });
    }
  }

  return result;
}

// Calculate average confidence from metrics
function calculateAvgConfidence(metrics: Record<string, MetricWithSource>): number {
  const values = Object.values(metrics);
  if (values.length === 0) return 0;
  const sum = values.reduce((acc, m) => acc + (m.current_value.confidence || 0), 0);
  return Math.round(sum / values.length);
}

export default function QuickStatsDetail() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsWithSourcesResponse | null>(null);
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocumentInfo[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (!companyId) return;

      try {
        setLoading(true);
        const data = await scoringApi.getMetricsWithSources(companyId).catch(() => null);
        setMetricsData(data);
        setSourceDocuments(data?.source_documents || []);
      } catch (err) {
        setError('Failed to load metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  const handleBackClick = () => {
    navigate('/');
  };

  // Group metrics by category
  const categorizeMetrics = () => {
    if (!metricsData) return {};

    const categories: Record<string, { label: string; value: string; confidence: number; sources: { filename: string; pages: number[] }[] }[]> = {
      'Financial': [],
      'Sales & GTM': [],
      'Customer': [],
      'Product': [],
      'Operations': [],
    };

    const m = metricsData.metrics;

    const formatMetric = (metric: MetricWithSource, label: string, format: (val: number) => string) => ({
      label,
      value: metric.current_value.numeric !== null ? format(metric.current_value.numeric) : 'N/A',
      confidence: metric.current_value.confidence,
      sources: metric.source_documents?.map(sd => ({ filename: sd.filename, pages: sd.page_numbers })) || []
    });

    // Financial
    if (m.ARR) categories['Financial'].push(formatMetric(m.ARR, 'ARR', v => formatCurrency(v)));
    if (m.MRR) categories['Financial'].push(formatMetric(m.MRR, 'MRR', v => formatCurrency(v)));
    if (m.BurnRateMonthly) categories['Financial'].push(formatMetric(m.BurnRateMonthly, 'Burn Rate', v => `${formatCurrency(v)}/mo`));
    if (m.RunwayMonths) categories['Financial'].push(formatMetric(m.RunwayMonths, 'Runway', v => `${v} months`));
    if (m.GrossMarginPct) categories['Financial'].push(formatMetric(m.GrossMarginPct, 'Gross Margin', v => `${v}%`));
    if (m.EBITDA_MarginPct) categories['Financial'].push(formatMetric(m.EBITDA_MarginPct, 'EBITDA Margin', v => `${v}%`));

    // Sales
    if (m.AvgDealSize) categories['Sales & GTM'].push(formatMetric(m.AvgDealSize, 'Avg Deal Size', v => formatCurrency(v)));
    if (m.AvgSalesCycleDays) categories['Sales & GTM'].push(formatMetric(m.AvgSalesCycleDays, 'Sales Cycle', v => `${v} days`));
    if (m.WinRatePct) categories['Sales & GTM'].push(formatMetric(m.WinRatePct, 'Win Rate', v => `${v}%`));
    if (m.PipelineCoverageRatio) categories['Sales & GTM'].push(formatMetric(m.PipelineCoverageRatio, 'Pipeline Coverage', v => `${v}x`));

    // Customer
    if (m.NRR) categories['Customer'].push(formatMetric(m.NRR, 'NRR', v => `${v}%`));
    if (m.GRR) categories['Customer'].push(formatMetric(m.GRR, 'GRR', v => `${v}%`));
    if (m.ChurnRatePct) categories['Customer'].push(formatMetric(m.ChurnRatePct, 'Churn Rate', v => `${v}%`));
    if (m.NPS) categories['Customer'].push(formatMetric(m.NPS, 'NPS', v => `${v}`));

    // Product
    if (m.UptimePct) categories['Product'].push(formatMetric(m.UptimePct, 'Uptime', v => `${v}%`));
    if (m.DeployFrequency) categories['Product'].push(formatMetric(m.DeployFrequency, 'Deploy Freq', v => `${v}/month`));
    if (m.TestCoveragePct) categories['Product'].push(formatMetric(m.TestCoveragePct, 'Test Coverage', v => `${v}%`));

    // Operations
    if (m.OnboardingTimeDays) categories['Operations'].push(formatMetric(m.OnboardingTimeDays, 'Onboarding Time', v => `${v} days`));
    if (m.TurnoverRatePct) categories['Operations'].push(formatMetric(m.TurnoverRatePct, 'Turnover Rate', v => `${v}%`));

    return categories;
  };

  const categories = categorizeMetrics();
  const avgConfidence = metricsData ? calculateAvgConfidence(metricsData.metrics) : 0;

  return (
    <AppLayout>
      <div className={commonStyles.container}>
        <button className={commonStyles.backButton} onClick={handleBackClick}>
          &larr; Back to Dashboard
        </button>

        <div className={commonStyles.headerSection}>
          <div className={commonStyles.categoryBadge}>Metrics & KPIs</div>
          <div className={commonStyles.titleRow}>
            <h1 className={commonStyles.pageTitle}>Quick Stats</h1>
            <span className={commonStyles.sourceCount}>
              Sources: {sourceDocuments.length}
            </span>
          </div>
          <p className={commonStyles.subtitle}>Key financial metrics and business indicators</p>
        </div>

        <div className={commonStyles.section}>
          <h2 className={commonStyles.sectionTitle}>DATA SOURCES</h2>

          {loading ? (
            <div className={commonStyles.loadingState}>Loading...</div>
          ) : error ? (
            <div className={commonStyles.errorState}>{error}</div>
          ) : !metricsData ? (
            <div className={commonStyles.emptyState}>
              <p>No metrics available. Run the scoring pipeline first.</p>
            </div>
          ) : (
            <>
              <div className={commonStyles.documentsContainer}>
                {sourceDocuments.filter(doc => doc.metrics_count > 0).map((doc) => {
                const docMetrics = getMetricsFromDocument(metricsData.metrics, doc.id);
                return (
                  <div key={doc.id} className={commonStyles.sourceCard}>
                    <div className={commonStyles.sourceHeader}>
                      <div className={commonStyles.sourceIcon}>
                        {doc.file_type === 'pdf' ? '📄' : doc.file_type === 'xlsx' ? '📊' : '📝'}
                      </div>
                      <div className={commonStyles.sourceInfo}>
                        <span className={commonStyles.sourceTitle}>{doc.original_filename}</span>
                        <span className={commonStyles.sourceDate}>
                          Last updated: {new Date(doc.updated_at).toLocaleDateString()}
                        </span>
                      </div>
                      <div className={commonStyles.confidenceBadge}>
                        Confidence: <span className={commonStyles.confidenceValue}>{doc.confidence}%</span>
                      </div>
                    </div>

                    <div className={commonStyles.extractedValues}>
                      <span className={commonStyles.valuesLabel}>Extracted Values</span>
                      <div className={commonStyles.valuesGrid}>
                        {docMetrics.slice(0, 4).map((m, idx) => (
                          <div key={idx} className={commonStyles.valueCard}>
                            <span className={commonStyles.valueLabel}>
                              {m.name}
                              {m.pages.length > 0 && (
                                <span className={commonStyles.pageRef}>(p.{m.pages.join(', ')})</span>
                              )}
                            </span>
                            <span className={commonStyles.valueNumber}>{m.value}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                );
              })}
              </div>

              {/* All Metrics by Category */}
              {Object.entries(categories).map(([category, metricsList]) => (
                metricsList.length > 0 && (
                  <div key={category} className={styles.metricsCategory}>
                    <h3 className={styles.categoryTitle}>{category}</h3>
                    <div className={styles.metricsGrid}>
                      {metricsList.map((m, idx) => (
                        <div key={idx} className={styles.metricCard}>
                          <span className={styles.metricValue}>{m.value}</span>
                          <span className={styles.metricLabel}>{m.label}</span>
                          <span className={styles.metricConfidence}>
                            Confidence: {m.confidence}%
                          </span>
                          {m.sources.length > 0 && (
                            <span className={styles.metricSource}>
                              Source: {m.sources[0].filename.slice(0, 20)}
                              {m.sources[0].pages.length > 0 && ` (p.${m.sources[0].pages.join(', ')})`}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )
              ))}

              {/* Conflicts Section */}
              {metricsData.conflicts.length > 0 && (
                <div className={styles.conflictsSection}>
                  <h3 className={styles.conflictsTitle}>Metrics Requiring Review</h3>
                  <div className={styles.conflictsList}>
                    {metricsData.conflicts.map((conflict, idx) => (
                      <div key={idx} className={styles.conflictCard}>
                        <span className={styles.conflictName}>{conflict.metric_name}</span>
                        <span className={styles.conflictValue}>{conflict.value}</span>
                        <span className={styles.conflictMeta}>
                          Period: {conflict.period} | Confidence: {conflict.confidence}%
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Data Lineage */}
        <div className={commonStyles.lineageSection}>
          <h3 className={commonStyles.lineageTitle}>Data Lineage</h3>
          <div className={commonStyles.lineageFlow}>
            <span className={commonStyles.lineageNode}>
              Source Documents
              <span className={commonStyles.lineageNodeMeta}>
                ({sourceDocuments.length} files)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Metric Extraction
              <span className={commonStyles.lineageNodeMeta}>
                ({metricsData?.metrics ? Object.keys(metricsData.metrics).length : 0} metrics)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Data Categorization
              <span className={commonStyles.lineageNodeMeta}>
                (by pillar)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNodeFinal}>Dashboard</span>
          </div>
        </div>

        {/* Confidence Summary */}
        {metricsData && (
          <div className={commonStyles.confidenceSection}>
            <h3 className={commonStyles.confidenceTitle}>Confidence Summary</h3>
            <div className={commonStyles.confidenceGrid}>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>{avgConfidence}%</span>
                <span className={commonStyles.confidenceLabel}>Average Confidence</span>
              </div>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>{Object.keys(metricsData.metrics).length}</span>
                <span className={commonStyles.confidenceLabel}>Data Points</span>
              </div>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>{sourceDocuments.length}</span>
                <span className={commonStyles.confidenceLabel}>Sources</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
