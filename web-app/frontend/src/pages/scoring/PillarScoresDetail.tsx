import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import commonStyles from '../../styles/scoring/common.module.css';
import styles from '../../styles/scoring/PillarScoresDetail.module.css';
import {
  scoringApi,
  PILLAR_CONFIG,
  getHealthStatusColor,
  getHealthStatusLabel
} from '../../api/scoringApi';
import type { BDEScoreResponse, BDEPillar, DataSourcesResponse, SourceDocumentInfo, MetricsWithSourcesResponse, MetricWithSource } from '../../api/scoringApi';

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

export default function PillarScoresDetail() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [scoreData, setScoreData] = useState<BDEScoreResponse | null>(null);
  const [dataSources, setDataSources] = useState<DataSourcesResponse | null>(null);
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocumentInfo[]>([]);
  const [metricsData, setMetricsData] = useState<MetricsWithSourcesResponse | null>(null);

  const handlePillarClick = (pillar: BDEPillar) => {
    if (companyId) {
      navigate(`/scoring/${companyId}/pillars/${pillar}`);
    }
  };

  useEffect(() => {
    const fetchData = async () => {
      if (!companyId) return;

      try {
        setLoading(true);
        const [scores, sources, metricsWithSources] = await Promise.all([
          scoringApi.getBDEScore(companyId).catch(() => null),
          scoringApi.getDataSources(companyId).catch(() => null),
          scoringApi.getMetricsWithSources(companyId).catch(() => null),
        ]);
        setScoreData(scores);
        setDataSources(sources);
        setMetricsData(metricsWithSources);
        setSourceDocuments(sources?.documents || []);
      } catch (err) {
        setError('Failed to load pillar scores');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  console.log("Scores Data", scoreData);
  console.log("Data Sources", dataSources);
  console.log("Metrics Data", metricsData);  

  const handleBackClick = () => {
    navigate('/');
  };

  return (
    <AppLayout>
      <div className={commonStyles.container}>
        <button className={commonStyles.backButton} onClick={handleBackClick}>
          &larr; Back to Dashboard
        </button>

        <div className={commonStyles.headerSection}>
          <div className={commonStyles.categoryBadge}>Metrics & KPIs</div>
          <div className={commonStyles.titleRow}>
            <h1 className={commonStyles.pageTitle}>Pillar Scores</h1>
            <span className={commonStyles.sourceCount}>
              Sources: {sourceDocuments.length}
            </span>
          </div>
          <p className={commonStyles.subtitle}>Health scores across 8 business pillars</p>
        </div>

        <div className={commonStyles.section}>
          <h2 className={commonStyles.sectionTitle}>DATA SOURCES</h2>

          {loading ? (
            <div className={commonStyles.loadingState}>Loading...</div>
          ) : error ? (
            <div className={commonStyles.errorState}>{error}</div>
          ) : !scoreData ? (
            <div className={commonStyles.emptyState}>
              <p>No scoring data available. Run the scoring pipeline first.</p>
            </div>
          ) : (
            <>
              <div className={commonStyles.documentsContainer}>
                {sourceDocuments.filter(doc => doc.metrics_count > 0).map((doc) => (
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
                      {metricsData && getMetricsFromDocument(metricsData.metrics, doc.id).length > 0 ? (
                        getMetricsFromDocument(metricsData.metrics, doc.id).slice(0, 3).map((m, idx) => (
                          <div key={idx} className={commonStyles.valueCard}>
                            <span className={commonStyles.valueLabel}>
                              {m.name}
                              {m.pages.length > 0 && (
                                <span className={commonStyles.pageRef}> (p.{m.pages.join(', ')})</span>
                              )}
                            </span>
                            <span className={commonStyles.valueNumber}>{m.value}</span>
                          </div>
                        ))
                      ) : (
                        <div className={commonStyles.emptyState} style={{ fontSize: '0.875rem', padding: '0.5rem' }}>
                          No metrics extracted from this document
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
              </div>

              {/* All Pillar Scores */}
              <div className={styles.allScoresSection}>
                <h3 className={styles.allScoresTitle}>All Pillar Scores</h3>
                <div className={styles.pillarGrid}>
                  {PILLAR_ORDER.map((pillar) => {
                    const score = scoreData.pillar_scores[pillar];
                    const config = PILLAR_CONFIG[pillar];
                    return (
                      <div
                        key={pillar}
                        className={styles.pillarCard}
                        onClick={() => handlePillarClick(pillar)}
                        style={{ cursor: 'pointer' }}
                      >
                        <div className={styles.pillarHeader}>
                          <span className={styles.pillarName}>{config.label}</span>
                          <span
                            className={styles.healthBadge}
                            style={{
                              backgroundColor: `${getHealthStatusColor(score.health_status)}20`,
                              color: getHealthStatusColor(score.health_status)
                            }}
                          >
                            {getHealthStatusLabel(score.health_status)}
                          </span>
                        </div>
                        <div className={styles.pillarScore}>
                          <span className={styles.scoreNumber}>{score.score.toFixed(1)}</span>
                          <span className={styles.scoreMax}>/5</span>
                        </div>
                        <div className={styles.pillarMeta}>
                          <span>Coverage: {score.data_coverage}%</span>
                          <span>Weight: {(config.weight * 100).toFixed(0)}%</span>
                        </div>
                      </div>
                    );
                  })}
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
              Metric Extraction
              <span className={commonStyles.lineageNodeMeta}>
                ({dataSources?.total_metrics || 0} metrics)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Pillar Evaluation
              <span className={commonStyles.lineageNodeMeta}>
                (8 pillars)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              BDE Calculation
              <span className={commonStyles.lineageNodeMeta}>
                (weighted scoring)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNodeFinal}>Dashboard</span>
          </div>
        </div>

        {/* Confidence Summary */}
        {scoreData && (
          <div className={commonStyles.confidenceSection}>
            <h3 className={commonStyles.confidenceTitle}>Confidence Summary</h3>
            <div className={commonStyles.confidenceGrid}>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>{scoreData.confidence}%</span>
                <span className={commonStyles.confidenceLabel}>Average Confidence</span>
              </div>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>
                  {dataSources?.total_metrics || 0}
                </span>
                <span className={commonStyles.confidenceLabel}>Total Metrics</span>
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
