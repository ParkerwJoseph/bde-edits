import { useState, useEffect } from 'react';
import { Document, Page, pdfjs } from 'react-pdf';
import mammoth from 'mammoth';
import styles from '../../styles/components/common/DocumentPreviewModal.module.css';
import 'react-pdf/dist/Page/AnnotationLayer.css';
import 'react-pdf/dist/Page/TextLayer.css';

// Set up PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = `//unpkg.com/pdfjs-dist@${pdfjs.version}/build/pdf.worker.min.mjs`;

interface DocumentPreviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentUrl: string | null;
  filename: string;
  fileType: 'pdf' | 'docx' | string;
}

export default function DocumentPreviewModal({
  isOpen,
  onClose,
  documentUrl,
  filename,
  fileType,
}: DocumentPreviewModalProps) {
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [docxHtml, setDocxHtml] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!isOpen || !documentUrl) return;

    setIsLoading(true);
    setError(null);
    setCurrentPage(1);
    setDocxHtml('');

    if (fileType === 'docx') {
      loadDocx(documentUrl);
    } else {
      setIsLoading(false);
    }
  }, [isOpen, documentUrl, fileType]);

  const loadDocx = async (url: string) => {
    try {
      const response = await fetch(url);
      if (!response.ok) throw new Error('Failed to fetch document');

      const arrayBuffer = await response.arrayBuffer();
      const result = await mammoth.convertToHtml({ arrayBuffer });
      setDocxHtml(result.value);
      setIsLoading(false);
    } catch (err) {
      console.error('Error loading DOCX:', err);
      setError('Failed to load document. Please try downloading instead.');
      setIsLoading(false);
    }
  };

  const onDocumentLoadSuccess = ({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setIsLoading(false);
  };

  const onDocumentLoadError = (err: Error) => {
    console.error('Error loading PDF:', err);
    setError('Failed to load PDF. Please try downloading instead.');
    setIsLoading(false);
  };

  const handlePrevPage = () => {
    setCurrentPage((prev) => Math.max(1, prev - 1));
  };

  const handleNextPage = () => {
    setCurrentPage((prev) => Math.min(numPages, prev + 1));
  };

  const handleZoomIn = () => {
    setScale((prev) => Math.min(2.0, prev + 0.2));
  };

  const handleZoomOut = () => {
    setScale((prev) => Math.max(0.5, prev - 0.2));
  };

  const handleDownload = () => {
    if (documentUrl) {
      window.open(documentUrl, '_blank');
    }
  };

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>{filename}</h2>
          <div className={styles.headerActions}>
            <button
              className={styles.downloadButton}
              onClick={handleDownload}
              title="Download"
            >
              ⬇ Download
            </button>
            <button className={styles.closeButton} onClick={onClose}>
              ✕
            </button>
          </div>
        </div>

        {fileType === 'pdf' && !error && (
          <div className={styles.toolbar}>
            <div className={styles.pageControls}>
              <button
                className={styles.toolbarButton}
                onClick={handlePrevPage}
                disabled={currentPage <= 1}
              >
                ◀ Prev
              </button>
              <span className={styles.pageInfo}>
                Page {currentPage} of {numPages}
              </span>
              <button
                className={styles.toolbarButton}
                onClick={handleNextPage}
                disabled={currentPage >= numPages}
              >
                Next ▶
              </button>
            </div>
            <div className={styles.zoomControls}>
              <button
                className={styles.toolbarButton}
                onClick={handleZoomOut}
                disabled={scale <= 0.5}
              >
                −
              </button>
              <span className={styles.zoomInfo}>{Math.round(scale * 100)}%</span>
              <button
                className={styles.toolbarButton}
                onClick={handleZoomIn}
                disabled={scale >= 2.0}
              >
                +
              </button>
            </div>
          </div>
        )}

        <div className={styles.content}>
          {isLoading && (
            <div className={styles.loading}>
              <div className={styles.spinner}></div>
              <p>Loading document...</p>
            </div>
          )}

          {error && (
            <div className={styles.error}>
              <p>{error}</p>
              <button className={styles.downloadButton} onClick={handleDownload}>
                Download File
              </button>
            </div>
          )}

          {!isLoading && !error && fileType === 'pdf' && documentUrl && (
            <div className={styles.pdfContainer}>
              <Document
                file={documentUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                loading={
                  <div className={styles.loading}>
                    <div className={styles.spinner}></div>
                    <p>Loading PDF...</p>
                  </div>
                }
              >
                <Page
                  pageNumber={currentPage}
                  scale={scale}
                  renderTextLayer={true}
                  renderAnnotationLayer={true}
                />
              </Document>
            </div>
          )}

          {!isLoading && !error && fileType === 'docx' && docxHtml && (
            <div
              className={styles.docxContainer}
              dangerouslySetInnerHTML={{ __html: docxHtml }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
