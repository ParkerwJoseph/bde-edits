import { useState, useEffect } from 'react';
import { useParams, useSearchParams, Link } from 'react-router-dom';
import { tenantApi, type OnboardingValidation } from '../api/tenantApi';
import { getApiBaseUrl } from '../utils/api';
import Loader from '../components/common/Loader';
import styles from '../styles/Login.module.css';

export default function Onboarding() {
  const { code } = useParams<{ code: string }>();
  const [searchParams] = useSearchParams();
  const [validation, setValidation] = useState<OnboardingValidation | null>(null);
  const [loading, setLoading] = useState(true);

  const errorParam = searchParams.get('error');
  const successParam = searchParams.get('success');

  useEffect(() => {
    if (code && !errorParam && !successParam) {
      validateCode();
    } else {
      setLoading(false);
    }
  }, [code, errorParam, successParam]);

  const validateCode = async () => {
    try {
      setLoading(true);
      const result = await tenantApi.validateOnboardingCode(code!);
      setValidation(result);
    } catch (err) {
      setValidation({ valid: false, tenant_id: null, company_name: null, error: 'Failed to validate code' });
    } finally {
      setLoading(false);
    }
  };

  const startOnboarding = () => {
    window.location.href = `${getApiBaseUrl()}/api/onboarding/start/${code}`;
  };

  if (loading) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <Loader size="large" text="Please wait while we validate your onboarding link." />
        </div>
      </div>
    );
  }

  if (successParam === 'true') {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Onboarding Complete!</h1>
          <p className={styles.subtitle}>
            Your organization has been successfully connected to BDE.
            Users from your organization can now sign in.
          </p>
          <Link to="/login" className={styles.button}>
            Sign In
          </Link>
        </div>
      </div>
    );
  }

  if (errorParam) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Onboarding Failed</h1>
          <p className={styles.subtitle} style={{ color: '#e94560' }}>
            {decodeURIComponent(errorParam)}
          </p>
          <p className={styles.subtitle}>
            Please contact the BDE administrator for assistance.
          </p>
        </div>
      </div>
    );
  }

  if (!validation?.valid) {
    return (
      <div className={styles.container}>
        <div className={styles.card}>
          <h1 className={styles.title}>Invalid Link</h1>
          <p className={styles.subtitle} style={{ color: '#e94560' }}>
            {validation?.error || 'This onboarding link is invalid or has expired.'}
          </p>
          <p className={styles.subtitle}>
            Please contact the BDE administrator for a new onboarding link.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <h1 className={styles.title}>Welcome to BDE</h1>
        <p className={styles.subtitle}>
          Connect <strong>{validation.company_name}</strong> to the BDE platform.
        </p>
        <p className={styles.subtitle} style={{ fontSize: '0.9rem', marginTop: '1rem' }}>
          As an IT administrator, you will grant BDE access to authenticate users from your Azure AD.
          This requires admin consent for your organization.
        </p>
        <button onClick={startOnboarding} className={styles.button}>
          Connect with Microsoft Azure AD
        </button>
        <p className={styles.subtitle} style={{ fontSize: '0.8rem', marginTop: '1rem', opacity: 0.7 }}>
          You must be a Global Administrator or Application Administrator in your Azure AD to complete this process.
        </p>
      </div>
    </div>
  );
}
