// src/components/TicketHistoryPanel.tsx
import React, { useEffect, useState } from "react";

export interface TicketHistoryItem {
  id: string;
  ticket_id: string;
  subject: string;
  severity: string;
  user_upn?: string | null;
  created_at: string;
}

interface Props {
  apiBaseUrl: string; // e.g. "http://127.0.0.1:8000"
  onSelectTicket: (ticketId: string) => void;
}

export const TicketHistoryPanel: React.FC<Props> = ({
  apiBaseUrl,
  onSelectTicket,
}) => {
  const [history, setHistory] = useState<TicketHistoryItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        setLoading(true);
        setError(null);

        const res = await fetch(`${apiBaseUrl}/tickets`);
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        const data: TicketHistoryItem[] = await res.json();
        setHistory(data);
      } catch (err: any) {
        console.error("Failed to load ticket history", err);
        setError(err.message || "Failed to load history");
      } finally {
        setLoading(false);
      }
    };

    fetchHistory();
  }, [apiBaseUrl]);

  return (
    <div className="ticket-history-panel">
      <h2 className="text-lg font-semibold mb-2">Ticket History</h2>

      {loading && <div className="text-sm text-gray-500">Loading...</div>}
      {error && (
        <div className="text-sm text-red-500">
          Error loading history: {error}
        </div>
      )}

      {!loading && !error && history.length === 0 && (
        <div className="text-sm text-gray-500">No tickets yet.</div>
      )}

      <ul className="space-y-1 max-h-80 overflow-y-auto">
        {history.map((item) => (
          <li
            key={item.id}
            className="border rounded-md p-2 hover:bg-gray-50 cursor-pointer"
            onClick={() => onSelectTicket(item.id)}
          >
            <div className="text-sm font-medium">{item.subject}</div>
            <div className="text-xs text-gray-500">
              #{item.ticket_id} • {item.severity} •{" "}
              {new Date(item.created_at).toLocaleString()}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};
