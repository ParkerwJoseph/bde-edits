import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import commonStyles from '../../styles/scoring/common.module.css';
import styles from '../../styles/scoring/SinglePillarDetail.module.css';
import {
  scoringApi,
  PILLAR_CONFIG,
  getHealthStatusColor,
  getHealthStatusLabel
} from '../../api/scoringApi';
import type { PillarDetailResponse, BDEPillar, MetricsWithSourcesResponse, MetricWithSource, MetricSourceInfo } from '../../api/scoringApi';

// Helper to format source info for display
function formatSourceInfo(source: MetricSourceInfo): string {
  if (source.source_type === 'connector') {
    const label = source.source_name || `${source.connector_type}/${source.entity_type}`;
    return source.entity_name ? `${label} (${source.entity_name})` : label;
  } else {
    // Document source
    const pages = source.page_numbers?.length ? ` (p.${source.page_numbers.join(', ')})` : '';
    return `${source.source_name}${pages}`;
  }
}

// Helper to get metrics for a specific pillar
function getPillarMetrics(
  metrics: Record<string, MetricWithSource>,
  pillar: string
): { name: string; value: string; confidence: number; sources: MetricSourceInfo[] }[] {
  const result: { name: string; value: string; confidence: number; sources: MetricSourceInfo[] }[] = [];

  for (const [name, metric] of Object.entries(metrics)) {
    // Check if this metric belongs to this pillar
    if (metric.primary_pillar === pillar || metric.pillars_used_by.includes(pillar)) {
      let value = 'N/A';
      if (metric.current_value.numeric !== null) {
        if (metric.current_value.unit === '$') {
          value = `$${metric.current_value.numeric.toLocaleString()}`;
        } else if (metric.current_value.unit === '%') {
          value = `${metric.current_value.numeric}%`;
        } else {
          value = `${metric.current_value.numeric}${metric.current_value.unit || ''}`;
        }
      } else if (metric.current_value.text) {
        value = metric.current_value.text;
      }

      // Use new unified sources, fallback to legacy source_documents
      const sources = metric.sources || metric.source_documents?.map(sd => ({
        source_type: 'document' as const,
        source_id: sd.document_id,
        source_name: sd.filename,
        page_numbers: sd.page_numbers
      })) || [];

      result.push({
        name,
        value,
        confidence: metric.current_value.confidence,
        sources
      });
    }
  }

  return result;
}

export default function SinglePillarDetail() {
  const { companyId, pillar } = useParams<{ companyId: string; pillar: BDEPillar }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [pillarDetail, setPillarDetail] = useState<PillarDetailResponse | null>(null);
  const [metricsData, setMetricsData] = useState<MetricsWithSourcesResponse | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!companyId || !pillar) return;

      try {
        setLoading(true);
        const [detail, metrics] = await Promise.all([
          scoringApi.getPillarDetail(companyId, pillar as BDEPillar).catch(() => null),
          scoringApi.getMetricsWithSources(companyId).catch(() => null),
        ]);
        setPillarDetail(detail);
        setMetricsData(metrics);
      } catch (err) {
        setError('Failed to load pillar details');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId, pillar]);

  const handleBackClick = () => {
    navigate(`/scoring/${companyId}/pillar-scores`);
  };

  const config = pillar ? PILLAR_CONFIG[pillar as BDEPillar] : null;
  const pillarMetrics = metricsData && pillar ? getPillarMetrics(metricsData.metrics, pillar) : [];

  return (
    <AppLayout>
      <div className={commonStyles.container}>
        <button className={commonStyles.backButton} onClick={handleBackClick}>
          &larr; Back to All Pillars
        </button>

        {loading ? (
          <div className={commonStyles.loadingState}>Loading...</div>
        ) : error ? (
          <div className={commonStyles.errorState}>{error}</div>
        ) : !pillarDetail || !config ? (
          <div className={commonStyles.emptyState}>
            <p>No pillar data available. Run the scoring pipeline first.</p>
          </div>
        ) : (
          <>
            <div className={commonStyles.headerSection}>
              <div className={commonStyles.categoryBadge}>Pillar Analysis</div>
              <div className={commonStyles.titleRow}>
                <h1 className={commonStyles.pageTitle}>{config.label}</h1>
                <span
                  className={styles.healthBadge}
                  style={{
                    backgroundColor: `${getHealthStatusColor(pillarDetail.health_status as any)}20`,
                    color: getHealthStatusColor(pillarDetail.health_status as any)
                  }}
                >
                  {getHealthStatusLabel(pillarDetail.health_status as any)}
                </span>
              </div>
              <p className={commonStyles.subtitle}>
                Weight: {(config.weight * 100).toFixed(0)}% |
                Coverage: {pillarDetail.data_coverage_percent}% |
                Confidence: {pillarDetail.confidence}%
              </p>
            </div>

            {/* Score Overview */}
            <div className={styles.scoreOverview}>
              <div className={styles.scoreCard}>
                <span className={styles.scoreLabel}>Pillar Score</span>
                <span className={styles.scoreValue}>{pillarDetail.score.toFixed(1)}</span>
                <span className={styles.scoreMax}>/5</span>
              </div>
              <div className={styles.scoreBar}>
                <div
                  className={styles.scoreBarFill}
                  style={{
                    width: `${(pillarDetail.score / 5) * 100}%`,
                    backgroundColor: getHealthStatusColor(pillarDetail.health_status as any)
                  }}
                />
              </div>
            </div>

            {/* Justification */}
            {pillarDetail.justification && (
              <div className={commonStyles.section}>
                <h2 className={commonStyles.sectionTitle}>JUSTIFICATION</h2>
                <div className={styles.textCard}>
                  <p>{pillarDetail.justification}</p>
                </div>
              </div>
            )}

            {/* Key Findings */}
            {pillarDetail.key_findings.length > 0 && (
              <div className={commonStyles.section}>
                <h2 className={commonStyles.sectionTitle}>KEY FINDINGS</h2>
                <div className={styles.findingsList}>
                  {pillarDetail.key_findings.map((finding, idx) => (
                    <div key={idx} className={styles.findingItem}>
                      <span className={styles.findingIcon}>✓</span>
                      <span className={styles.findingText}>{finding}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Risks */}
            {pillarDetail.risks.length > 0 && (
              <div className={commonStyles.section}>
                <h2 className={commonStyles.sectionTitle}>RISKS</h2>
                <div className={styles.risksList}>
                  {pillarDetail.risks.map((risk, idx) => (
                    <div key={idx} className={styles.riskItem}>
                      <span className={styles.riskIcon}>⚠</span>
                      <span className={styles.riskText}>{risk}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Data Gaps */}
            {pillarDetail.data_gaps.length > 0 && (
              <div className={commonStyles.section}>
                <h2 className={commonStyles.sectionTitle}>DATA GAPS</h2>
                <div className={styles.gapsList}>
                  {pillarDetail.data_gaps.map((gap, idx) => (
                    <div key={idx} className={styles.gapItem}>
                      <span className={styles.gapIcon}>○</span>
                      <span className={styles.gapText}>{gap}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Related Metrics */}
            {pillarMetrics.length > 0 && (
              <div className={commonStyles.section}>
                <h2 className={commonStyles.sectionTitle}>RELATED METRICS ({pillarMetrics.length})</h2>
                <div className={styles.metricsGrid}>
                  {pillarMetrics.map((metric, idx) => (
                    <div key={idx} className={styles.metricCard}>
                      <span className={styles.metricValue}>{metric.value}</span>
                      <span className={styles.metricLabel}>{metric.name}</span>
                      <span className={styles.metricConfidence}>
                        Confidence: {metric.confidence}%
                      </span>
                      {metric.sources.length > 0 && (
                        <div className={styles.metricSources}>
                          {metric.sources.slice(0, 2).map((source, sIdx) => (
                            <span
                              key={sIdx}
                              className={`${styles.metricSource} ${source.source_type === 'connector' ? styles.connectorSource : styles.documentSource}`}
                              title={formatSourceInfo(source)}
                            >
                              {source.source_type === 'connector' ? '🔗' : '📄'} {formatSourceInfo(source).slice(0, 25)}
                              {formatSourceInfo(source).length > 25 ? '...' : ''}
                            </span>
                          ))}
                          {metric.sources.length > 2 && (
                            <span className={styles.moreSources}>+{metric.sources.length - 2} more</span>
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Evidence Summary */}
            <div className={commonStyles.confidenceSection}>
              <h3 className={commonStyles.confidenceTitle}>Evidence Summary</h3>
              <div className={commonStyles.confidenceGrid}>
                <div className={commonStyles.confidenceItem}>
                  <span className={commonStyles.confidenceNumber}>{pillarDetail.confidence}%</span>
                  <span className={commonStyles.confidenceLabel}>Confidence</span>
                </div>
                <div className={commonStyles.confidenceItem}>
                  <span className={commonStyles.confidenceNumber}>{pillarMetrics.length}</span>
                  <span className={commonStyles.confidenceLabel}>Metrics</span>
                </div>
                <div className={commonStyles.confidenceItem}>
                  <span className={commonStyles.confidenceNumber}>{pillarDetail.evidence_chunk_ids.length}</span>
                  <span className={commonStyles.confidenceLabel}>Evidence Chunks</span>
                </div>
              </div>
            </div>
          </>
        )}
      </div>
    </AppLayout>
  );
}
