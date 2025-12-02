from typing import List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field


# ---------- Core structures ----------

class SuggestedAction(BaseModel):
    title: str
    steps: List[str]


class FollowupQuestion(BaseModel):
    text: str


class SimilarIncident(BaseModel):
    ticket_id: Optional[str] = None
    subject: Optional[str] = None
    description: Optional[str] = None
    similarity_score: Optional[float] = None


class TicketMessage(BaseModel):
    role: Literal["user", "agent"]
    content: str
    # Accept either a datetime or string – frontend will handle formatting
    timestamp: datetime | str


# ---------- Request models ----------

class TicketCreateRequest(BaseModel):
    subject: str
    description: str
    user_upn: str = Field(..., description="User's UPN or email")
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class FollowupRequest(BaseModel):
    message: str = Field(..., description="User follow-up message text")


# ---------- Response / view models ----------

class TicketResponse(BaseModel):
    """
    Returned immediately when a new ticket is created.
    Contains the first AI answer + structured actions + questions + thread.
    """
    ticket_id: str
    subject: str
    description: str
    user_upn: str
    severity: str
    status: Literal["open", "closed"] = "open"

    answer: str
    suggested_actions: List[SuggestedAction]
    followup_questions: List[FollowupQuestion]
    similar_incidents: List[SimilarIncident] = []

    thread: List[TicketMessage]


class TicketHistoryItem(BaseModel):
    """
    Lightweight item for the left-hand 'Ticket History' list.
    """
    ticket_id: str
    subject: str
    severity: str
    status: Literal["open", "closed"] = "open"
    created_at: datetime | str


class TicketThreadResponse(BaseModel):
    """
    Full thread view for a single ticket.
    Used when loading /tickets/{id}/thread and when posting follow-ups.
    """
    ticket_id: str
    subject: str
    description: str
    severity: str
    status: Literal["open", "closed"] = "open"

    answer: str
    suggested_actions: List[SuggestedAction]
    followup_questions: List[FollowupQuestion]

    thread: List[TicketMessage]
    similar_incidents: List[SimilarIncident] = []
