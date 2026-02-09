/**
 * DocumentDetail Page
 *
 * Displays document details and extracted chunks with pillar filtering.
 * Based on reference UI design.
 */

import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, ChevronDown, ChevronRight } from 'lucide-react';
import { AppLayout } from '../components/layout/AppLayout';
import {
  documentApi,
  type DocumentWithChunks,
  type BDEPillar,
  PILLAR_LABELS,
  PILLAR_COLORS,
} from '../api/documentApi';
import { formatFileSize } from '../utils/fileUtils';
import styles from '../styles/pages/DocumentDetail.module.css';

const getChunkTypeIcon = (type: string): string => {
  switch (type) {
    case 'text':
      return '📝';
    case 'table':
      return '📊';
    case 'chart':
      return '📈';
    case 'image':
      return '🖼️';
    case 'mixed':
      return '📑';
    default:
      return '📄';
  }
};

export default function DocumentDetail() {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  const [data, setData] = useState<DocumentWithChunks | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPillar, setSelectedPillar] = useState<BDEPillar | 'all'>('all');
  const [expandedChunks, setExpandedChunks] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (documentId) {
      loadDocument();
    }
  }, [documentId]);

  const loadDocument = async () => {
    if (!documentId) return;

    try {
      setIsLoading(true);
      setError(null);
      const response = await documentApi.get(documentId);
      setData(response);
    } catch (err) {
      console.error('Failed to load document:', err);
      setError('Failed to load document. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleChunkExpand = (chunkId: string) => {
    setExpandedChunks((prev) => {
      const next = new Set(prev);
      if (next.has(chunkId)) {
        next.delete(chunkId);
      } else {
        next.add(chunkId);
      }
      return next;
    });
  };

  const handleBack = () => {
    navigate('/ingestion');
  };

  const filteredChunks =
    data?.chunks.filter(
      (chunk) => selectedPillar === 'all' || chunk.pillar === selectedPillar
    ) || [];

  // Group chunks by pillar for summary
  const chunksByPillar =
    data?.chunks.reduce(
      (acc, chunk) => {
        acc[chunk.pillar] = (acc[chunk.pillar] || 0) + 1;
        return acc;
      },
      {} as Record<BDEPillar, number>
    ) || {};

  if (isLoading) {
    return (
      <AppLayout title="Document Details" subtitle="Loading...">
        <div className={styles.container}>
          <div className={styles.infoCard}>
            <div className={styles.loadingState}>Loading document...</div>
          </div>
        </div>
      </AppLayout>
    );
  }

  if (error || !data) {
    return (
      <AppLayout title="Document Details" subtitle="Error">
        <div className={styles.container}>
          <div className={styles.infoCard}>
            <div className={styles.emptyState}>
              <p className={styles.emptyText}>{error || 'Document not found'}</p>
              <button className={styles.backButton} onClick={handleBack}>
                <ArrowLeft size={16} />
                Back to Ingestion
              </button>
            </div>
          </div>
        </div>
      </AppLayout>
    );
  }

  return (
    <AppLayout
      title={data.document.original_filename}
      subtitle={`${data.chunk_count} chunks extracted`}
    >
      <div className={styles.container}>
        {/* Document Info */}
        <div className={styles.infoCard}>
          <div className={styles.infoHeader}>
            <div className={styles.infoMeta}>
              <span>{formatFileSize(data.document.file_size)}</span>
              <span>•</span>
              <span>{data.document.total_pages} pages</span>
              <span>•</span>
              <span>Uploaded {new Date(data.document.created_at).toLocaleDateString()}</span>
            </div>
            <button className={styles.backButton} onClick={handleBack}>
              <ArrowLeft size={16} />
              Back to Ingestion
            </button>
          </div>

          {/* Pillar Summary */}
          {Object.keys(chunksByPillar).length > 0 && (
            <div className={styles.pillarSection}>
              <h4 className={styles.pillarTitle}>Chunks by Pillar</h4>
              <div className={styles.pillarFilters}>
                {(Object.entries(chunksByPillar) as [BDEPillar, number][]).map(
                  ([pillar, count]) => (
                    <button
                      key={pillar}
                      onClick={() => setSelectedPillar(pillar)}
                      className={`${styles.pillarButton} ${
                        selectedPillar === pillar ? styles.pillarButtonActive : ''
                      }`}
                      style={{
                        borderColor: PILLAR_COLORS[pillar],
                        backgroundColor:
                          selectedPillar === pillar
                            ? `${PILLAR_COLORS[pillar]}20`
                            : 'transparent',
                        color: PILLAR_COLORS[pillar],
                      }}
                    >
                      {PILLAR_LABELS[pillar]} ({count})
                    </button>
                  )
                )}
                {selectedPillar !== 'all' && (
                  <button
                    className={styles.showAllButton}
                    onClick={() => setSelectedPillar('all')}
                  >
                    Show All
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Chunks List */}
        <div className={styles.chunksCard}>
          <h3 className={styles.chunksHeader}>Extracted Chunks ({filteredChunks.length})</h3>

          {filteredChunks.length === 0 ? (
            <div className={styles.emptyState}>
              <p className={styles.emptyText}>No chunks found for this filter</p>
            </div>
          ) : (
            <div className={styles.chunksList}>
              {filteredChunks.map((chunk) => {
                const isExpanded = expandedChunks.has(chunk.id);
                return (
                  <div key={chunk.id} className={styles.chunkItem}>
                    {/* Chunk Header */}
                    <div
                      className={styles.chunkHeader}
                      onClick={() => toggleChunkExpand(chunk.id)}
                    >
                      <span className={styles.chunkIcon}>
                        {getChunkTypeIcon(chunk.chunk_type)}
                      </span>
                      <div className={styles.chunkInfo}>
                        <div className={styles.chunkMeta}>
                          <span
                            className={styles.pillarBadge}
                            style={{
                              backgroundColor: `${PILLAR_COLORS[chunk.pillar]}20`,
                              color: PILLAR_COLORS[chunk.pillar],
                            }}
                          >
                            {PILLAR_LABELS[chunk.pillar]}
                          </span>
                          <span className={styles.chunkPage}>Page {chunk.page_number}</span>
                          {chunk.confidence_score && (
                            <span className={styles.chunkConfidence}>
                              • {Math.round(chunk.confidence_score * 100)}% confidence
                            </span>
                          )}
                        </div>
                        <p className={styles.chunkSummary}>{chunk.summary}</p>
                      </div>
                      <span className={styles.expandIcon}>
                        {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                      </span>
                    </div>

                    {/* Chunk Content */}
                    {isExpanded && (
                      <div className={styles.chunkContent}>
                        {chunk.previous_context && (
                          <div className={styles.previousContext}>
                            <span className={styles.previousContextLabel}>
                              Previous Context:{' '}
                            </span>
                            {chunk.previous_context}
                          </div>
                        )}
                        <div className={styles.contentText}>{chunk.content}</div>
                        {chunk.metadata && Object.keys(chunk.metadata).length > 0 && (
                          <div className={styles.metadataSection}>
                            <div className={styles.metadataLabel}>Metadata</div>
                            <pre className={styles.metadataContent}>
                              {JSON.stringify(chunk.metadata, null, 2)}
                            </pre>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
