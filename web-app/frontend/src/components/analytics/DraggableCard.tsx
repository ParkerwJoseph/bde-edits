/**
 * DraggableCard Component
 *
 * Drag-and-drop wrapper for analytics cards.
 * Uses HTML5 native drag-and-drop API.
 */

import { useRef, useState } from 'react';
import { GripVertical, X } from 'lucide-react';
import { cn } from '../../lib/scorecard-utils';
import {
  type AnalyticsCardConfig,
  getCardGridSpan,
  getCardHeight,
  renderAnalyticsCard,
} from './AnalyticsCardRegistry';
import styles from '../../styles/components/analytics/DraggableCard.module.css';

export interface DraggableCardProps {
  /** Card configuration */
  card: AnalyticsCardConfig;
  /** Index in the enabled cards list */
  index: number;
  /** Callback when card is moved */
  onMove: (dragIndex: number, hoverIndex: number) => void;
  /** Callback when card is removed/disabled */
  onRemove: (cardId: string) => void;
  /** Whether edit mode is active */
  isEditMode: boolean;
}

export function DraggableCard({
  card,
  index,
  onMove,
  onRemove,
  isEditMode,
}: DraggableCardProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);

  // Drag start handler
  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isEditMode) {
      e.preventDefault();
      return;
    }
    setIsDragging(true);
    e.dataTransfer.setData('application/analytics-card', index.toString());
    e.dataTransfer.effectAllowed = 'move';

    // Set drag image (optional: could customize)
    if (ref.current) {
      e.dataTransfer.setDragImage(ref.current, 0, 0);
    }
  };

  // Drag end handler
  const handleDragEnd = () => {
    setIsDragging(false);
    setIsDragOver(false);
  };

  // Drag over handler
  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isEditMode) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setIsDragOver(true);
  };

  // Drag leave handler
  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  // Drop handler
  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isEditMode) return;
    e.preventDefault();
    setIsDragOver(false);

    const dragIndex = parseInt(e.dataTransfer.getData('application/analytics-card'), 10);
    if (!isNaN(dragIndex) && dragIndex !== index) {
      onMove(dragIndex, index);
    }
  };

  // Remove handler
  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    onRemove(card.id);
  };

  return (
    <div
      ref={ref}
      className={cn(
        styles.card,
        getCardGridSpan(card.size),
        getCardHeight(card.size),
        isDragging && styles.dragging,
        isDragOver && styles.dragOver,
        isEditMode && styles.editMode
      )}
      draggable={isEditMode}
      onDragStart={handleDragStart}
      onDragEnd={handleDragEnd}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* Edit mode overlay */}
      {isEditMode && (
        <div className={styles.editOverlay}>
          <div className={styles.dragHandle}>
            <GripVertical size={16} />
          </div>
          <button
            type="button"
            className={styles.removeButton}
            onClick={handleRemove}
            aria-label={`Remove ${card.title}`}
          >
            <X size={14} />
          </button>
        </div>
      )}

      {/* Card content */}
      <div className={styles.cardContent}>
        {renderAnalyticsCard(card)}
      </div>
    </div>
  );
}

export default DraggableCard;
