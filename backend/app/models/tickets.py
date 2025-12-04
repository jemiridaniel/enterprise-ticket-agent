from typing import List, Literal, Optional
from datetime import datetime
from pydantic import BaseModel, Field


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
    timestamp: datetime | str


# -------- Request --------

class TicketCreateRequest(BaseModel):
    subject: str
    description: str
    user_upn: Optional[str] = None
    severity: Literal["low", "medium", "high", "critical"] = "medium"


class FollowupRequest(BaseModel):
    message: str


# -------- Response Models --------

class TicketResponse(BaseModel):
    ticket_id: str
    subject: str
    description: str
    user_upn: Optional[str]
    severity: str
    status: Literal["open", "closed"] = "open"

    answer: str
    suggested_actions: List[SuggestedAction]
    followup_questions: List[FollowupQuestion]
    similar_incidents: List[SimilarIncident]

    thread: List[TicketMessage]


class TicketHistoryItem(BaseModel):
    ticket_id: str
    subject: str
    severity: str
    status: Literal["open", "closed"] = "open"
    created_at: datetime | str


class TicketThreadResponse(BaseModel):
    ticket_id: str
    subject: str
    description: str
    severity: str
    status: Literal["open", "closed"] = "open"

    answer: str
    suggested_actions: List[SuggestedAction]
    followup_questions: List[FollowupQuestion]
    similar_incidents: List[SimilarIncident]

    thread: List[TicketMessage]
