/**
 * DocumentCoverage Component
 *
 * Displays a grid of document type cards with counts.
 * Based on reference UI design.
 */

import { useState, useEffect } from 'react';
import { FileText, Table2, Mail, FileAudio, Database, type LucideIcon } from 'lucide-react';
import { documentApi } from '../../api/documentApi';
import styles from '../../styles/components/ingestion/DocumentCoverage.module.css';

interface DocumentTypeConfig {
  icon: LucideIcon;
  label: string;
  description: string;
  fileTypes: string[];  // Maps to our file_type values
}

const DOCUMENT_TYPES: DocumentTypeConfig[] = [
  {
    icon: FileText,
    label: 'PDF Documents',
    description: 'Board decks, reports, financials',
    fileTypes: ['pdf', 'docx', 'pptx'],
  },
  {
    icon: Table2,
    label: 'Spreadsheets',
    description: 'Financial models, data exports',
    fileTypes: ['xlsx'],
  },
  {
    icon: Mail,
    label: 'Emails',
    description: 'Communication archives',
    fileTypes: [],  // Not supported yet
  },
  {
    icon: FileAudio,
    label: 'Transcripts',
    description: 'Meeting notes, call transcripts',
    fileTypes: ['audio'],
  },
  {
    icon: Database,
    label: 'CRM Exports',
    description: 'Pipeline and customer data',
    fileTypes: [],  // From connectors, not documents
  },
];

export interface DocumentCoverageProps {
  companyId: string | null;
  refreshTrigger?: number;
}

export function DocumentCoverage({ companyId, refreshTrigger }: DocumentCoverageProps) {
  const [counts, setCounts] = useState<Record<string, number>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadCounts = async () => {
      if (!companyId) {
        setCounts({});
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        const response = await documentApi.list({
          company_id: companyId || undefined,
          limit: 100,  // Backend max is 100
        });

        // Count by file type
        const typeCounts: Record<string, number> = {};
        response.documents.forEach((doc) => {
          const fileType = doc.file_type;
          typeCounts[fileType] = (typeCounts[fileType] || 0) + 1;
        });

        setCounts(typeCounts);
      } catch (error) {
        console.error('Failed to load document counts:', error);
      } finally {
        setIsLoading(false);
      }
    };

    loadCounts();
  }, [companyId, refreshTrigger]);

  const getCountForType = (config: DocumentTypeConfig): number => {
    return config.fileTypes.reduce((sum, type) => sum + (counts[type] || 0), 0);
  };

  return (
    <div className={styles.container}>
      <h2 className={styles.title}>Document Coverage</h2>
      <div className={styles.grid}>
        {DOCUMENT_TYPES.map((type) => {
          const Icon = type.icon;
          const count = getCountForType(type);

          return (
            <div key={type.label} className={styles.card}>
              <div className={styles.cardHeader}>
                <div className={styles.iconWrapper}>
                  <Icon className={styles.icon} size={20} />
                </div>
                <span className={styles.count}>{isLoading ? '-' : count}</span>
              </div>
              <h4 className={styles.label}>{type.label}</h4>
              <p className={styles.description}>{type.description}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default DocumentCoverage;
