import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import Loader from '../components/common/Loader';
import AlertModal from '../components/common/AlertModal';
import styles from '../styles/Login.module.css';

const ERROR_MESSAGES: Record<string, { title: string; message: string }> = {
  company_not_onboarded: {
    title: 'Company Not Onboarded',
    message: 'Your company has not been onboarded yet. Please contact BCP to request access to the platform.',
  },
  tenant_inactive: {
    title: 'Company Inactive',
    message: 'Your company account is currently inactive. Please contact BCP for assistance.',
  },
  provisioning_failed: {
    title: 'Login Failed',
    message: 'Unable to provision your account. Please try again or contact support.',
  },
};

export default function Login() {
  const { login, loading } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [showModal, setShowModal] = useState(false);
  const [errorInfo, setErrorInfo] = useState<{ title: string; message: string } | null>(null);

  useEffect(() => {
    const error = searchParams.get('error');
    if (error && ERROR_MESSAGES[error]) {
      setErrorInfo(ERROR_MESSAGES[error]);
      setShowModal(true);
      // Clear the error from URL
      searchParams.delete('error');
      setSearchParams(searchParams, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  const handleCloseModal = () => {
    setShowModal(false);
    setErrorInfo(null);
  };

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Welcome to BDE</h1>
        <p className={styles.subtitle}>Sign in with your Microsoft account to continue</p>
        <button
          onClick={login}
          disabled={loading}
          className={styles.button}
        >
          {loading ? <Loader size="small" color="#fff" /> : 'Sign in with Microsoft'}
        </button>
      </div>

      <AlertModal
        isOpen={showModal}
        type="warning"
        title={errorInfo?.title || ''}
        message={errorInfo?.message || ''}
        buttonText="OK"
        onClose={handleCloseModal}
      />
    </div>
  );
}
