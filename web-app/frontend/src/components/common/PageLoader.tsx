/**
 * PageLoader Component
 *
 * Full-page loading state with spinner and optional message.
 * Used for initial page loads when fetching data.
 */

import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import styles from '../../styles/components/common/PageLoader.module.css';

export interface PageLoaderProps {
  /** Loading message to display */
  message?: string;
  /** Whether to show the loader inline (not full page) */
  inline?: boolean;
  /** Additional class name */
  className?: string;
  /** Size of the spinner */
  size?: 'sm' | 'md' | 'lg';
}

export function PageLoader({
  message = 'Loading...',
  inline = false,
  className,
  size = 'md',
}: PageLoaderProps) {
  const sizeMap = {
    sm: 24,
    md: 32,
    lg: 48,
  };

  return (
    <div
      className={cn(
        styles.container,
        inline ? styles.inline : styles.fullPage,
        className
      )}
    >
      <div className={styles.content}>
        <Loader2
          size={sizeMap[size]}
          className={styles.spinner}
        />
        {message && <p className={styles.message}>{message}</p>}
      </div>
    </div>
  );
}

export default PageLoader;
