import React, { useEffect, useState } from "react";
import "./App.css";

/** ---------- Types that mirror FastAPI models ---------- */

export interface ThreadMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string; // backend field
}

export interface SuggestedAction {
  title: string;
  steps: string[];
}

export interface FollowupQuestion {
  text: string;
}

export interface SimilarIncident {
  incident_id: string;
  subject: string;
  description: string;
  similarity_score: number;
  created_at?: string | null;
}

export interface TicketHistoryItem {
  ticket_id: string;
  id: string;
  subject: string;
  severity: string;
  user_upn?: string | null;
  created_at: string;
  status?: "open" | "closed";
}

export interface TicketCreateResponse {
  ticket_id: string;
  subject: string;
  description: string;
  severity: string;
  user_upn?: string | null;
  answer: string;
  suggested_actions: SuggestedAction[];
  followup_questions: FollowupQuestion[];
  similar_incidents: SimilarIncident[];
  thread: ThreadMessage[];
  created_at: string;
  status?: "open" | "closed";
}

export interface TicketThreadResponse {
  ticket_id: string;
  subject: string;
  description: string;
  severity: string;
  user_upn?: string | null;
  created_at: string;
  status?: "open" | "closed";

  thread: ThreadMessage[];
  suggested_actions: SuggestedAction[];
  followup_questions: FollowupQuestion[];
  similar_incidents: SimilarIncident[];
}

/** ---------- Helper ---------- */

const API_BASE =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

/** ---------- Main App ---------- */

const App: React.FC = () => {
  const [history, setHistory] = useState<TicketHistoryItem[]>([]);
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null);
  const [thread, setThread] = useState<TicketThreadResponse | null>(null);

  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [userUpn, setUserUpn] = useState("");
  const [severity, setSeverity] = useState<"low" | "medium" | "high">("medium");

  const [loadingHistory, setLoadingHistory] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [followup, setFollowup] = useState("");
  const [error, setError] = useState<string | null>(null);

  /** ------ Load ticket history on mount ------ */
  useEffect(() => {
    const loadHistory = async () => {
      try {
        setLoadingHistory(true);
        setError(null);

        // GET /tickets  (FastAPI will 307 -> /tickets/ which is fine)
        const res = await fetch(`${API_BASE}/tickets`);
        if (!res.ok) {
          const txt = await res.text();
          console.error("History error:", res.status, txt);
          throw new Error(`History HTTP ${res.status}`);
        }

        const data: TicketHistoryItem[] = await res.json();
        setHistory(data || []);
      } catch (err: any) {
        console.error("Failed to load history:", err);
        setError("Failed to load ticket history.");
      } finally {
        setLoadingHistory(false);
      }
    };

    loadHistory();
  }, []);

  /** ------ Normalize thread from any response ------ */
  const normalizeThread = (
    data: TicketCreateResponse | TicketThreadResponse
  ): TicketThreadResponse => {
    const msgs: ThreadMessage[] = (data as any).thread || [];

    return {
      ticket_id: data.ticket_id,
      subject: data.subject,
      description: (data as any).description || "",
      severity: (data as any).severity || "medium",
      user_upn: (data as any).user_upn ?? null,
      created_at:
        (data as any).created_at || new Date().toISOString(),
      status: (data as any).status ?? "open",
      thread: msgs || [],
      suggested_actions: (data as any).suggested_actions || [],
      followup_questions: (data as any).followup_questions || [],
      similar_incidents: (data as any).similar_incidents || [],
    };
  };

  /** ------ Submit new ticket ------ */
  const handleSubmitTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      setError(null);

      const payload = {
        subject,
        description,
        user_upn: userUpn || null,
        severity,
      };

      const res = await fetch(`${API_BASE}/tickets`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const txt = await res.text();
        console.error("Create ticket error:", res.status, txt);
        throw new Error(`Create ticket HTTP ${res.status}`);
      }

      const data: TicketCreateResponse = await res.json();
      console.log("Ticket created:", data);

      // Clear form
      setSubject("");
      setDescription("");

      // Update history list (prepend)
      const newHistoryItem: TicketHistoryItem = {
        ticket_id: data.ticket_id,
        id: data.ticket_id,
        subject: data.subject,
        severity: data.severity,
        user_upn: data.user_upn,
        created_at: data.created_at,
        status: data.status ?? "open",
      };
      setHistory((prev) => [newHistoryItem, ...(prev || [])]);

      // Show thread immediately using the response
      const t = normalizeThread(data);
      setSelectedTicketId(t.ticket_id);
      setThread(t);
    } catch (err: any) {
      console.error("Submit ticket failed:", err);
      setError("Failed to submit ticket.");
    } finally {
      setSubmitting(false);
    }
  };

  /** ------ Load thread for a ticket from history ------ */
  const handleSelectTicket = async (ticketId: string) => {
    try {
      setSelectedTicketId(ticketId);
      setLoadingThread(true);
      setError(null);

      const res = await fetch(`${API_BASE}/tickets/${ticketId}/thread`);
      if (!res.ok) {
        const txt = await res.text();
        console.error("Thread error:", res.status, txt);
        throw new Error(`Thread HTTP ${res.status}`);
      }

      const data: TicketThreadResponse = await res.json();
      console.log("Loaded thread:", data);

      const t = normalizeThread(data);
      setThread(t);
    } catch (err: any) {
      console.error("Failed to load thread:", err);
      setError("Failed to load ticket thread.");
      setThread(null);
    } finally {
      setLoadingThread(false);
    }
  };

  /** ------ Send follow-up message ------ */
  const handleSendFollowup = async () => {
    if (!selectedTicketId || !followup.trim()) return;

    try {
      setLoadingThread(true);
      setError(null);

      const res = await fetch(
        `${API_BASE}/tickets/${selectedTicketId}/followup`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: followup }),
        }
      );

      if (!res.ok) {
        const txt = await res.text();
        console.error("Followup error:", res.status, txt);
        throw new Error(`Followup HTTP ${res.status}`);
      }

      const data: TicketThreadResponse = await res.json();
      console.log("Followup thread:", data);

      const t = normalizeThread(data);
      setThread(t);
      setFollowup("");
    } catch (err: any) {
      console.error("Failed to send follow-up:", err);
      setError("Failed to send follow-up.");
    } finally {
      setLoadingThread(false);
    }
  };

  /** ------ Optional: Close ticket ------ */
  const handleCloseTicket = async () => {
    if (!selectedTicketId) return;

    try {
      setLoadingThread(true);
      setError(null);

      const res = await fetch(
        `${API_BASE}/tickets/${selectedTicketId}/close`,
        {
          method: "POST",
        }
      );

      if (!res.ok) {
        const txt = await res.text();
        console.error("Close ticket error:", res.status, txt);
        throw new Error(`Close ticket HTTP ${res.status}`);
      }

      const data: TicketThreadResponse = await res.json();
      const t = normalizeThread(data);
      setThread(t);

      // Update history status
      setHistory((prev) =>
        (prev || []).map((h) =>
          h.ticket_id === selectedTicketId
            ? { ...h, status: t.status ?? "closed" }
            : h
        )
      );
    } catch (err: any) {
      console.error("Failed to close ticket:", err);
      setError("Failed to close ticket.");
    } finally {
      setLoadingThread(false);
    }
  };

  /** ------ UI helpers ------ */

  const renderMessages = () => {
    if (!thread) return null;
    const msgs = thread.thread || [];
    if (!msgs.length) return <p>No messages yet.</p>;

    return (
      <div className="messages">
        {msgs.map((m) => (
          <div
            key={m.id}
            className={`message-bubble ${
              m.role === "agent" ? "agent" : "user"
            }`}
          >
            <div className="message-meta">
              <span className="role">{m.role.toUpperCase()}</span>
              <span className="time">
                {m.timestamp
                  ? new Date(m.timestamp).toLocaleString()
                  : ""}
              </span>
            </div>
            <div className="message-content">{m.content}</div>
          </div>
        ))}
      </div>
    );
  };

  const renderActions = () => {
    if (!thread || !thread.suggested_actions?.length) return null;
    return (
      <div className="panel">
        <h3>Suggested Actions</h3>
        {thread.suggested_actions.map((a, idx) => (
          <div key={idx} className="action-block">
            <strong>{a.title}</strong>
            <ol>
              {a.steps.map((s, sIdx) => (
                <li key={sIdx}>{s}</li>
              ))}
            </ol>
          </div>
        ))}
      </div>
    );
  };

  const renderQuestions = () => {
    if (!thread || !thread.followup_questions?.length) return null;
    return (
      <div className="panel">
        <h3>Questions for User</h3>
        <ul>
          {thread.followup_questions.map((q, idx) => (
            <li key={idx}>{q.text}</li>
          ))}
        </ul>
      </div>
    );
  };

  const renderSimilarIncidents = () => {
    if (!thread || !thread.similar_incidents?.length) return null;
    return (
      <div className="panel">
        <h3>Similar Incidents</h3>
        <ul>
          {thread.similar_incidents.map((inc) => (
            <li key={inc.incident_id}>
              <strong>{inc.subject}</strong>{" "}
              {typeof inc.similarity_score === "number" && (
                <span className="similar-score">
                  (score {inc.similarity_score.toFixed(3)})
                </span>
              )}
              <div className="similar-desc">{inc.description}</div>
            </li>
          ))}
        </ul>
      </div>
    );
  };

  /** ------ Render ------ */

  return (
    <div className="app-root">
      <header className="app-header">
        <h1>Enterprise Ticket Agent</h1>
        <span className="env-label">Backend: {API_BASE}</span>
      </header>

      {error && <div className="error-banner">{error}</div>}

      <div className="app-layout">
        {/* Left column: create + history */}
        <div className="left-column">
          <section className="card">
            <h2>New Ticket</h2>
            <form onSubmit={handleSubmitTicket} className="ticket-form">
              <label>
                Subject
                <input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                />
              </label>
              <label>
                Description
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={4}
                  required
                />
              </label>
              <label>
                User UPN / Email
                <input
                  value={userUpn}
                  onChange={(e) => setUserUpn(e.target.value)}
                  placeholder="alice@contoso.com"
                />
              </label>
              <label>
                Severity
                <select
                  value={severity}
                  onChange={(e) =>
                    setSeverity(e.target.value as "low" | "medium" | "high")
                  }
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                </select>
              </label>
              <button type="submit" disabled={submitting}>
                {submitting ? "Submitting..." : "Submit Ticket"}
              </button>
            </form>
          </section>

          <section className="card history-card">
            <div className="history-header">
              <h2>Ticket History</h2>
              {loadingHistory && (
                <span className="small-loading">Loading…</span>
              )}
            </div>
            {!history.length && !loadingHistory && (
              <p className="empty">No tickets yet.</p>
            )}
            <ul className="history-list">
              {history.map((t) => (
                <li
                  key={t.ticket_id}
                  className={
                    t.ticket_id === selectedTicketId
                      ? "selected history-item"
                      : "history-item"
                  }
                  onClick={() => handleSelectTicket(t.ticket_id)}
                >
                  <div className="history-subject">{t.subject}</div>
                  <div className="history-meta">
                    <span className={`severity severity-${t.severity}`}>
                      {t.severity.toUpperCase()}
                    </span>
                    <span className="history-time">
                      {t.created_at
                        ? new Date(t.created_at).toLocaleString()
                        : ""}
                    </span>
                  </div>
                  <div className="history-meta">
                    {t.user_upn && (
                      <span className="history-user">{t.user_upn}</span>
                    )}
                    {t.status && (
                      <span
                        className={`status-badge status-${t.status.toLowerCase()}`}
                      >
                        {t.status.toUpperCase()}
                      </span>
                    )}
                  </div>
                </li>
              ))}
            </ul>
          </section>
        </div>

        {/* Right column: thread / actions / questions / similar */}
        <div className="right-column">
          <section className="card thread-card">
            {loadingThread && (
              <div className="overlay-loading">Thinking / loading…</div>
            )}

            {!thread && !loadingThread && (
              <p className="empty">
                Submit a ticket or click one from history to see the
                conversation.
              </p>
            )}

            {thread && (
              <>
                <div className="thread-header">
                  <h2>{thread.subject}</h2>
                  <div className="thread-meta">
                    <span className={`severity severity-${thread.severity}`}>
                      {thread.severity.toUpperCase()}
                    </span>
                    <span>
                      Opened:{" "}
                      {thread.created_at
                        ? new Date(thread.created_at).toLocaleString()
                        : ""}
                    </span>
                    {thread.user_upn && (
                      <span>User: {thread.user_upn}</span>
                    )}
                    {thread.status && (
                      <span
                        className={`status-badge status-${thread.status.toLowerCase()}`}
                      >
                        {thread.status.toUpperCase()}
                      </span>
                    )}
                    {thread.status !== "closed" && (
                      <button
                        onClick={handleCloseTicket}
                        className="close-button"
                      >
                        Close Ticket
                      </button>
                    )}
                  </div>
                </div>

                <div className="thread-description">
                  <strong>Description:</strong> {thread.description}
                </div>

                <div className="thread-messages">{renderMessages()}</div>

                <div className="followup-box">
                  <textarea
                    placeholder="Ask a follow-up question or add more details…"
                    value={followup}
                    onChange={(e) => setFollowup(e.target.value)}
                    rows={3}
                  />
                  <button
                    onClick={handleSendFollowup}
                    disabled={loadingThread || !followup.trim()}
                  >
                    Send Follow-up
                  </button>
                </div>

                <div className="thread-panels">
                  {renderActions()}
                  {renderQuestions()}
                  {renderSimilarIncidents()}
                </div>
              </>
            )}
          </section>
        </div>
      </div>
    </div>
  );
};

export default App;
