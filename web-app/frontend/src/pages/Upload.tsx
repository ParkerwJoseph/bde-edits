import { useState, useRef, useEffect } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import styles from '../styles/Upload.module.css';
import { documentApi, type Document, type DocumentStatus } from '../api/documentApi';
import { companyApi, type Company } from '../api/companyApi';
import { useToast } from '../components/common/Toast';
import ConfirmModal from '../components/common/ConfirmModal';
import DocumentPreviewModal from '../components/common/DocumentPreviewModal';
import { useDocumentProgressContext } from '../context/DocumentProgressContext';
import {
  ALL_ALLOWED_EXTENSIONS,
  ALLOWED_EXTENSIONS,
  formatFileSize,
  getFileIcon,
  getExtension,
} from '../utils/fileUtils';

// Processing steps for progress bar
const PROCESSING_STEPS = [
  { step: 1, name: 'Uploading' },
  { step: 2, name: 'Analyzing' },
  { step: 3, name: 'Chunking' },
  { step: 4, name: 'Embeddings' },
  { step: 5, name: 'Storing' },
  { step: 6, name: 'Done' },
];

interface FileProgress {
  step: number;
  stepName: string;
  progress: number;
}

interface SelectedFile {
  id: string;
  file: File;
  relativePath: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  documentId?: string;
  error?: string;
  progress?: FileProgress;
}

const getStatusBadge = (status: SelectedFile['status']): { text: string; className: string } => {
  switch (status) {
    case 'pending':
      return { text: 'Pending', className: styles.statusPending };
    case 'uploading':
      return { text: 'Uploading...', className: styles.statusUploading };
    case 'processing':
      return { text: 'Processing...', className: styles.statusProcessing };
    case 'completed':
      return { text: 'Completed', className: styles.statusCompleted };
    case 'failed':
      return { text: 'Failed', className: styles.statusFailed };
    default:
      return { text: 'Unknown', className: styles.statusPending };
  }
};

const processFiles = (files: File[]): SelectedFile[] => {
  const result: SelectedFile[] = [];

  for (const file of files) {
    const relativePath = (file as File & { webkitRelativePath?: string }).webkitRelativePath || file.name;
    const ext = getExtension(file.name);

    if (!ALL_ALLOWED_EXTENSIONS.includes(ext)) continue;

    result.push({
      id: `${file.name}-${Date.now()}-${Math.random()}`,
      file,
      relativePath,
      status: 'pending',
    });
  }

  return result;
};

export default function Upload() {
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [recentDocuments, setRecentDocuments] = useState<Document[]>([]);
  const [isLoadingDocuments, setIsLoadingDocuments] = useState(true);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const pageSize = 10;
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const [companies, setCompanies] = useState<Company[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<string>('');
  const [isLoadingCompanies, setIsLoadingCompanies] = useState(true);

  const [deleteModal, setDeleteModal] = useState<{ isOpen: boolean; document: Document | null }>({
    isOpen: false,
    document: null,
  });
  const [isDeleting, setIsDeleting] = useState(false);

  const [previewModal, setPreviewModal] = useState<{
    isOpen: boolean;
    documentUrl: string | null;
    filename: string;
    fileType: string;
  }>({
    isOpen: false,
    documentUrl: null,
    filename: '',
    fileType: '',
  });

  const toast = useToast();

  // Use global progress context - WebSocket stays connected across page navigation
  const { progressMap, trackDocument } = useDocumentProgressContext();

  // Sync global progress state with local files state
  useEffect(() => {
    setFiles((prev) => {
      let hasChanges = false;
      const updated = prev.map((f) => {
        if (!f.documentId) return f;

        const globalProgress = progressMap.get(f.documentId);
        if (!globalProgress) return f;

        // Check if status changed to completed
        if (globalProgress.status === 'completed' && f.status !== 'completed') {
          hasChanges = true;
          // Trigger refresh to update document list
          setCurrentPage(0);
          setRefreshTrigger((t) => t + 1);
          return {
            ...f,
            status: 'completed' as const,
            progress: { step: 6, stepName: 'Completed', progress: 100 },
          };
        }

        // Check if status changed to failed
        if (globalProgress.status === 'failed' && f.status !== 'failed') {
          hasChanges = true;
          setRefreshTrigger((t) => t + 1);
          return {
            ...f,
            status: 'failed' as const,
            error: globalProgress.error_message || 'Processing failed',
          };
        }

        // Update progress if still processing
        if (globalProgress.status === 'processing') {
          const newProgress = {
            step: globalProgress.step,
            stepName: globalProgress.step_name,
            progress: globalProgress.progress,
          };

          if (
            f.progress?.step !== newProgress.step ||
            f.progress?.progress !== newProgress.progress
          ) {
            hasChanges = true;
            return { ...f, progress: newProgress };
          }
        }

        return f;
      });

      return hasChanges ? updated : prev;
    });
  }, [progressMap]);

  // Restore progress for documents that are still processing when page loads
  // This adds placeholder files for processing documents from global context
  useEffect(() => {
    const processingDocs = recentDocuments.filter((doc) => doc.status === 'processing');

    if (processingDocs.length === 0) return;

    console.log(`[Progress Restore] Found ${processingDocs.length} processing document(s)`);

    setFiles((prev) => {
      const newFiles = [...prev];
      let hasChanges = false;

      for (const doc of processingDocs) {
        // Check if we already have this document in local state
        const existingFile = newFiles.find((f) => f.documentId === doc.id);
        if (existingFile) continue;

        // Get progress from global context
        const globalProgress = progressMap.get(doc.id);

        // Add a placeholder for this processing document
        const placeholderFile: SelectedFile = {
          id: `restored-${doc.id}`,
          file: new File([], doc.original_filename),
          relativePath: doc.original_filename,
          status: 'processing',
          documentId: doc.id,
          progress: globalProgress
            ? {
                step: globalProgress.step,
                stepName: globalProgress.step_name,
                progress: globalProgress.progress,
              }
            : { step: 2, stepName: 'Processing', progress: 0 },
        };

        console.log(`[Progress Restore] Adding placeholder for ${doc.id}`);
        newFiles.push(placeholderFile);
        hasChanges = true;

        // Also track in global context if not already tracked
        if (!globalProgress) {
          trackDocument(doc.id, doc.original_filename);
        }
      }

      return hasChanges ? newFiles : prev;
    });
  }, [recentDocuments]); // Run when documents list changes

  useEffect(() => {
    loadCompanies();
  }, []);

  useEffect(() => {
    if (selectedCompanyId) {
      loadRecentDocuments(currentPage);
    }
  }, [currentPage, selectedCompanyId, refreshTrigger]);

  const loadCompanies = async () => {
    try {
      setIsLoadingCompanies(true);
      const response = await companyApi.list();
      const companiesList = response?.companies || [];
      setCompanies(companiesList);
      if (companiesList.length > 0) {
        setSelectedCompanyId(companiesList[0].id);
      }
    } catch (error) {
      console.error('Failed to load companies:', error);
      setCompanies([]);
    } finally {
      setIsLoadingCompanies(false);
    }
  };

  const loadRecentDocuments = async (page: number) => {
    try {
      setIsLoadingDocuments(true);
      const response = await documentApi.list({
        company_id: selectedCompanyId || undefined,
        skip: page * pageSize,
        limit: pageSize,
      });
      setRecentDocuments(response.documents);
      setTotalDocuments(response.total);
    } catch (error) {
      console.error('Failed to load documents:', error);
    } finally {
      setIsLoadingDocuments(false);
    }
  };

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.toLowerCase().split('.').pop();
    if (!ALL_ALLOWED_EXTENSIONS.includes(ext)) {
      return `File type not allowed. Allowed: ${ALLOWED_EXTENSIONS.join(', ')}, audio`;
    }
    return null;
  };

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    const items = e.dataTransfer.items;
    const allFiles: File[] = [];

    const processEntry = async (entry: FileSystemEntry): Promise<void> => {
      if (entry.isFile) {
        const fileEntry = entry as FileSystemFileEntry;
        return new Promise((resolve) => {
          fileEntry.file((file) => {
            Object.defineProperty(file, 'webkitRelativePath', {
              value: entry.fullPath.substring(1),
              writable: false,
            });
            allFiles.push(file);
            resolve();
          });
        });
      } else if (entry.isDirectory) {
        const dirEntry = entry as FileSystemDirectoryEntry;
        const reader = dirEntry.createReader();
        return new Promise((resolve) => {
          const readEntries = () => {
            reader.readEntries(async (entries) => {
              if (entries.length === 0) {
                resolve();
              } else {
                await Promise.all(entries.map(processEntry));
                readEntries();
              }
            });
          };
          readEntries();
        });
      }
    };

    const promises: Promise<void>[] = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) {
        promises.push(processEntry(entry));
      }
    }

    await Promise.all(promises);
    addFiles(allFiles);
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFolderSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      addFiles(Array.from(e.target.files));
    }
    if (folderInputRef.current) {
      folderInputRef.current.value = '';
    }
  };

  const addFiles = (newFiles: File[]) => {
    const allowedFiles = newFiles.filter((file) => {
      const ext = '.' + file.name.toLowerCase().split('.').pop();
      return ALL_ALLOWED_EXTENSIONS.includes(ext);
    });

    if (allowedFiles.length === 0) return;

    const processedFiles = processFiles(allowedFiles);

    const validatedFiles = processedFiles.map((fileObj) => {
      const error = validateFile(fileObj.file);
      return {
        ...fileObj,
        status: error ? 'failed' : 'pending',
        error: error || undefined,
      } as SelectedFile;
    });

    setFiles((prev) => [...prev, ...validatedFiles]);
  };

  const removeFile = (id: string) => {
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  const uploadFile = async (fileItem: SelectedFile) => {
    if (!selectedCompanyId) {
      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? { ...f, status: 'failed', error: 'Please select a company first' }
            : f
        )
      );
      return;
    }

    setFiles((prev) =>
      prev.map((f) => (f.id === fileItem.id ? { ...f, status: 'uploading' } : f))
    );

    try {
      const response = await documentApi.upload(fileItem.file, selectedCompanyId);

      // Track document in global context for progress updates across page navigation
      trackDocument(response.document_id, fileItem.file.name);

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id
            ? { ...f, status: 'processing', documentId: response.document_id }
            : f
        )
      );
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error
          ? error.message
          : (error as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Upload failed';

      setFiles((prev) =>
        prev.map((f) =>
          f.id === fileItem.id ? { ...f, status: 'failed', error: errorMessage } : f
        )
      );
    }
  };

  const handleUpload = async () => {
    const pendingFiles = files.filter((f) => f.status === 'pending');
    for (const file of pendingFiles) {
      await uploadFile(file);
    }
  };

  const clearCompleted = () => setFiles((prev) => prev.filter((f) => f.status !== 'completed'));

  const handleOpenDocument = async (doc: Document) => {
    const fileType = doc.file_type;

    // Only support PDF and DOCX preview
    if (fileType !== 'pdf' && fileType !== 'docx') {
      // For unsupported types, download instead
      try {
        const response = await documentApi.getDownloadUrl(doc.id);
        window.open(response.download_url, '_blank');
      } catch (error) {
        console.error('Failed to get download URL:', error);
        toast.error('Failed to open document', 'Could not retrieve the document URL.');
      }
      return;
    }

    try {
      const response = await documentApi.getDownloadUrl(doc.id);
      setPreviewModal({
        isOpen: true,
        documentUrl: response.download_url,
        filename: doc.original_filename,
        fileType: fileType,
      });
    } catch (error) {
      console.error('Failed to get download URL:', error);
      toast.error('Failed to open document', 'Could not retrieve the document URL.');
    }
  };

  const handlePreviewClose = () => {
    setPreviewModal({
      isOpen: false,
      documentUrl: null,
      filename: '',
      fileType: '',
    });
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
      loadRecentDocuments(currentPage);
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

  const getDocumentStatusBadge = (status: DocumentStatus): { text: string; className: string } => {
    switch (status) {
      case 'pending':
        return { text: 'Pending', className: styles.statusPending };
      case 'processing':
        return { text: 'Processing', className: styles.statusProcessing };
      case 'completed':
        return { text: 'Completed', className: styles.statusCompleted };
      case 'failed':
        return { text: 'Failed', className: styles.statusFailed };
      default:
        return { text: 'Unknown', className: styles.statusPending };
    }
  };

  const pendingCount = files.filter((f) => f.status === 'pending').length;
  const processingCount = files.filter(
    (f) => f.status === 'uploading' || f.status === 'processing'
  ).length;

  return (
    <AppLayout title="Upload Documents" subtitle="Upload your business documents for analysis">
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.companySelectorWrapper}>
            <label className={styles.companySelectorLabel}>Select Company *</label>
            {isLoadingCompanies ? (
              <p className={styles.loadingText}>Loading companies...</p>
            ) : companies.length === 0 ? (
              <div className={styles.warningBox}>
                No companies found. <a href="/companies" className={styles.warningLink}>Create a company</a> first.
              </div>
            ) : (
              <select
                value={selectedCompanyId}
                onChange={(e) => {
                  setSelectedCompanyId(e.target.value);
                  setCurrentPage(0);
                }}
                className={styles.companySelect}
              >
                {companies.map((company) => (
                  <option key={company.id} value={company.id}>{company.name}</option>
                ))}
              </select>
            )}
          </div>
        </div>

        <div className={styles.card}>
          <div
            className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ''}`}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
          >
            <div className={styles.dropzoneIcon}>📁</div>
            <h3 className={styles.dropzoneTitle}>Drag and drop files or folders here</h3>
            <p className={styles.dropzoneText}>
              <span className={styles.formatHint}>
                Supported: PDF, DOCX, XLSX, PPTX, Audio (no size limit)
              </span>
            </p>
            <div className={styles.browseButtons}>
              <button type="button" className={styles.browseButton} onClick={() => fileInputRef.current?.click()}>
                Browse Files
              </button>
              <button type="button" className={styles.browseButton} onClick={() => folderInputRef.current?.click()}>
                Browse Folder
              </button>
            </div>
            <input
              ref={fileInputRef}
              type="file"
              multiple
              accept={ALL_ALLOWED_EXTENSIONS.join(',')}
              className={styles.fileInput}
              onChange={handleFileSelect}
            />
            <input
              ref={folderInputRef}
              type="file"
              multiple
              className={styles.fileInput}
              onChange={handleFolderSelect}
              {...({ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
            />
          </div>

          {files.length > 0 && (
            <div className={styles.fileList}>
              <div className={styles.fileListHeader}>
                <h4 className={styles.fileListTitle}>
                  Selected Files ({files.length})
                  {processingCount > 0 && (
                    <span className={styles.processingIndicator}> ({processingCount} processing)</span>
                  )}
                </h4>
                <div className={styles.fileListActions}>
                  {files.some((f) => f.status === 'completed') && (
                    <button type="button" className={styles.linkButton} onClick={clearCompleted}>
                      Clear completed
                    </button>
                  )}
                </div>
              </div>

              {files.map((fileItem) => {
                const statusBadge = getStatusBadge(fileItem.status);
                const isProcessing = fileItem.status === 'processing' || fileItem.status === 'uploading';
                return (
                  <div key={fileItem.id} className={styles.fileItem}>
                    <span className={styles.fileIcon}>{getFileIcon(fileItem.file.name)}</span>
                    <div className={styles.fileInfo}>
                      <p className={styles.fileName}>
                        {fileItem.file.name}
                        {fileItem.relativePath !== fileItem.file.name && (
                          <span className={styles.filePath}> ({fileItem.relativePath})</span>
                        )}
                      </p>
                      <p className={styles.fileSize}>
                        {formatFileSize(fileItem.file.size)}
                        {fileItem.error && <span className={styles.errorText}> — {fileItem.error}</span>}
                      </p>
                      {/* Progress bar for processing files */}
                      {isProcessing && (
                        <div className={styles.progressContainer}>
                          <div className={styles.progressBar}>
                            <div
                              className={styles.progressFill}
                              style={{ width: `${fileItem.progress?.progress || 0}%` }}
                            />
                          </div>
                          {/* Show current step name with progress percentage */}
                          <div className={styles.progressCurrentStep}>
                            <span className={styles.progressStepName}>
                              {fileItem.progress?.stepName || 'Starting...'}
                            </span>
                            <span className={styles.progressPercent}>
                              {fileItem.progress?.progress || 0}%
                            </span>
                          </div>
                          <div className={styles.progressSteps}>
                            {PROCESSING_STEPS.map((step) => {
                              const currentStep = fileItem.progress?.step || 0;
                              const isCompleted = currentStep > step.step;
                              const isActive = currentStep === step.step;
                              return (
                                <span
                                  key={step.step}
                                  className={`${styles.progressStep} ${isCompleted ? styles.progressStepCompleted : ''} ${isActive ? styles.progressStepActive : ''}`}
                                >
                                  {isCompleted ? '✓' : isActive ? '→' : '○'} {step.name}
                                </span>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                    {!isProcessing && (
                      <span className={`${styles.statusBadge} ${statusBadge.className}`}>{statusBadge.text}</span>
                    )}
                    {fileItem.status === 'pending' && (
                      <button
                        className={`${styles.browseButton} ${styles.smallButtonWithMargin}`}
                        onClick={() => uploadFile(fileItem)}
                      >
                        Upload
                      </button>
                    )}
                    {(fileItem.status === 'pending' || fileItem.status === 'failed') && (
                      <button className={styles.removeButton} onClick={() => removeFile(fileItem.id)}>
                        Remove
                      </button>
                    )}
                  </div>
                );
              })}
              {pendingCount > 0 && (
                <button className={styles.uploadButton} onClick={handleUpload} disabled={processingCount > 0}>
                  {processingCount > 0
                    ? `Processing ${processingCount} file(s)...`
                    : `Upload ${pendingCount} ${pendingCount === 1 ? 'File' : 'Files'}`}
                </button>
              )}
            </div>
          )}

          {files.length === 0 && (
            <div className={styles.emptyState}>
              <p>No files selected yet</p>
            </div>
          )}
        </div>

        <div className={styles.card}>
          <h4 className={styles.fileListTitle}>
            Recent Documents {totalDocuments > 0 && `(${totalDocuments})`}
          </h4>
          {isLoadingDocuments ? (
            <div className={styles.emptyState}><p>Loading documents...</p></div>
          ) : recentDocuments.length === 0 ? (
            <div className={styles.emptyState}><p>No documents uploaded yet</p></div>
          ) : (
            <div>
              {recentDocuments.map((doc) => {
                const statusBadge = getDocumentStatusBadge(doc.status);
                return (
                  <div key={doc.id} className={styles.fileItem}>
                    <span className={styles.fileIcon}>{getFileIcon(doc.original_filename)}</span>
                    <div className={styles.fileInfo}>
                      <p
                        className={styles.fileNameClickable}
                        onClick={() => handleOpenDocument(doc)}
                        title="Click to open document"
                      >
                        {doc.original_filename}
                      </p>
                      <p className={styles.fileSize}>
                        {formatFileSize(doc.file_size)} • {new Date(doc.created_at).toLocaleDateString()}
                        {doc.total_pages && ` • ${doc.total_pages} pages`}
                      </p>
                    </div>
                    <span className={`${styles.statusBadge} ${statusBadge.className}`}>{statusBadge.text}</span>
                    <div className={styles.documentActions}>
                      {doc.status === 'completed' && (
                        <a href={`/documents/${doc.id}`} className={styles.viewLink}>View Chunks</a>
                      )}
                      <button
                        className={styles.deleteButton}
                        onClick={() => handleDeleteClick(doc)}
                        title="Delete document"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                );
              })}
              {totalDocuments > pageSize && (
                <div className={styles.paginationContainer}>
                  <span className={styles.paginationInfo}>
                    Showing {currentPage * pageSize + 1}-{Math.min((currentPage + 1) * pageSize, totalDocuments)} of {totalDocuments}
                  </span>
                  <div className={styles.paginationButtons}>
                    <button
                      className={`${styles.browseButton} ${styles.smallButton}`}
                      onClick={() => setCurrentPage((p) => Math.max(0, p - 1))}
                      disabled={currentPage === 0}
                    >
                      Previous
                    </button>
                    <button
                      className={`${styles.browseButton} ${styles.smallButton}`}
                      onClick={() => setCurrentPage((p) => p + 1)}
                      disabled={(currentPage + 1) * pageSize >= totalDocuments}
                    >
                      Next
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
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

      <DocumentPreviewModal
        isOpen={previewModal.isOpen}
        onClose={handlePreviewClose}
        documentUrl={previewModal.documentUrl}
        filename={previewModal.filename}
        fileType={previewModal.fileType}
      />
    </AppLayout>
  );
}
