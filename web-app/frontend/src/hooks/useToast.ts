/**
 * useToast Hook
 *
 * Hook for managing toast notifications.
 * Provides methods to show, dismiss, and manage toasts.
 */

import { useState, useCallback, useEffect } from 'react';

export type ToastVariant = 'default' | 'success' | 'warning' | 'error';

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

export interface ToastOptions {
  title?: string;
  description?: string;
  variant?: ToastVariant;
  duration?: number;
  action?: {
    label: string;
    onClick: () => void;
  };
}

const TOAST_LIMIT = 5;
const DEFAULT_DURATION = 5000;

// Global state for toasts (simple implementation without external state management)
let toasts: Toast[] = [];
let listeners: Array<(toasts: Toast[]) => void> = [];

const notifyListeners = () => {
  listeners.forEach((listener) => listener([...toasts]));
};

const addToast = (toast: Toast) => {
  toasts = [toast, ...toasts].slice(0, TOAST_LIMIT);
  notifyListeners();
};

const removeToast = (id: string) => {
  toasts = toasts.filter((t) => t.id !== id);
  notifyListeners();
};

const clearToasts = () => {
  toasts = [];
  notifyListeners();
};

let toastCount = 0;

export function useToast() {
  const [localToasts, setLocalToasts] = useState<Toast[]>(toasts);

  useEffect(() => {
    listeners.push(setLocalToasts);
    return () => {
      listeners = listeners.filter((l) => l !== setLocalToasts);
    };
  }, []);

  const toast = useCallback((options: ToastOptions) => {
    const id = `toast-${++toastCount}`;
    const duration = options.duration ?? DEFAULT_DURATION;

    const newToast: Toast = {
      id,
      ...options,
      duration,
    };

    addToast(newToast);

    // Auto dismiss
    if (duration > 0) {
      setTimeout(() => {
        removeToast(id);
      }, duration);
    }

    return id;
  }, []);

  const dismiss = useCallback((id: string) => {
    removeToast(id);
  }, []);

  const dismissAll = useCallback(() => {
    clearToasts();
  }, []);

  // Convenience methods
  const success = useCallback(
    (options: Omit<ToastOptions, 'variant'>) => toast({ ...options, variant: 'success' }),
    [toast]
  );

  const warning = useCallback(
    (options: Omit<ToastOptions, 'variant'>) => toast({ ...options, variant: 'warning' }),
    [toast]
  );

  const error = useCallback(
    (options: Omit<ToastOptions, 'variant'>) => toast({ ...options, variant: 'error' }),
    [toast]
  );

  return {
    toasts: localToasts,
    toast,
    dismiss,
    dismissAll,
    success,
    warning,
    error,
  };
}

export default useToast;
