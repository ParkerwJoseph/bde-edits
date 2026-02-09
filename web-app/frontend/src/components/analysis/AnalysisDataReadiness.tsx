/**
 * AnalysisDataReadiness Component
 *
 * Displays the readiness of data sources for analysis including
 * documents and connectors.
 */

import { FileText, Link2 } from 'lucide-react';
import type { AnalysisStatusResponse } from '../../api/scoringApi';
import styles from '../../styles/components/analysis/AnalysisDataReadiness.module.css';

export interface AnalysisDataReadinessProps {
  status: AnalysisStatusResponse | null;
  isLoading: boolean;
}

interface DataSourceItem {
  id: string;
  label: string;
  description: string;
  icon: React.ReactNode;
  count: number;
  hasNew: boolean;
}

export function AnalysisDataReadiness({ status, isLoading }: AnalysisDataReadinessProps) {
  if (isLoading) {
    return (
      <div className={styles.container}>
        <div className={styles.loading}>Loading data sources...</div>
      </div>
    );
  }

  const dataSources: DataSourceItem[] = [
    {
      id: 'documents',
      label: 'Documents',
      description: 'PDFs, spreadsheets, and other files',
      icon: <FileText size={20} />,
      count: status?.document_count || 0,
      hasNew: status?.has_new_documents || false,
    },
    {
      id: 'connectors',
      label: 'Connectors',
      description: 'QuickBooks and other integrations',
      icon: <Link2 size={20} />,
      count: status?.connector_count || 0,
      hasNew: status?.has_new_connector_data || false,
    },
  ];

  const getStatusInfo = (item: DataSourceItem) => {
    if (item.count === 0) {
      return {
        status: 'empty',
        badge: 'No Data',
        iconClass: styles.iconWrapperEmpty,
        badgeClass: styles.statusEmpty,
      };
    }
    if (item.hasNew) {
      return {
        status: 'pending',
        badge: 'New Data',
        iconClass: styles.iconWrapperPending,
        badgeClass: styles.statusPending,
      };
    }
    return {
      status: 'ready',
      badge: 'Ready',
      iconClass: styles.iconWrapperReady,
      badgeClass: styles.statusReady,
    };
  };

  return (
    <div className={styles.container}>
      <div className={styles.header}>
        <h2 className={styles.title}>Data Readiness</h2>
        <p className={styles.subtitle}>Sources available for analysis</p>
      </div>

      <div className={styles.grid}>
        {dataSources.map((item) => {
          const statusInfo = getStatusInfo(item);
          return (
            <div key={item.id} className={styles.item}>
              <div className={`${styles.iconWrapper} ${statusInfo.iconClass}`}>
                {item.icon}
              </div>
              <div className={styles.info}>
                <div className={styles.label}>{item.label}</div>
                <div className={styles.description}>{item.description}</div>
              </div>
              <span className={styles.count}>{item.count}</span>
              <span className={`${styles.statusBadge} ${statusInfo.badgeClass}`}>
                {statusInfo.badge}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default AnalysisDataReadiness;
