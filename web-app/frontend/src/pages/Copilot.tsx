import { useState, useRef, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  User,
  FileText,
  Target,
  AlertTriangle,
  Calculator,
  Sparkles,
  ChevronRight,
  Loader2,
  Trash2,
} from 'lucide-react';
import { chatApi } from '../api/chatApi';
import type { ChatSession, ChatMessageResponse, SourceInfo } from '../api/chatApi';
import { documentApi } from '../api/documentApi';
import type { Document } from '../api/documentApi';
import { AppLayout } from '../components/layout/AppLayout';
import { useCompany } from '../contexts/CompanyContext';
import { ChatSendIcon } from '../components/icons/ChatSendIcon';
import { PILLARS_ORDERED } from '../lib/constants';
import styles from '../styles/pages/Copilot.module.css';

interface LocationState {
  prompt?: string;
}

type StreamPhase = 'searching' | 'generating' | 'streaming' | null;

interface DisplayMessage {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: SourceInfo[];
  isStreaming?: boolean;
  streamPhase?: StreamPhase;
  statusMessage?: string;
}

const QUICK_PROMPTS = [
  { id: 'full', label: 'Full 8-Pillar Analysis', icon: Target, mode: 'analysis' },
  { id: 'deep', label: 'Pillar Deep-Dive', icon: Sparkles, mode: 'deep-dive' },
  { id: 'red', label: 'Red-Flag Scan', icon: AlertTriangle, mode: 'scan' },
  { id: 'valuation', label: 'Valuation Compute', icon: Calculator, mode: 'valuation' },
];

const PILLAR_PROMPTS = PILLARS_ORDERED.slice(0, 4).map((p) => ({
  id: p.id,
  label: `Analyze ${p.name}`,
  description: p.description,
}));

export default function Copilot() {
  const location = useLocation();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<DisplayMessage[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [mode, setMode] = useState<string>('analysis');
  const [activeTab, setActiveTab] = useState<'recent' | 'cited'>('recent');
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const autoSubmitRef = useRef(false);

  // Use global company context
  const { selectedCompanyId } = useCompany();

  // Handle incoming prompt from navigation state (e.g., from Home page quick prompts)
  useEffect(() => {
    const state = location.state as LocationState | null;
    if (state?.prompt && !autoSubmitRef.current) {
      setPendingPrompt(state.prompt);
      autoSubmitRef.current = true;
      // Clear the state to prevent re-triggering on refresh
      window.history.replaceState({}, document.title);
    }
  }, [location.state]);

  // Load documents and sessions when company changes
  useEffect(() => {
    if (selectedCompanyId) {
      loadDocuments();
      loadSessions();
    }
  }, [selectedCompanyId]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadDocuments = async () => {
    try {
      const response = await documentApi.list({
        status: 'completed',
        company_id: selectedCompanyId || undefined,
      });
      setDocuments(response.documents);
    } catch (err) {
      console.error('Failed to load documents:', err);
    }
  };

  const loadSessions = async () => {
    try {
      setSessionsLoading(true);
      const response = await chatApi.listSessions(selectedCompanyId || undefined);
      setSessions(response.sessions);
    } catch (err) {
      console.error('Failed to load sessions:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadSession = async (sessionId: string) => {
    try {
      setLoading(true);
      const session = await chatApi.getSession(sessionId);
      setCurrentSessionId(sessionId);

      // Convert messages to display format
      const displayMessages: DisplayMessage[] = session.messages.map((msg: ChatMessageResponse) => ({
        id: msg.id,
        role: msg.role,
        content: msg.content,
        sources: msg.sources || undefined,
      }));
      setMessages(displayMessages);
    } catch (err) {
      console.error('Failed to load session:', err);
      setError('Failed to load chat session');
    } finally {
      setLoading(false);
    }
  };

  const startNewChat = () => {
    setCurrentSessionId(null);
    setMessages([]);
    setError(null);
  };

  const deleteSession = async (sessionId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm('Delete this chat?')) return;

    try {
      await chatApi.deleteSession(sessionId);
      setSessions(sessions.filter(s => s.id !== sessionId));
      if (currentSessionId === sessionId) {
        startNewChat();
      }
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleSend = async (messageOverride?: string) => {
    const messageToSend = messageOverride || input.trim();
    if (!messageToSend || loading) return;

    const userMessage = messageToSend;
    setInput('');
    setError(null);

    const newMessages: DisplayMessage[] = [
      ...messages,
      { role: 'user', content: userMessage },
    ];
    setMessages(newMessages);
    setLoading(true);

    // Add placeholder for assistant message with initial searching phase
    const assistantMessageIndex = newMessages.length;
    setMessages([
      ...newMessages,
      {
        role: 'assistant',
        content: '',
        isStreaming: true,
        streamPhase: 'searching',
        statusMessage: 'Searching documents...',
      },
    ]);

    let streamedSources: SourceInfo[] = [];

    try {
      await chatApi.chatStream(
        {
          query: userMessage,
          session_id: currentSessionId,
          company_id: selectedCompanyId || null,
          document_ids: null,
          top_k: 5,
        },
        {
          onStatus: (phase, message) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[assistantMessageIndex] = {
                ...updated[assistantMessageIndex],
                streamPhase: phase as StreamPhase,
                statusMessage: message,
              };
              return updated;
            });
          },
          onSession: (sessionId) => {
            if (!currentSessionId) {
              setCurrentSessionId(sessionId);
              loadSessions();
            }
          },
          onSources: (sources) => {
            streamedSources = sources;
          },
          onChunk: (_chunk, fullText) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[assistantMessageIndex] = {
                role: 'assistant',
                content: fullText,
                isStreaming: true,
                streamPhase: 'streaming',
                statusMessage: undefined,
              };
              return updated;
            });
          },
          onDone: (fullText) => {
            setMessages((prev) => {
              const updated = [...prev];
              updated[assistantMessageIndex] = {
                role: 'assistant',
                content: fullText,
                sources: streamedSources,
                isStreaming: false,
                streamPhase: null,
                statusMessage: undefined,
              };
              return updated;
            });
            setLoading(false);
          },
          onError: (errorMsg) => {
            setError(errorMsg);
            setMessages((prev) => prev.slice(0, -1));
            setLoading(false);
          },
        }
      );
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get response';
      setError(errorMessage);
      setMessages(newMessages);
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickPrompt = (prompt: typeof QUICK_PROMPTS[0]) => {
    setMode(prompt.mode);
    setInput(`Run a ${prompt.label.toLowerCase()} for the selected company`);
  };

  const handlePillarPrompt = (pillar: typeof PILLAR_PROMPTS[0]) => {
    setInput(`Provide a detailed analysis of the ${pillar.label.replace('Analyze ', '')} pillar, including current scores, risks, and recommendations.`);
  };

  // Auto-submit pending prompt from navigation (e.g., Home page quick prompts)
  useEffect(() => {
    if (pendingPrompt && selectedCompanyId && !loading && !sessionsLoading) {
      const promptToSend = pendingPrompt;
      setPendingPrompt(null);
      // Small delay to ensure component is fully ready
      setTimeout(() => {
        handleSend(promptToSend);
      }, 100);
    }
  }, [pendingPrompt, selectedCompanyId, loading, sessionsLoading]);

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffDays = Math.floor((now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24));

    if (diffDays === 0) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return date.toLocaleDateString([], { weekday: 'short' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
    }
  };

  // Get all cited sources from messages
  const citedSources = messages
    .filter(m => m.sources && m.sources.length > 0)
    .flatMap(m => m.sources!)
    .reduce((acc: SourceInfo[], source) => {
      // Deduplicate by document name
      if (!acc.find(s => s.document_name === source.document_name)) {
        acc.push(source);
      }
      return acc;
    }, []);

  return (
    <AppLayout title="AI Analyst">
      <div className={styles.container}>
        {/* Main Chat Area */}
        <div className={styles.mainArea}>
          <div className={styles.chatCard}>
            {/* Mode Selector Header */}
            <div className={styles.modeHeader}>
              <div className={styles.modeButtons}>
                {QUICK_PROMPTS.map((prompt) => {
                  const Icon = prompt.icon;
                  return (
                    <button
                      key={prompt.id}
                      className={`${styles.modeButton} ${mode === prompt.mode ? styles.modeButtonActive : ''}`}
                      onClick={() => handleQuickPrompt(prompt)}
                    >
                      <Icon size={16} />
                      {prompt.label}
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Messages Area */}
            <div className={styles.messagesArea}>
              <div className={styles.messagesContent}>
                {messages.length === 0 ? (
                  <div className={styles.emptyState}>
                    <div className={styles.emptyIcon}>
                      <Bot size={48} />
                    </div>
                    <h3 className={styles.emptyTitle}>Welcome to AI Analyst</h3>
                    <p className={styles.emptyDescription}>
                      Ask questions about your portfolio companies, run analyses,
                      or get recommendations based on your data.
                    </p>
                    <div className={styles.pillarPrompts}>
                      {PILLAR_PROMPTS.map((pillar) => (
                        <button
                          key={pillar.id}
                          className={styles.pillarPromptButton}
                          onClick={() => handlePillarPrompt(pillar)}
                        >
                          {pillar.label}
                          <ChevronRight size={14} />
                        </button>
                      ))}
                    </div>
                  </div>
                ) : (
                  <>
                    {messages.map((message, index) => (
                      <div
                        key={message.id || index}
                        className={`${styles.messageRow} ${message.role === 'user' ? styles.messageRowUser : ''}`}
                      >
                        {message.role === 'assistant' && (
                          <div className={styles.avatarBot}>
                            <Bot size={16} />
                          </div>
                        )}
                        <div
                          className={`${styles.messageBubble} ${
                            message.role === 'user' ? styles.messageBubbleUser : styles.messageBubbleAssistant
                          }`}
                        >
                          {message.role === 'assistant' ? (
                            <>
                              {message.isStreaming && message.statusMessage && !message.content && (
                                <div className={styles.statusIndicator}>
                                  <Loader2 size={16} className={styles.spinner} />
                                  <span>{message.statusMessage}</span>
                                </div>
                              )}
                              {message.content && (
                                <div className={styles.markdownContent}>
                                  <ReactMarkdown>{message.content}</ReactMarkdown>
                                </div>
                              )}
                              {message.isStreaming && message.content && (
                                <span className={styles.streamingCursor}>|</span>
                              )}
                              {message.sources && message.sources.length > 0 && (
                                <div className={styles.sources}>
                                  <p className={styles.sourcesLabel}>Sources:</p>
                                  <div className={styles.sourcesBadges}>
                                    {message.sources.map((source, idx) => (
                                      <span key={idx} className={styles.sourceBadge}>
                                        <FileText size={12} />
                                        {source.document_name}
                                        {source.page_number && ` (p. ${source.page_number})`}
                                      </span>
                                    ))}
                                  </div>
                                </div>
                              )}
                            </>
                          ) : (
                            <p className={styles.userMessageText}>{message.content}</p>
                          )}
                        </div>
                        {message.role === 'user' && (
                          <div className={styles.avatarUser}>
                            <User size={16} />
                          </div>
                        )}
                      </div>
                    ))}
                    {loading && messages[messages.length - 1]?.role !== 'assistant' && (
                      <div className={styles.messageRow}>
                        <div className={styles.avatarBot}>
                          <Bot size={16} />
                        </div>
                        <div className={styles.messageBubbleAssistant}>
                          <Loader2 size={16} className={styles.spinner} />
                        </div>
                      </div>
                    )}
                    <div ref={messagesEndRef} />
                  </>
                )}
              </div>
            </div>

            {error && <div className={styles.error}>{error}</div>}

            {/* Input Area */}
            <div className={styles.inputArea}>
              <div className={styles.inputWrapper}>
                <input
                  type="text"
                  className={styles.input}
                  placeholder="Ask about your portfolio companies..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={loading}
                />
                <button
                  className={styles.sendButton}
                  onClick={() => handleSend()}
                  disabled={loading || !input.trim()}
                >
                  <ChatSendIcon size={18} />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Side Panel - Source Documents */}
        <div className={styles.sidePanel}>
          <div className={styles.sidePanelCard}>
            <div className={styles.sidePanelHeader}>
              <FileText size={16} />
              <span>Source Documents</span>
            </div>
            <div className={styles.sidePanelContent}>
              {/* Tabs */}
              <div className={styles.tabs}>
                <button
                  className={`${styles.tab} ${activeTab === 'recent' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('recent')}
                >
                  Recent
                </button>
                <button
                  className={`${styles.tab} ${activeTab === 'cited' ? styles.tabActive : ''}`}
                  onClick={() => setActiveTab('cited')}
                >
                  Cited
                </button>
              </div>

              {/* Tab Content */}
              <div className={styles.documentList}>
                {activeTab === 'recent' ? (
                  documents.length === 0 ? (
                    <p className={styles.noDocuments}>No documents uploaded</p>
                  ) : (
                    documents.slice(0, 10).map((doc) => (
                      <button key={doc.id} className={styles.documentItem}>
                        <FileText size={16} className={styles.documentIcon} />
                        <span className={styles.documentName}>{doc.original_filename}</span>
                      </button>
                    ))
                  )
                ) : citedSources.length === 0 ? (
                  <p className={styles.noDocuments}>No citations yet</p>
                ) : (
                  citedSources.map((source, idx) => (
                    <button key={idx} className={styles.documentItem}>
                      <FileText size={16} className={styles.documentIconCited} />
                      <span className={styles.documentName}>{source.document_name}</span>
                    </button>
                  ))
                )}
              </div>

              {/* Chat History */}
              <div className={styles.chatHistorySection}>
                <div className={styles.chatHistoryHeader}>
                  <span>Chat History</span>
                  <button className={styles.newChatButton} onClick={startNewChat}>
                    + New
                  </button>
                </div>
                <div className={styles.sessionsList}>
                  {sessionsLoading ? (
                    <div className={styles.sessionsLoading}>Loading...</div>
                  ) : sessions.length === 0 ? (
                    <div className={styles.noSessions}>No chat history</div>
                  ) : (
                    sessions.slice(0, 5).map((session) => (
                      <div
                        key={session.id}
                        className={`${styles.sessionItem} ${currentSessionId === session.id ? styles.sessionItemActive : ''}`}
                        onClick={() => loadSession(session.id)}
                      >
                        <div className={styles.sessionInfo}>
                          <span className={styles.sessionTitle}>{session.title}</span>
                          <span className={styles.sessionDate}>{formatDate(session.updated_at)}</span>
                        </div>
                        <button
                          className={styles.deleteSessionButton}
                          onClick={(e) => deleteSession(session.id, e)}
                          title="Delete chat"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
