/**
 * MinimalChatBar Component
 *
 * Chat input bar with quick prompt suggestions.
 * Used for AI assistant interaction on the home page.
 */

import { useState } from 'react';
import { ArrowRight, Send } from 'lucide-react';
import styles from '../../styles/components/home/MinimalChatBar.module.css';

export interface MinimalChatBarProps {
  /** Callback when message is submitted */
  onSubmit?: (message: string) => void;
  /** Placeholder text */
  placeholder?: string;
  /** Quick prompts to show */
  quickPrompts?: string[];
}

const DEFAULT_QUICK_PROMPTS = [
  "What's my biggest risk?",
  'Explain my score',
  'How to improve multiple?',
];

export function MinimalChatBar({
  onSubmit,
  placeholder = 'Ask about exit readiness, risks, or valuation...',
  quickPrompts = DEFAULT_QUICK_PROMPTS,
}: MinimalChatBarProps) {
  const [message, setMessage] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && onSubmit) {
      onSubmit(message.trim());
      setMessage('');
    }
  };

  const handleQuickPrompt = (prompt: string) => {
    if (onSubmit) {
      onSubmit(prompt);
    }
  };

  return (
    <div className={styles.container}>
      {/* Quick prompts */}
      <div className={styles.quickPromptsWrapper}>
        <div className={styles.quickPrompts}>
          {quickPrompts.map((prompt) => (
            <button
              key={prompt}
              className={styles.quickPromptButton}
              onClick={() => handleQuickPrompt(prompt)}
            >
              {prompt}
              <ArrowRight size={12} />
            </button>
          ))}
        </div>
      </div>

      {/* Input bar */}
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.inputWrapper}>
          <input
            type="text"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            placeholder={placeholder}
            className={styles.input}
          />

          <button
            type="submit"
            disabled={!message.trim()}
            className={styles.submitButton}
          >
            <Send size={16} />
          </button>
        </div>
      </form>
    </div>
  );
}

export default MinimalChatBar;
