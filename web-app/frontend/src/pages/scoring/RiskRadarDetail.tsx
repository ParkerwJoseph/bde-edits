import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { AppLayout } from '../../components/layout/AppLayout';
import commonStyles from '../../styles/scoring/common.module.css';
import styles from '../../styles/scoring/RiskRadarDetail.module.css';
import { scoringApi } from '../../api/scoringApi';
import type { FlagsResponse, DataSourcesResponse, SourceDocumentInfo } from '../../api/scoringApi';

export default function RiskRadarDetail() {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [flags, setFlags] = useState<FlagsResponse | null>(null);
  const [dataSources, setDataSources] = useState<DataSourcesResponse | null>(null);
  const [sourceDocuments, setSourceDocuments] = useState<SourceDocumentInfo[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      if (!companyId) return;

      try {
        setLoading(true);
        const [flagsData, sources] = await Promise.all([
          scoringApi.getFlags(companyId).catch(() => null),
          scoringApi.getDataSources(companyId).catch(() => null),
        ]);
        setFlags(flagsData);
        setDataSources(sources);
        setSourceDocuments(sources?.documents || []);
      } catch (err) {
        setError('Failed to load risk data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [companyId]);

  const handleBackClick = () => {
    navigate('/');
  };

  const totalFlags = flags
    ? flags.red_flags.length + flags.yellow_flags.length + flags.green_accelerants.length
    : 0;

  return (
    <AppLayout>
      <div className={commonStyles.container}>
        <button className={commonStyles.backButton} onClick={handleBackClick}>
          &larr; Back to Dashboard
        </button>

        <div className={commonStyles.headerSection}>
          <div className={commonStyles.categoryBadge}>Insights & Priorities</div>
          <div className={commonStyles.titleRow}>
            <h1 className={commonStyles.pageTitle}>Risk Radar</h1>
            <span className={commonStyles.sourceCount}>
              Sources: {sourceDocuments.length}
            </span>
          </div>
          <p className={commonStyles.subtitle}>Active business risks by severity</p>
        </div>

        <div className={commonStyles.section}>
          <h2 className={commonStyles.sectionTitle}>DATA SOURCES</h2>

          {loading ? (
            <div className={commonStyles.loadingState}>Loading...</div>
          ) : error ? (
            <div className={commonStyles.errorState}>{error}</div>
          ) : !flags ? (
            <div className={commonStyles.emptyState}>
              <p>No risk data available. Run the scoring pipeline first.</p>
            </div>
          ) : (
            <>
              <div className={commonStyles.documentsContainer}>
                {sourceDocuments.filter(doc => doc.chunks_count > 0).map((doc) => (
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
                      Chunks: <span className={commonStyles.confidenceValue}>{doc.chunks_count}</span>
                    </div>
                  </div>

                  <div className={commonStyles.extractedValues}>
                    <span className={commonStyles.valuesLabel}>Flag Summary</span>
                    <div className={commonStyles.valuesGrid}>
                      <div className={commonStyles.valueCard}>
                        <span className={commonStyles.valueLabel} style={{ color: '#ef4444' }}>High Risks</span>
                        <span className={commonStyles.valueNumber}>{flags.red_flags.length}</span>
                      </div>
                      <div className={commonStyles.valueCard}>
                        <span className={commonStyles.valueLabel} style={{ color: '#f59e0b' }}>Medium Risks</span>
                        <span className={commonStyles.valueNumber}>{flags.yellow_flags.length}</span>
                      </div>
                      <div className={commonStyles.valueCard}>
                        <span className={commonStyles.valueLabel} style={{ color: '#22c55e' }}>Accelerants</span>
                        <span className={commonStyles.valueNumber}>{flags.green_accelerants.length}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              </div>

              {/* Red Flags Section */}
              {flags.red_flags.length > 0 && (
                <div className={styles.flagsSection}>
                  <h3 className={styles.flagsSectionTitle} style={{ color: '#ef4444' }}>
                    Red Flags ({flags.red_flags.length})
                  </h3>
                  <div className={styles.flagsList}>
                    {flags.red_flags.map((flag, idx) => (
                      <div key={idx} className={`${styles.flagCard} ${styles.redFlag}`}>
                        <div className={styles.flagHeader}>
                          <span className={styles.flagText}>{flag.text}</span>
                          <span className={styles.flagSeverity}>Severity: {flag.severity}/10</span>
                        </div>
                        <div className={styles.flagMeta}>
                          <span className={styles.flagCategory}>{flag.category}</span>
                          <span className={styles.flagPillar}>{flag.pillar}</span>
                          {flag.source && (
                            <span className={styles.flagSource}>Source: {flag.source}</span>
                          )}
                        </div>
                        {flag.rationale && (
                          <p className={styles.flagRationale}>{flag.rationale}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Yellow Flags Section */}
              {flags.yellow_flags.length > 0 && (
                <div className={styles.flagsSection}>
                  <h3 className={styles.flagsSectionTitle} style={{ color: '#f59e0b' }}>
                    Yellow Flags ({flags.yellow_flags.length})
                  </h3>
                  <div className={styles.flagsList}>
                    {flags.yellow_flags.map((flag, idx) => (
                      <div key={idx} className={`${styles.flagCard} ${styles.yellowFlag}`}>
                        <div className={styles.flagHeader}>
                          <span className={styles.flagText}>{flag.text}</span>
                          <span className={styles.flagSeverity}>Severity: {flag.severity}/10</span>
                        </div>
                        <div className={styles.flagMeta}>
                          <span className={styles.flagCategory}>{flag.category}</span>
                          <span className={styles.flagPillar}>{flag.pillar}</span>
                          {flag.source && (
                            <span className={styles.flagSource}>Source: {flag.source}</span>
                          )}
                        </div>
                        {flag.rationale && (
                          <p className={styles.flagRationale}>{flag.rationale}</p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Green Accelerants Section */}
              {flags.green_accelerants.length > 0 && (
                <div className={styles.flagsSection}>
                  <h3 className={styles.flagsSectionTitle} style={{ color: '#22c55e' }}>
                    Green Accelerants ({flags.green_accelerants.length})
                  </h3>
                  <div className={styles.flagsList}>
                    {flags.green_accelerants.map((flag, idx) => (
                      <div key={idx} className={`${styles.flagCard} ${styles.greenFlag}`}>
                        <div className={styles.flagHeader}>
                          <span className={styles.flagText}>{flag.text}</span>
                        </div>
                        <div className={styles.flagMeta}>
                          <span className={styles.flagCategory}>{flag.category}</span>
                          <span className={styles.flagPillar}>{flag.pillar}</span>
                          {flag.source && (
                            <span className={styles.flagSource}>Source: {flag.source}</span>
                          )}
                        </div>
                        {flag.rationale && (
                          <p className={styles.flagRationale}>{flag.rationale}</p>
                        )}
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
              Text Chunking
              <span className={commonStyles.lineageNodeMeta}>
                ({dataSources?.total_chunks || 0} chunks)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Risk Analysis
              <span className={commonStyles.lineageNodeMeta}>
                (LLM evaluation)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNode}>
              Flag Classification
              <span className={commonStyles.lineageNodeMeta}>
                (RED/YELLOW/GREEN)
              </span>
            </span>
            <span className={commonStyles.lineageArrow}>&rarr;</span>
            <span className={commonStyles.lineageNodeFinal}>Dashboard</span>
          </div>
        </div>

        {/* Confidence Summary */}
        {flags && (
          <div className={commonStyles.confidenceSection}>
            <h3 className={commonStyles.confidenceTitle}>Analysis Summary</h3>
            <div className={commonStyles.confidenceGrid}>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>
                  {dataSources?.total_chunks || 0}
                </span>
                <span className={commonStyles.confidenceLabel}>Text Chunks Analyzed</span>
              </div>
              <div className={commonStyles.confidenceItem}>
                <span className={commonStyles.confidenceNumber}>{totalFlags}</span>
                <span className={commonStyles.confidenceLabel}>Total Flags</span>
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
