import { useState, useEffect } from 'react';
import { AppLayout } from '../components/layout/AppLayout';
import { promptApi, type PromptTemplate } from '../api/promptApi';
import { usePermission } from '../hooks/usePermission';
import { Permissions } from '../constants/permissions';
import styles from '../styles/PromptManagement.module.css';

export default function PromptManagement() {
  const [prompt, setPrompt] = useState<PromptTemplate | null>(null);
  const [defaultPrompt, setDefaultPrompt] = useState<string>('');
  const [editedTemplate, setEditedTemplate] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [hasChanges, setHasChanges] = useState(false);
  const [showDefault, setShowDefault] = useState(false);

  const { hasPermission } = usePermission();
  const canEdit = hasPermission(Permissions.SETTINGS_UPDATE);

  useEffect(() => {
    loadPrompt();
  }, []);

  useEffect(() => {
    if (prompt) {
      setHasChanges(editedTemplate !== prompt.template);
    }
  }, [editedTemplate, prompt]);

  const loadPrompt = async () => {
    try {
      setLoading(true);
      setError(null);
      const [promptData, defaultData] = await Promise.all([
        promptApi.get(),
        promptApi.getDefault(),
      ]);
      setPrompt(promptData);
      setEditedTemplate(promptData.template);
      setDefaultPrompt(defaultData.template);
    } catch (err) {
      setError('Failed to load prompt template');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!hasChanges) return;

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const updated = await promptApi.update({ template: editedTemplate });
      setPrompt(updated);
      setSuccess('Prompt template saved successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to save prompt template');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleReset = async () => {
    if (!confirm('Are you sure you want to reset the prompt to default? This cannot be undone.')) {
      return;
    }

    try {
      setSaving(true);
      setError(null);
      setSuccess(null);
      const updated = await promptApi.reset();
      setPrompt(updated);
      setEditedTemplate(updated.template);
      setSuccess('Prompt reset to default successfully');
      setTimeout(() => setSuccess(null), 3000);
    } catch (err) {
      setError('Failed to reset prompt template');
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  const handleDiscard = () => {
    if (prompt) {
      setEditedTemplate(prompt.template);
    }
  };

  if (loading) {
    return (
      <AppLayout title="Prompt Management" subtitle="Configure the RAG system prompt">
        <div className={styles.loading}>Loading...</div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Prompt Management" subtitle="Configure the RAG system prompt">
      <div className={styles.container}>
        {error && <div className={styles.error}>{error}</div>}
        {success && <div className={styles.success}>{success}</div>}

        <div className={styles.card}>
          <div className={styles.cardHeader}>
            <div>
              <h2 className={styles.cardTitle}>RAG System Prompt</h2>
              <p className={styles.cardDescription}>
                This prompt is used when the AI generates answers based on retrieved document chunks.
              </p>
            </div>
            {prompt && (
              <div className={styles.meta}>
                <span className={styles.version}>Version {prompt.version}</span>
                {prompt.updated_by && (
                  <span className={styles.updatedBy}>
                    Last updated by {prompt.updated_by}
                  </span>
                )}
              </div>
            )}
          </div>

          <div className={styles.editorContainer}>
            <textarea
              className={styles.editor}
              value={editedTemplate}
              onChange={(e) => setEditedTemplate(e.target.value)}
              disabled={!canEdit || saving}
              placeholder="Enter the system prompt..."
              spellCheck={false}
            />
          </div>

          <div className={styles.actions}>
            <div className={styles.leftActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => setShowDefault(!showDefault)}
              >
                {showDefault ? 'Hide Default' : 'Show Default'}
              </button>
              {canEdit && (
                <button
                  type="button"
                  className={styles.dangerButton}
                  onClick={handleReset}
                  disabled={saving}
                >
                  Reset to Default
                </button>
              )}
            </div>

            {canEdit && (
              <div className={styles.rightActions}>
                <button
                  type="button"
                  className={styles.secondaryButton}
                  onClick={handleDiscard}
                  disabled={!hasChanges || saving}
                >
                  Discard Changes
                </button>
                <button
                  type="button"
                  className={styles.primaryButton}
                  onClick={handleSave}
                  disabled={!hasChanges || saving}
                >
                  {saving ? 'Saving...' : 'Save Changes'}
                </button>
              </div>
            )}
          </div>
        </div>

        {showDefault && (
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>Default Prompt (Reference)</h2>
            <pre className={styles.defaultPrompt}>{defaultPrompt}</pre>
          </div>
        )}

        {prompt && (
          <div className={styles.card}>
            <h2 className={styles.cardTitle}>Prompt Information</h2>
            <div className={styles.infoGrid}>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Name</span>
                <span className={styles.infoValue}>{prompt.name}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Description</span>
                <span className={styles.infoValue}>{prompt.description || 'N/A'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Version</span>
                <span className={styles.infoValue}>{prompt.version}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Last Updated</span>
                <span className={styles.infoValue}>
                  {new Date(prompt.updated_at).toLocaleString()}
                </span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Updated By</span>
                <span className={styles.infoValue}>{prompt.updated_by || 'System'}</span>
              </div>
              <div className={styles.infoItem}>
                <span className={styles.infoLabel}>Status</span>
                <span className={`${styles.infoValue} ${styles.statusBadge}`}>
                  {prompt.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </AppLayout>
  );
}
