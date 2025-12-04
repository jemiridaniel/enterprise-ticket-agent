import React from "react";
import type { TicketThreadResponse } from "../api";

interface TicketDetailProps {
  thread: TicketThreadResponse | null;
  onSendFollowup: (ticketId: string, message: string) => Promise<void>;
}

export const TicketDetail: React.FC<TicketDetailProps> = ({
  thread,
  onSendFollowup,
}) => {
  const [followupText, setFollowupText] = React.useState("");

  if (!thread) {
    return (
      <div className="p-4 text-sm text-gray-500">
        Select a ticket to view details.
      </div>
    );
  }

  const handleSend = async () => {
    if (!followupText.trim()) return;
    await onSendFollowup(thread.ticket_id, followupText.trim());
    setFollowupText("");
  };

  const safeMessages = thread.thread || thread.messages || [];

  return (
    <div className="flex flex-col h-full border-l border-gray-200">
      {/* Header */}
      <div className="px-4 py-3 border-b border-gray-200">
        <h2 className="text-base font-semibold">{thread.subject}</h2>
        <p className="text-xs text-gray-500">
          Ticket #{thread.ticket_id.slice(0, 8)} • Severity:{" "}
          <span className="font-medium">{thread.severity}</span>
        </p>
      </div>

      {/* Conversation */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-3 bg-gray-50">
        {safeMessages.map((m) => (
          <div
            key={m.id}
            className={`max-w-[80%] rounded-lg px-3 py-2 text-sm shadow-sm ${
              m.role === "agent"
                ? "bg-white border border-blue-100 self-start"
                : "bg-blue-600 text-white ml-auto"
            }`}
          >
            <div className="text-[10px] opacity-60 mb-1">
              {m.role === "agent" ? "Agent" : "User"}
            </div>
            <div className="whitespace-pre-wrap">{m.content}</div>
            <div className="text-[9px] opacity-40 mt-1">
              {new Date(m.created_at).toLocaleString()}
            </div>
          </div>
        ))}
      </div>

      {/* Questions for the User */}
      {thread.questions_for_user?.length > 0 && (
        <div className="px-4 py-3 border-t bg-white">
          <h3 className="text-xs font-semibold text-gray-700 mb-1">
            Questions for the user
          </h3>
          <ul className="list-disc list-inside text-xs text-gray-700 space-y-1">
            {thread.questions_for_user.map((q, idx) => (
              <li key={idx}>{q}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Suggested Actions */}
      {thread.suggested_actions?.length > 0 && (
        <div className="px-4 py-3 border-t bg-white">
          <h3 className="text-xs font-semibold text-gray-700 mb-1">
            Suggested Actions
          </h3>
          <ul className="list-disc list-inside text-xs text-gray-700 space-y-1">
            {thread.suggested_actions.map((step, idx) => (
              <li key={idx}>{step}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Follow-up Input */}
      <div className="px-4 py-3 border-t bg-white">
        <label className="block text-xs font-medium text-gray-700 mb-1">
          Add follow-up message
        </label>
        <textarea
          className="w-full text-sm border border-gray-300 rounded-md p-2 mb-2"
          rows={2}
          value={followupText}
          onChange={(e) => setFollowupText(e.target.value)}
        />
        <div className="flex justify-end">
          <button
            onClick={handleSend}
            disabled={!followupText.trim()}
            className="px-3 py-1.5 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            Send Follow-up
          </button>
        </div>
      </div>
    </div>
  );
};
