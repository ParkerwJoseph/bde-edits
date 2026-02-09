import { useState, useEffect } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import ConfirmModal from '../components/common/ConfirmModal';
import { companyApi, type Company } from '../api/companyApi';
import styles from '../styles/Companies.module.css';

export default function Companies() {
  const [companies, setCompanies] = useState<Company[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [formName, setFormName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  // Delete modal state
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [companyToDelete, setCompanyToDelete] = useState<Company | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadCompanies();
  }, []);

  const loadCompanies = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await companyApi.list();
      setCompanies(response?.companies || []);
    } catch (err) {
      console.error('Failed to load companies:', err);
      setError('Failed to load companies');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) return;

    try {
      setSubmitting(true);
      setError(null);

      if (editingId) {
        await companyApi.update(editingId, { name: formName.trim() });
      } else {
        await companyApi.create({ name: formName.trim() });
      }

      setFormName('');
      setShowForm(false);
      setEditingId(null);
      await loadCompanies();
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Failed to save company';
      setError(errorMessage);
    } finally {
      setSubmitting(false);
    }
  };

  const handleEdit = (company: Company) => {
    setFormName(company.name);
    setEditingId(company.id);
    setShowForm(true);
  };

  const handleDelete = (company: Company) => {
    setCompanyToDelete(company);
    setDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!companyToDelete) return;

    try {
      setDeleting(true);
      setError(null);
      await companyApi.delete(companyToDelete.id);
      setDeleteModalOpen(false);
      setCompanyToDelete(null);
      await loadCompanies();
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error
          ? err.message
          : (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            'Failed to delete company';
      setError(errorMessage);
    } finally {
      setDeleting(false);
    }
  };

  const cancelDelete = () => {
    setDeleteModalOpen(false);
    setCompanyToDelete(null);
  };

  const handleCancel = () => {
    setFormName('');
    setShowForm(false);
    setEditingId(null);
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString();
  };

  return (
    <AppLayout title="Companies" subtitle="Manage companies for document organization">
      <div className={styles.container}>
        <div className={styles.card}>
          <div className={styles.header}>
            <h3 className={styles.title}>
              Companies {companies.length > 0 && `(${companies.length})`}
            </h3>
            {!showForm && (
              <button className={styles.addButton} onClick={() => setShowForm(true)}>
                + Add Company
              </button>
            )}
          </div>

          {error && <div className={styles.error}>{error}</div>}

          {showForm && (
            <form className={styles.form} onSubmit={handleSubmit}>
              <input
                type="text"
                className={styles.input}
                placeholder="Company name"
                value={formName}
                onChange={(e) => setFormName(e.target.value)}
                autoFocus
              />
              <button type="submit" className={styles.submitButton} disabled={submitting || !formName.trim()}>
                {submitting ? 'Saving...' : editingId ? 'Update' : 'Create'}
              </button>
              <button type="button" className={styles.cancelButton} onClick={handleCancel}>
                Cancel
              </button>
            </form>
          )}

          {loading ? (
            <div className={styles.loading}>Loading companies...</div>
          ) : companies.length === 0 ? (
            <div className={styles.emptyState}>
              <div className={styles.emptyIcon}>🏢</div>
              <p className={styles.emptyText}>No companies yet</p>
              <p className={styles.emptyHint}>Create a company to start organizing your documents</p>
            </div>
          ) : (
            <div className={styles.companyList}>
              {companies.map((company) => (
                <div key={company.id} className={styles.companyItem}>
                  <span className={styles.companyIcon}>🏢</span>
                  <div className={styles.companyInfo}>
                    <p className={styles.companyName}>{company.name}</p>
                    <p className={styles.companyMeta}>Created {formatDate(company.created_at)}</p>
                  </div>
                  <div className={styles.actions}>
                    <button className={styles.editButton} onClick={() => handleEdit(company)}>
                      Edit
                    </button>
                    <button className={styles.deleteButton} onClick={() => handleDelete(company)}>
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      <ConfirmModal
        isOpen={deleteModalOpen}
        type="danger"
        title="Delete Company"
        message={`Are you sure you want to delete "${companyToDelete?.name}"? This will permanently delete all associated documents, chat sessions, connectors, and scores.`}
        confirmText="Delete"
        cancelText="Cancel"
        isLoading={deleting}
        onConfirm={confirmDelete}
        onCancel={cancelDelete}
      />
    </AppLayout>
  );
}
