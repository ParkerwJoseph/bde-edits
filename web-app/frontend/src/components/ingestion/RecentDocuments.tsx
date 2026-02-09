/**
 * RecentDocuments Component
 *
 * Displays a list of recently uploaded documents with status,
 * chunk count, and actions like View Chunks and Delete.
 * Based on reference UI design.
 */

import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { FileText, Trash2, Eye, ChevronLeft, ChevronRight } from 'lucide-react';
import { documentApi, type Document, type DocumentStatus } from '../../api/documentApi';
import { useToast } from '../../components/common/Toast';
import ConfirmModal from '../../components/common/ConfirmModal';
import { formatFileSize, getFileIcon } from '../../utils/fileUtils';
import styles from '../../styles/components/ingestion/RecentDocuments.module.css';

export interface RecentDocumentsProps {
  companyId: string | null;
  refreshTrigger?: number;
}

const getStatusConfig = (status: DocumentStatus) => {
  switch (status) {
    case 'pending':
      return { label: 'Pending', className: styles.statusPending };
    case 'processing':
      return { label: 'Processing', className: styles.statusProcessing };
    case 'completed':
      return { label: 'Completed', className: styles.statusCompleted };
    case 'failed':
      return { label: 'Failed', className: styles.statusFailed };
    default:
      return { label: 'Unknown', className: styles.statusPending };
  }
};

export function RecentDocuments({ companyId, refreshTrigger }: RecentDocumentsProps) {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const pageSize = 5;

  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; document: Document | null }>({
    isOpen: false,
    document: null,
  });
  const [isDeleting, setIsDeleting] = useState(false);

  const toast = useToast();

  useEffect(() => {
    if (companyId) {
      loadDocuments();
    } else {
      setDocuments([]);
      setTotalDocuments(0);
      setIsLoading(false);
    }
  }, [companyId, currentPage, refreshTrigger]);

  const loadDocuments = async () => {
    if (!companyId) return;

    try {
      setIsLoading(true);
      const response = await documentApi.list({
        company_id: companyId,
        skip: currentPage * pageSize,
        limit: pageSize,
      });
      setDocuments(response.documents);
      setTotalDocuments(response.total);
    } catch (error) {
      console.error('Failed to load documents:', error);
      toast.error('Failed to load documents', 'Could not fetch recent documents.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteClick = (doc: Document) => {
    setDeleteModal({ isOpen: true, document: doc });
  };

  const handleDeleteConfirm = async () => {
    if (!deleteModal.document) return;

    setIsDeleting(true);
    try {
      await documentApi.delete(deleteModal.document.id);
      toast.success('Document deleted', `"${deleteModal.document.original_filename}" has been deleted.`);
      setDeleteModal({ isOpen: false, document: null });
      loadDocuments();
    } catch (error) {
      console.error('Failed to delete document:', error);
      toast.error('Failed to delete', 'Could not delete the document. Please try again.');
    } finally {
      setIsDeleting(false);
    }
  };

  const handleDeleteCancel = () => {
    setDeleteModal({ isOpen: false, document: null });
  };

  const totalPages = Math.ceil(totalDocuments / pageSize);
  const canGoPrev = currentPage > 0;
  const canGoNext = currentPage < totalPages - 1;

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Recent Documents</h2>
        {totalDocuments > 0 && (
          <span className={styles.count}>{totalDocuments} total</span>
        )}
      </div>

      <div className={styles.content}>
        {isLoading ? (
          <div className={styles.empty}>Loading documents...</div>
        ) : documents.length === 0 ? (
          <div className={styles.empty}>
            <FileText className={styles.emptyIcon} size={32} />
            <p>No documents uploaded yet</p>
          </div>
        ) : (
          <>
            <div className={styles.documentList}>
              {documents.map((doc) => {
                const statusConfig = getStatusConfig(doc.status);
                return (
                  <div key={doc.id} className={styles.documentItem}>
                    <div className={styles.documentIcon}>
                      {getFileIcon(doc.original_filename)}
                    </div>

                    <div className={styles.documentInfo}>
                      <span className={styles.documentName}>{doc.original_filename}</span>
                      <div className={styles.documentMeta}>
                        <span>{formatFileSize(doc.file_size)}</span>
                        <span>•</span>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                        {doc.total_pages && (
                          <>
                            <span>•</span>
                            <span>{doc.total_pages} pages</span>
                          </>
                        )}
                        {doc.status === 'completed' && doc.chunk_count !== undefined && (
                          <>
                            <span>•</span>
                            <span className={styles.chunkCount}>{doc.chunk_count} chunks</span>
                          </>
                        )}
                      </div>
                    </div>

                    <span className={`${styles.statusBadge} ${statusConfig.className}`}>
                      {statusConfig.label}
                    </span>

                    <div className={styles.documentActions}>
                      {doc.status === 'completed' && (
                        <Link
                          to={`/documents/${doc.id}`}
                          className={styles.actionButton}
                          title="View Chunks"
                        >
                          <Eye size={16} />
                          <span>View Chunks</span>
                        </Link>
                      )}
                      <button
                        className={`${styles.actionButton} ${styles.deleteButton}`}
                        onClick={() => handleDeleteClick(doc)}
                        title="Delete document"
                      >
                        <Trash2 size={16} />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>

            {totalPages > 1 && (
              <div className={styles.pagination}>
                <span className={styles.paginationInfo}>
                  {currentPage * pageSize + 1}-{Math.min((currentPage + 1) * pageSize, totalDocuments)} of {totalDocuments}
                </span>
                <div className={styles.paginationButtons}>
                  <button
                    className={styles.paginationButton}
                    onClick={() => setCurrentPage((p) => p - 1)}
                    disabled={!canGoPrev}
                  >
                    <ChevronLeft size={16} />
                  </button>
                  <button
                    className={styles.paginationButton}
                    onClick={() => setCurrentPage((p) => p + 1)}
                    disabled={!canGoNext}
                  >
                    <ChevronRight size={16} />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>

      <ConfirmModal
        isOpen={deleteModal.isOpen}
        type="danger"
        title="Delete Document"
        message={`Are you sure you want to delete "${deleteModal.document?.original_filename}"? This action cannot be undone.`}
        confirmText="Delete"
        cancelText="Cancel"
        isLoading={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={handleDeleteCancel}
      />
    </div>
  );
}

export default RecentDocuments;
