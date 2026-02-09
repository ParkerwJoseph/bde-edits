import { useState, useEffect } from 'react';
import { tenantApi, type Tenant, type OnboardingPackage } from '../api/tenantApi';
import { PermissionGate } from '../components/common/PermissionGate';
import { Permissions } from '../constants/permissions';
import { AppLayout } from '../components/layout/AppLayout';
import Loader from '../components/common/Loader';
import styles from '../styles/Common.module.css';

export default function Tenants() {
  const [tenants, setTenants] = useState<Tenant[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState('');
  const [creating, setCreating] = useState(false);
  const [onboardingPackage, setOnboardingPackage] = useState<OnboardingPackage | null>(null);

  useEffect(() => {
    loadTenants();
  }, []);

  const loadTenants = async () => {
    try {
      setLoading(true);
      const response = await tenantApi.list();
      setTenants(response.tenants || []);
    } catch (err) {
      console.error('Failed to load tenants:', err);
      setError('Failed to load tenants');
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newCompanyName.trim()) return;
    try {
      setCreating(true);
      await tenantApi.create(newCompanyName);
      setShowCreateModal(false);
      setNewCompanyName('');
      loadTenants();
    } catch (err) {
      setError('Failed to create tenant');
    } finally {
      setCreating(false);
    }
  };

  const handleGenerateOnboarding = async (tenantId: string) => {
    try {
      const pkg = await tenantApi.generateOnboarding(tenantId);
      setOnboardingPackage(pkg);
    } catch (err) {
      setError('Failed to generate onboarding link');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  const getStatusBadgeClass = (status: string) => {
    switch (status) {
      case 'active': return styles.statusActive;
      case 'pending': return styles.statusPending;
      case 'suspended': return styles.statusSuspended;
      default: return '';
    }
  };

  return (
    <AppLayout title="Tenants" subtitle="Manage tenant organizations">
      {error && <div className={styles.error}>{error}</div>}

      <div className={styles.card}>
        <div className={styles.cardHeader}>
          <h2 className={styles.cardTitle}>All Tenants</h2>
          <PermissionGate permission={Permissions.TENANTS_CREATE}>
            <button onClick={() => setShowCreateModal(true)} className={styles.primaryButton}>
              + New Tenant
            </button>
          </PermissionGate>
        </div>

        {loading ? (
          <Loader size="medium" text="Loading tenants..." />
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Company Name</th>
                <th>Status</th>
                <th>Azure Tenant ID</th>
                <th>Type</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {tenants.map((tenant) => (
                <tr key={tenant.id}>
                  <td>{tenant.company_name}</td>
                  <td>
                    <span className={`${styles.statusBadge} ${getStatusBadgeClass(tenant.status)}`}>
                      {tenant.status}
                    </span>
                  </td>
                  <td>{tenant.azure_tenant_id || '-'}</td>
                  <td>
                    {tenant.is_platform_tenant ? (
                      <span className={styles.platformBadge}>Platform</span>
                    ) : (
                      <span className={styles.standardBadge}>External</span>
                    )}
                  </td>
                  <td>
                    {tenant.status === 'pending' && !tenant.is_platform_tenant && (
                      <PermissionGate permission={Permissions.TENANTS_ONBOARD}>
                        <button
                          onClick={() => handleGenerateOnboarding(tenant.id)}
                          className={styles.secondaryButton}
                        >
                          Generate Onboarding
                        </button>
                      </PermissionGate>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Create New Tenant</h3>
            <input
              type="text"
              placeholder="Company Name"
              value={newCompanyName}
              onChange={(e) => setNewCompanyName(e.target.value)}
              className={styles.input}
            />
            <div className={styles.modalActions}>
              <button onClick={() => setShowCreateModal(false)} className={styles.secondaryButton}>
                Cancel
              </button>
              <button onClick={handleCreate} disabled={creating} className={styles.primaryButton}>
                {creating ? <Loader size="small" color="#fff" /> : 'Create'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Onboarding Modal */}
      {onboardingPackage && (
        <div className={styles.modal}>
          <div className={styles.modalContent}>
            <h3>Onboarding Package</h3>
            <p><strong>Company:</strong> {onboardingPackage.company_name}</p>
            <div className={styles.onboardingInfo}>
              <label>Onboarding URL:</label>
              <div className={styles.copyField}>
                <input type="text" value={onboardingPackage.onboarding_url} readOnly className={styles.input} />
                <button onClick={() => copyToClipboard(onboardingPackage.onboarding_url)} className={styles.copyButton}>
                  Copy
                </button>
              </div>
            </div>
            <p><strong>Expires:</strong> {new Date(onboardingPackage.expires_at).toLocaleString()}</p>
            <div className={styles.modalActions}>
              <button onClick={() => setOnboardingPackage(null)} className={styles.primaryButton}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </AppLayout>
  );
}
