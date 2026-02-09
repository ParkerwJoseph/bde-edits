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
        } else if (metric.current_value.unit === 'ms') {
          value = `${metric.current_value.numeric}ms`;
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

export default function ProductHealthDetail() {
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
        setError('Failed to load product health data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  const handleBackClick = () => {
    navigate('/');
  };

  // Extract product-related metrics with source information
  const getProductMetrics = () => {
    if (!metricsData) return [];

    const m = metricsData.metrics;
    const productMetrics: {
      label: string;
      value: string;
      status: 'good' | 'warning' | 'bad' | 'neutral';
      sources: { filename: string; pages: number[] }[];
    }[] = [];

    const formatMetric = (
      metric: MetricWithSource,
      label: string,
      getValue: () => string,
      getStatus: (val: number | string | null) => 'good' | 'warning' | 'bad' | 'neutral'
    ) => ({
      label,
      value: getValue(),
      status: getStatus(metric.current_value.numeric ?? metric.current_value.text),
      sources: metric.source_documents?.map(sd => ({ filename: sd.filename, pages: sd.page_numbers })) || []
    });

    if (m.UptimePct) {
      const val = m.UptimePct.current_value.numeric;
      productMetrics.push(formatMetric(
        m.UptimePct,
        'Uptime',
        () => val ? `${val}%` : 'N/A',
        (v) => typeof v === 'number' ? (v >= 99.9 ? 'good' : v >= 99 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.AvgResponseTimeMs) {
      const val = m.AvgResponseTimeMs.current_value.numeric;
      productMetrics.push(formatMetric(
        m.AvgResponseTimeMs,
        'Avg Response Time',
        () => val ? `${val}ms` : 'N/A',
        (v) => typeof v === 'number' ? (v <= 200 ? 'good' : v <= 500 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.ErrorRatePct) {
      const val = m.ErrorRatePct.current_value.numeric;
      productMetrics.push(formatMetric(
        m.ErrorRatePct,
        'Error Rate',
        () => val ? `${val}%` : 'N/A',
        (v) => typeof v === 'number' ? (v <= 0.5 ? 'good' : v <= 2 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.DeployFrequency) {
      productMetrics.push(formatMetric(
        m.DeployFrequency,
        'Deploy Frequency',
        () => m.DeployFrequency.current_value.numeric ? `${m.DeployFrequency.current_value.numeric}/day` : 'N/A',
        () => 'neutral'
      ));
    }

    if (m.TechDebtLevel) {
      const val = m.TechDebtLevel.current_value.text;
      productMetrics.push(formatMetric(
        m.TechDebtLevel,
        'Tech Debt Level',
        () => val ?? 'N/A',
        (v) => v === 'Low' ? 'good' : v === 'Medium' ? 'warning' : v === 'High' ? 'bad' : 'neutral'
      ));
    }

    if (m.TestCoveragePct) {
      const val = m.TestCoveragePct.current_value.numeric;
      productMetrics.push(formatMetric(
        m.TestCoveragePct,
        'Test Coverage',
        () => val ? `${val}%` : 'N/A',
        (v) => typeof v === 'number' ? (v >= 70 ? 'good' : v >= 40 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.ArchitectureType) {
      const val = m.ArchitectureType.current_value.text;
      productMetrics.push(formatMetric(
        m.ArchitectureType,
        'Architecture',
        () => val ?? 'N/A',
        (v) => v === 'Modular' ? 'good' : v === 'Mixed' ? 'warning' : v === 'Monolithic' ? 'bad' : 'neutral'
      ));
    }

    if (m.APIType) {
      productMetrics.push(formatMetric(
        m.APIType,
        'API Type',
        () => m.APIType.current_value.text ?? 'N/A',
        () => 'neutral'
      ));
    }

    if (m.SecurityCompliance) {
      const val = m.SecurityCompliance.current_value.text;
      productMetrics.push(formatMetric(
        m.SecurityCompliance,
        'Security Compliance',
        () => val ?? 'N/A',
        (v) => typeof v === 'string' && (v.includes('SOC2') || v.includes('ISO')) ? 'good' : v === 'Basic' ? 'warning' : 'neutral'
      ));
    }

    if (m.IncidentFrequency) {
      const val = m.IncidentFrequency.current_value.numeric;
      productMetrics.push(formatMetric(
        m.IncidentFrequency,
        'Incidents/Month',
        () => val !== null ? `${val}` : 'N/A',
        (v) => typeof v === 'number' ? (v <= 2 ? 'good' : v <= 5 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    if (m.BusFactorRisk) {
      const val = m.BusFactorRisk.current_value.text;
      productMetrics.push(formatMetric(
        m.BusFactorRisk,
        'Bus Factor Risk',
        () => val ?? 'N/A',
        (v) => v === 'None' ? 'good' : v === 'Some' ? 'warning' : v === 'High' ? 'bad' : 'neutral'
      ));
    }

    if (m.RoadmapDeliveryPct) {
      const val = m.RoadmapDeliveryPct.current_value.numeric;
      productMetrics.push(formatMetric(
        m.RoadmapDeliveryPct,
        'Roadmap Delivery',
        () => val ? `${val}%` : 'N/A',
        (v) => typeof v === 'number' ? (v >= 75 ? 'good' : v >= 50 ? 'warning' : 'bad') : 'neutral'
      ));
    }

    return productMetrics;
  };

  const productMetrics = getProductMetrics();
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
            <h1 className={commonStyles.pageTitle}>Product Health</h1>
            <span className={commonStyles.sourceCount}>
              Sources: {sourceDocuments.length}
            </span>
          </div>
          <p className={commonStyles.subtitle}>Technical performance and reliability metrics</p>
        </div>

        <div className={commonStyles.section}>
          <h2 className={commonStyles.sectionTitle}>DATA SOURCES</h2>

          {loading ? (
            <div className={commonStyles.loadingState}>Loading...</div>
          ) : error ? (
            <div className={commonStyles.errorState}>{error}</div>
          ) : !metricsData ? (
            <div className={commonStyles.emptyState}>
              <p>No product health data available. Run the scoring pipeline first.</p>
            </div>
          ) : (
            <>
              {sourceDocuments.slice(0, 3).map((doc) => {
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

              {/* All Product Metrics */}
              <div className={styles.allMetricsSection}>
                <h3 className={styles.allMetricsTitle}>All Product Health Metrics</h3>
                <div className={styles.metricsDetailGrid}>
                  {productMetrics.map((metric, idx) => (
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
              Product Metrics Extraction
              <span className={commonStyles.lineageNodeMeta}>
                (uptime, latency, etc.)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Product Health Scoring
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
                <span className={commonStyles.confidenceNumber}>{productMetrics.length}</span>
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
