import styles from '../../styles/components/common/ConfirmModal.module.css';

type ConfirmType = 'danger' | 'warning' | 'info';

interface ConfirmModalProps {
  isOpen: boolean;
  type?: ConfirmType;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  isLoading?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

const ICONS: Record<ConfirmType, string> = {
  danger: '\u2717',
  warning: '\u26A0',
  info: '?',
};

const ICON_CLASSES: Record<ConfirmType, string> = {
  danger: styles.iconDanger,
  warning: styles.iconWarning,
  info: styles.iconInfo,
};

export default function ConfirmModal({
  isOpen,
  type = 'danger',
  title,
  message,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isLoading = false,
  onConfirm,
  onCancel,
}: ConfirmModalProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onCancel}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={`${styles.icon} ${ICON_CLASSES[type]}`}>
          {ICONS[type]}
        </div>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.message}>{message}</p>
        <div className={styles.buttons}>
          <button
            className={`${styles.button} ${styles.cancelButton}`}
            onClick={onCancel}
            disabled={isLoading}
          >
            {cancelText}
          </button>
          <button
            className={`${styles.button} ${styles.confirmButton} ${styles[type]}`}
            onClick={onConfirm}
            disabled={isLoading}
          >
            {isLoading ? 'Deleting...' : confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}
