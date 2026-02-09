/**
 * AnalyticsCustomizer Component
 *
 * Sheet panel for customizing analytics dashboard cards.
 * Allows toggling cards on/off, grouped by category with collapsible sections.
 */

import { useState } from 'react';
import {
  Settings2,
  GripVertical,
  Eye,
  EyeOff,
  RotateCcw,
  ChevronDown,
  ChevronRight,
  Sparkles,
} from 'lucide-react';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from '../ui/Sheet';
import { Button } from '../ui/Button';
import { Switch } from '../ui/Switch';
import {
  type AnalyticsCardConfig,
  type CardCategory,
  CATEGORY_LABELS,
} from './AnalyticsCardRegistry';
import styles from '../../styles/components/analytics/AnalyticsCustomizer.module.css';

export interface AnalyticsCustomizerProps {
  /** All cards configuration */
  cards: AnalyticsCardConfig[];
  /** Callback when cards change */
  onCardsChange: (cards: AnalyticsCardConfig[]) => void;
  /** Callback to reset to defaults */
  onReset: () => void;
}

export function AnalyticsCustomizer({
  cards,
  onCardsChange,
  onReset,
}: AnalyticsCustomizerProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
    new Set(Object.keys(CATEGORY_LABELS))
  );

  // Group cards by category
  const cardsByCategory = cards.reduce((acc, card) => {
    if (!acc[card.category]) {
      acc[card.category] = [];
    }
    acc[card.category].push(card);
    return acc;
  }, {} as Record<CardCategory, AnalyticsCardConfig[]>);

  // Toggle a single card
  const handleToggleCard = (cardId: string) => {
    const updatedCards = cards.map(card =>
      card.id === cardId ? { ...card, enabled: !card.enabled } : card
    );
    onCardsChange(updatedCards);
  };

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    const newExpanded = new Set(expandedCategories);
    if (newExpanded.has(category)) {
      newExpanded.delete(category);
    } else {
      newExpanded.add(category);
    }
    setExpandedCategories(newExpanded);
  };

  // Enable all cards
  const enableAll = () => {
    const updatedCards = cards.map(card => ({ ...card, enabled: true }));
    onCardsChange(updatedCards);
  };

  // Disable all cards
  const disableAll = () => {
    const updatedCards = cards.map(card => ({ ...card, enabled: false }));
    onCardsChange(updatedCards);
  };

  // Count enabled cards
  const enabledCount = cards.filter(c => c.enabled).length;

  // Get size badge color class
  const getSizeBadgeClass = (size: string) => {
    switch (size) {
      case 'sm': return styles.sizeBadgeSm;
      case 'md': return styles.sizeBadgeMd;
      case 'lg': return styles.sizeBadgeLg;
      case 'xl': return styles.sizeBadgeXl;
      default: return styles.sizeBadgeSm;
    }
  };

  return (
    <>
      <Button
        variant="outline"
        size="sm"
        className={styles.triggerButton}
        onClick={() => setIsOpen(true)}
      >
        <Settings2 size={16} />
        <span className={styles.triggerText}>Customize</span>
        <span className={styles.countBadge}>{enabledCount}</span>
      </Button>

      <Sheet open={isOpen} onOpenChange={setIsOpen}>
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle className={styles.sheetTitle}>
              <Sparkles size={20} className={styles.titleIcon} />
              Customize Analytics
            </SheetTitle>
            <SheetDescription>
              Toggle cards on/off and drag to reorder. Changes are saved automatically.
            </SheetDescription>
          </SheetHeader>

          {/* Quick Actions */}
          <div className={styles.quickActions}>
            <Button variant="outline" size="sm" onClick={enableAll} className={styles.quickActionBtn}>
              <Eye size={14} />
              <span>Show All</span>
            </Button>
            <Button variant="outline" size="sm" onClick={disableAll} className={styles.quickActionBtn}>
              <EyeOff size={14} />
              <span>Hide All</span>
            </Button>
            <Button variant="ghost" size="sm" onClick={onReset} className={styles.quickActionBtn}>
              <RotateCcw size={14} />
              <span>Reset</span>
            </Button>
          </div>

          {/* Scrollable Content */}
          <div className={styles.scrollArea}>
            <div className={styles.content}>
              {(Object.entries(cardsByCategory) as [CardCategory, AnalyticsCardConfig[]][]).map(
                ([category, categoryCards]) => {
                  const categoryInfo = CATEGORY_LABELS[category];
                  const CategoryIcon = categoryInfo.icon;
                  const enabledInCategory = categoryCards.filter(c => c.enabled).length;
                  const isExpanded = expandedCategories.has(category);

                  return (
                    <div key={category} className={styles.categorySection}>
                      {/* Category Header - Clickable */}
                      <button
                        className={styles.categoryHeader}
                        onClick={() => toggleCategory(category)}
                      >
                        <div className={styles.categoryLeft}>
                          <CategoryIcon size={16} className={styles.categoryIcon} />
                          <span className={styles.categoryLabel}>{categoryInfo.label}</span>
                          <span className={styles.categoryCount}>
                            {enabledInCategory}/{categoryCards.length}
                          </span>
                        </div>
                        {isExpanded ? (
                          <ChevronDown size={16} className={styles.chevron} />
                        ) : (
                          <ChevronRight size={16} className={styles.chevron} />
                        )}
                      </button>

                      {/* Category Cards - Collapsible */}
                      {isExpanded && (
                        <div className={styles.cardList}>
                          {categoryCards.map(card => (
                            <div
                              key={card.id}
                              className={`${styles.cardItem} ${card.enabled ? styles.cardItemEnabled : styles.cardItemDisabled}`}
                            >
                              <div className={styles.cardLeft}>
                                <GripVertical size={16} className={styles.gripHandle} />
                                <div className={styles.cardInfo}>
                                  <div className={styles.cardTitleRow}>
                                    <span className={styles.cardTitle}>{card.title}</span>
                                    <span className={`${styles.sizeBadge} ${getSizeBadgeClass(card.size)}`}>
                                      {card.size.toUpperCase()}
                                    </span>
                                  </div>
                                  <span className={styles.cardDescription}>{card.description}</span>
                                </div>
                              </div>
                              <Switch
                                checked={card.enabled}
                                onCheckedChange={() => handleToggleCard(card.id)}
                                aria-label={`Toggle ${card.title}`}
                              />
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                }
              )}
            </div>
          </div>
        </SheetContent>
      </Sheet>
    </>
  );
}

export default AnalyticsCustomizer;
