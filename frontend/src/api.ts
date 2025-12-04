export interface ThreadMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  created_at: string;   // backend uses created_at, NOT timestamp
}

export interface SimilarIncident {
  incident_id: string;
  subject: string;
  description: string;
  similarity_score: number;
}

export interface TicketThreadResponse {
  ticket_id: string;
  subject: string;
  description: string;
  severity: string;
  user_upn?: string | null;
  created_at: string;

  /** Messages from backend */
  thread: ThreadMessage[];
  messages?: ThreadMessage[];

  /** Arrays of strings, NOT objects */
  suggested_actions: string[];
  questions_for_user: string[];

  similar_incidents: SimilarIncident[];
}