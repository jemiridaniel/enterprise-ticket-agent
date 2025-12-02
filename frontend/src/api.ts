export interface ThreadMessage {
  id: string;
  role: "user" | "agent";
  content: string;
  timestamp: string;
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
}

export interface TicketThreadResponse {
  ticket_id: string;
  subject: string;
  description: string;
  severity: string;
  user_upn?: string | null;
  created_at: string;

  /** PRIMARY FIELDS FROM BACKEND */
  thread: ThreadMessage[];

  /** Secondary optional fields */
  suggested_actions: SuggestedAction[];
  followup_questions: FollowupQuestion[];
  similar_incidents: SimilarIncident[];
}
