/**
 * useAnalyticsLayout Hook
 *
 * Manages analytics dashboard card state with localStorage persistence.
 * Handles card ordering, enabling/disabling, and drag-and-drop reordering.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  DEFAULT_ANALYTICS_CARDS,
  type AnalyticsCardConfig,
} from '../components/analytics/AnalyticsCardRegistry';

const STORAGE_KEY = 'analytics-dashboard-layout';

/**
 * Merge saved layout with defaults (handles new cards added later)
 */
function mergeWithDefaults(saved: AnalyticsCardConfig[]): AnalyticsCardConfig[] {
  const savedIds = new Set(saved.map(c => c.id));
  const merged = [...saved];

  // Add any new default cards that don't exist in saved
  DEFAULT_ANALYTICS_CARDS.forEach(defaultCard => {
    if (!savedIds.has(defaultCard.id)) {
      merged.push({ ...defaultCard, order: merged.length });
    }
  });

  return merged.sort((a, b) => a.order - b.order);
}

/**
 * Load cards from localStorage
 */
function loadFromStorage(): AnalyticsCardConfig[] {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      const parsed = JSON.parse(saved);
      return mergeWithDefaults(parsed);
    }
  } catch (error) {
    console.error('Failed to load analytics layout from localStorage:', error);
  }
  return [...DEFAULT_ANALYTICS_CARDS];
}

/**
 * Save cards to localStorage
 */
function saveToStorage(cards: AnalyticsCardConfig[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(cards));
  } catch (error) {
    console.error('Failed to save analytics layout to localStorage:', error);
  }
}

export interface UseAnalyticsLayoutReturn {
  /** All cards (enabled and disabled) */
  cards: AnalyticsCardConfig[];
  /** Only enabled cards, sorted by order */
  enabledCards: AnalyticsCardConfig[];
  /** Update all cards */
  updateCards: (newCards: AnalyticsCardConfig[]) => void;
  /** Toggle a card's enabled state */
  toggleCard: (cardId: string) => void;
  /** Reset to default configuration */
  resetToDefaults: () => void;
  /** Move a card from one position to another (for drag-and-drop) */
  moveCard: (dragIndex: number, hoverIndex: number) => void;
}

export function useAnalyticsLayout(): UseAnalyticsLayoutReturn {
  const [cards, setCards] = useState<AnalyticsCardConfig[]>(loadFromStorage);

  // Auto-save to localStorage on changes
  useEffect(() => {
    saveToStorage(cards);
  }, [cards]);

  // Update all cards
  const updateCards = useCallback((newCards: AnalyticsCardConfig[]) => {
    setCards(newCards);
  }, []);

  // Toggle a single card's enabled state
  const toggleCard = useCallback((cardId: string) => {
    setCards(prevCards =>
      prevCards.map(card =>
        card.id === cardId ? { ...card, enabled: !card.enabled } : card
      )
    );
  }, []);

  // Reset to default configuration
  const resetToDefaults = useCallback(() => {
    setCards([...DEFAULT_ANALYTICS_CARDS]);
    localStorage.removeItem(STORAGE_KEY);
  }, []);

  // Move card (for drag-and-drop reordering)
  const moveCard = useCallback((dragIndex: number, hoverIndex: number) => {
    setCards(prevCards => {
      const enabledCards = prevCards.filter(c => c.enabled).sort((a, b) => a.order - b.order);
      const dragCard = enabledCards[dragIndex];

      if (!dragCard) return prevCards;

      // Create new order for enabled cards
      const newEnabledCards = [...enabledCards];
      newEnabledCards.splice(dragIndex, 1);
      newEnabledCards.splice(hoverIndex, 0, dragCard);

      // Update order values for all cards
      return prevCards.map(card => {
        const newIndex = newEnabledCards.findIndex(c => c.id === card.id);
        if (newIndex !== -1) {
          return { ...card, order: newIndex };
        }
        // Disabled cards keep their relative order after enabled cards
        return card;
      }).sort((a, b) => a.order - b.order);
    });
  }, []);

  // Get only enabled cards, sorted by order
  const enabledCards = cards
    .filter(c => c.enabled)
    .sort((a, b) => a.order - b.order);

  return {
    cards,
    enabledCards,
    updateCards,
    toggleCard,
    resetToDefaults,
    moveCard,
  };
}

export default useAnalyticsLayout;
