import { Link } from 'react-router-dom';
import { AppLayout } from '../components/layout/AppLayout';
import styles from '../styles/Common.module.css';

export default function Forbidden() {
  return (
    <AppLayout title="Access Denied" subtitle="You don't have permission to view this page">
      <div className={styles.card}>
        <div className={styles.errorContainer}>
          <div className={styles.errorCode}>403</div>
          <h2 className={styles.errorTitle}>Access Denied</h2>
          <p className={styles.errorMessage}>
            You don't have the required permissions to access this page.
            Please contact your administrator if you believe this is an error.
          </p>
          <Link to="/" className={styles.primaryButton}>
            Return to Dashboard
          </Link>
        </div>
      </div>
    </AppLayout>
  );
}
