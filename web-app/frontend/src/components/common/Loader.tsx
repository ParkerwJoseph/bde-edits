import styles from '../../styles/components/common/Loader.module.css';

export type LoaderSize = 'small' | 'medium' | 'large';

export interface LoaderProps {
  size?: LoaderSize;
  fullScreen?: boolean;
  color?: string;
  text?: string;
  className?: string;
}

export default function Loader({
  size = 'medium',
  fullScreen = false,
  color,
  text,
  className = '',
}: LoaderProps) {
  const spinnerStyle = color ? { borderTopColor: color } : undefined;

  const containerClasses = [
    styles.container,
    fullScreen ? styles.fullScreen : styles.inline,
    className,
  ]
    .filter(Boolean)
    .join(' ');

  const spinnerClasses = [styles.spinner, styles[size]].join(' ');

  return (
    <div className={containerClasses}>
      <div className={styles.content}>
        <div className={spinnerClasses} style={spinnerStyle} />
        {text && <span className={styles.text}>{text}</span>}
      </div>
    </div>
  );
}
