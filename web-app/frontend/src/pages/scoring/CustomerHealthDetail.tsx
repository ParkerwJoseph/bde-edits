import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import commonStyles from '../../styles/scoring/common.module.css';
import styles from '../../styles/scoring/HealthDetail.module.css';
import { scoringApi } from '../../api/scoringApi';
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
        if (metric.current_value.unit === '%') {
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

export default function CustomerHealthDetail() {
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
        setError('Failed to load customer health data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  const handleBackClick = () => {
    navigate('/');
  };

  // Extract customer-related metrics with source information
  const getCustomerMetrics = () => {
    if (!metricsData) return [];

    const m = metricsData.metrics;
    const customerMetrics: {
      label: string;
      value: string;
      status: 'good' | 'warning' | 'bad' | 'neutral';
      sources: { filename: string; pages: number[] }[];
    }[] = [];

    const formatMetric = (
      metric: MetricWithSource,
      label: string,
      getValue: () => string,
      getStatus: (val: number | null) => 'good' | 'warning' | 'bad' | 'neutral'
    ) => ({
      label,
      value: getValue(),
      status: getStatus(metric.current_value.numeric),
      sources: metric.source_documents?.map(sd => ({ filename: sd.filename, pages: sd.page_numbers })) || []
    });

    if (m.NRR) {
      const val = m.NRR.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.NRR,
        'Net Revenue Retention (NRR)',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v >= 110 ? 'good' : v >= 95 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.GRR) {
      const val = m.GRR.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.GRR,
        'Gross Revenue Retention (GRR)',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v >= 90 ? 'good' : v >= 80 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.ChurnRatePct) {
      const val = m.ChurnRatePct.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.ChurnRatePct,
        'Churn Rate',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v <= 5 ? 'good' : v <= 10 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.NPS) {
      const val = m.NPS.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.NPS,
        'Net Promoter Score (NPS)',
        () => val !== null ? `${val}` : 'N/A',
        (v) => v !== null ? (v >= 50 ? 'good' : v >= 0 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.CSAT) {
      const val = m.CSAT.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.CSAT,
        'Customer Satisfaction (CSAT)',
        () => val ? `${val}` : 'N/A',
        (v) => v ? (v >= 4 ? 'good' : v >= 3 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.AtRiskCustomerCount) {
      customerMetrics.push(formatMetric(
        m.AtRiskCustomerCount,
        'At-Risk Accounts',
        () => m.AtRiskCustomerCount.current_value.numeric?.toString() ?? 'N/A',
        (v) => v ? (v <= 5 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.AtRiskRevenuePct) {
      const val = m.AtRiskRevenuePct.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.AtRiskRevenuePct,
        'Revenue at Risk',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v <= 5 ? 'good' : v <= 15 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.Top3CustomerConcentrationPct) {
      const val = m.Top3CustomerConcentrationPct.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.Top3CustomerConcentrationPct,
        'Top 3 Customer Concentration',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v <= 20 ? 'good' : v <= 35 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.ExpansionRevenuePct) {
      customerMetrics.push(formatMetric(
        m.ExpansionRevenuePct,
        'Expansion Revenue',
        () => m.ExpansionRevenuePct.current_value.numeric ? `${m.ExpansionRevenuePct.current_value.numeric}%` : 'N/A',
        () => 'neutral'
      ));
    }

    if (m.ActiveUserPct) {
      const val = m.ActiveUserPct.current_value.numeric;
      customerMetrics.push(formatMetric(
        m.ActiveUserPct,
        'Active User Rate',
        () => val ? `${val}%` : 'N/A',
        (v) => v ? (v >= 80 ? 'good' : v >= 50 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    return customerMetrics;
  };

  const customerMetrics = getCustomerMetrics();
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
            <h1 className={commonStyles.pageTitle}>Customer Health</h1>
            <span className={commonStyles.sourceCount}>
              Sources: {sourceDocuments.length}
            </span>
          </div>
          <p className={commonStyles.subtitle}>Customer acquisition, retention, and expansion metrics</p>
        </div>

        <div className={commonStyles.section}>
          <h2 className={commonStyles.sectionTitle}>DATA SOURCES</h2>

          {loading ? (
            <div className={commonStyles.loadingState}>Loading...</div>
          ) : error ? (
            <div className={commonStyles.errorState}>{error}</div>
          ) : !metricsData ? (
            <div className={commonStyles.emptyState}>
              <p>No customer health data available. Run the scoring pipeline first.</p>
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
                        {docMetrics.slice(0, 3).map((m, idx) => (
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

              {/* All Customer Metrics */}
              <div className={styles.allMetricsSection}>
                <h3 className={styles.allMetricsTitle}>All Customer Health Metrics</h3>
                <div className={styles.metricsDetailGrid}>
                  {customerMetrics.map((metric, idx) => (
                    <div
                      key={idx}
                      className={`${styles.metricDetailCard} ${styles[metric.status]}`}
                    >
                      <span className={`${styles.metricDetailValue} ${styles[metric.status]}`}>
                        {metric.value}
                      </span>
                      <span className={styles.metricDetailLabel}>{metric.label}</span>
                      {metric.sources.length > 0 && (
                        <span className={styles.metricDetailSource}>
                          Source: {metric.sources[0].filename.slice(0, 20)}
                          {metric.sources[0].pages.length > 0 && ` (p.${metric.sources[0].pages.join(', ')})`}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
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
              Customer Metrics Extraction
              <span className={commonStyles.lineageNodeMeta}>
                (NRR, GRR, Churn, NPS, etc.)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Customer Health Scoring
              <span className={commonStyles.lineageNodeMeta}>
                (pillar evaluation)
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
                <span className={commonStyles.confidenceNumber}>{customerMetrics.length}</span>
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
