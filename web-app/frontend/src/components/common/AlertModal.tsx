import styles from '../../styles/components/common/AlertModal.module.css';

type AlertType = 'warning' | 'error' | 'success' | 'info';

interface AlertModalProps {
  isOpen: boolean;
  type?: AlertType;
  title: string;
  message: string;
  buttonText?: string;
  onClose: () => void;
}

const ICONS: Record<AlertType, string> = {
  warning: '⚠️',
  error: '❌',
  success: '✓',
  info: 'ℹ️',
};

const ICON_CLASSES: Record<AlertType, string> = {
  warning: styles.iconWarning,
  error: styles.iconError,
  success: styles.iconSuccess,
  info: styles.iconInfo,
};

export default function AlertModal({
  isOpen,
  type = 'warning',
  title,
  message,
  buttonText = 'OK',
  onClose,
}: AlertModalProps) {
  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={`${styles.icon} ${ICON_CLASSES[type]}`}>
          {ICONS[type]}
        </div>
        <h2 className={styles.title}>{title}</h2>
        <p className={styles.message}>{message}</p>
        <button className={styles.button} onClick={onClose}>
          {buttonText}
        </button>
      </div>
    </div>
  );
}
