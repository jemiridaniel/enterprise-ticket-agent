from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import uuid4
import json
import re

from ..models.tickets import (
    TicketCreateRequest,
    TicketResponse,
    TicketHistoryItem,
    TicketThreadResponse,
    SuggestedAction,
    FollowupQuestion,
    TicketMessage,
    SimilarIncident,
)
from .vector_service import vector_store
from .llm_service import call_llm


def _now_iso() -> str:
    """Return current UTC time as ISO string with Z."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def generate_ticket_id() -> str:
    """Generate a simple ticket id like TCK-ABC12345."""
    return f"TCK-{uuid4().hex[:8].upper()}"


# ---------- System prompt for the IT helpdesk agent ----------

IT_HELPDESK_SYSTEM_PROMPT = """
You are an expert IT support engineer in a corporate environment
(Microsoft 365, Azure AD, Teams, Exchange Online, Windows, network & printers).

You MUST always:
- Ask a few clarifying questions WHEN NEEDED, but still propose concrete next steps.
- Give step-by-step instructions that a Level 1 helpdesk engineer can follow.
- For M365/Teams/Exchange/Intune, prefer using the latest Microsoft admin centers
  (Entra admin center, Teams admin center, M365 admin center, Intune).
- If a scenario is ambiguous, give branching instructions:
  "If A, do X. If B, do Y."

You MUST reply in this STRICT JSON format (no extra keys, no commentary):

{
  "answer": "Short overview answer in 2–4 sentences. Mention key tools/portals.",
  "suggested_actions": [
    {
      "title": "Action title",
      "steps": [
        "Step 1...",
        "Step 2...",
        "Step 3..."
      ]
    }
  ],
  "followup_questions": [
    { "text": "Clarifying question 1?" },
    { "text": "Clarifying question 2?" }
  ]
}

Rules:
- Do NOT include any date text like "Invalid Date".
- Do NOT wrap the JSON in backticks.
- Do NOT include any other top-level fields.
"""


# ---------- LLM helper ----------

def _parse_llm_jsonish(raw: str) -> dict:
    """
    Try to extract the JSON object from the LLM response.
    If parsing fails, wrap whole text as {"answer": raw, ...}.
    """
    # Try to locate the first { ... } block
    match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
    candidate = match.group(0) if match else raw

    try:
        data = json.loads(candidate)
    except Exception:
        # fallback: just put everything into answer
        return {
            "answer": raw.strip(),
            "suggested_actions": [],
            "followup_questions": [],
        }

    # Ensure keys exist
    if "answer" not in data:
        data["answer"] = candidate.strip()

    if "suggested_actions" not in data or not isinstance(
        data["suggested_actions"], list
    ):
        data["suggested_actions"] = []

    if "followup_questions" not in data or not isinstance(
        data["followup_questions"], list
    ):
        data["followup_questions"] = []

    return data


def _build_messages_for_new_ticket(
    req: TicketCreateRequest,
    similar_incidents: List[SimilarIncident],
) -> List[dict]:
    """
    Build LLM messages for the initial ticket.
    """
    system_msg = {"role": "system", "content": IT_HELPDESK_SYSTEM_PROMPT}

    similar_block_lines: List[str] = []
    if similar_incidents:
        similar_block_lines.append("We have some similar past incidents:\n")
        for inc in similar_incidents:
            similar_block_lines.append(
                f"- Ticket {inc.ticket_id or 'N/A'} | Subject: {inc.subject or ''}"
            )
            if inc.description:
                similar_block_lines.append(
                    f"  Summary: {inc.description[:220]}..."
                )
        similar_block_lines.append("")

    similar_block = "\n".join(similar_block_lines)

    user_content = f"""
New support ticket:

Subject: {req.subject}
Description: {req.description}
User: {req.user_upn}
Severity: {req.severity}

{similar_block}

Please respond in the STRICT JSON format described earlier.
""".strip()

    user_msg = {"role": "user", "content": user_content}

    return [system_msg, user_msg]


def _build_messages_for_followup(
    ticket_subject: str,
    ticket_description: str,
    history_messages: List[TicketMessage],
    new_user_message: str,
    similar_incidents: List[SimilarIncident],
) -> List[dict]:
    """
    Build LLM messages for a follow-up.
    We include a brief summary of the ticket and recent conversation turns.
    """
    system_msg = {"role": "system", "content": IT_HELPDESK_SYSTEM_PROMPT}

    # Build a condensed history (last few turns)
    history_lines: List[str] = []
    for m in history_messages[-6:]:
        prefix = "USER" if m.role == "user" else "AGENT"
        history_lines.append(f"{prefix}: {m.content}")
    history_block = "\n".join(history_lines) if history_lines else "None yet."

    similar_block_lines: List[str] = []
    if similar_incidents:
        similar_block_lines.append("Similar incidents in the knowledge base:\n")
        for inc in similar_incidents:
            similar_block_lines.append(
                f"- Ticket {inc.ticket_id or 'N/A'} | Subject: {inc.subject or ''}"
            )
            if inc.description:
                similar_block_lines.append(
                    f"  Summary: {inc.description[:220]}..."
                )
        similar_block_lines.append("")
    similar_block = "\n".join(similar_block_lines)

    user_content = f"""
Follow-up on an existing ticket.

Ticket subject: {ticket_subject}
Initial description: {ticket_description}

Recent conversation:
{history_block}

New user message:
{new_user_message}

{similar_block}

Please respond in the STRICT JSON format described earlier.
""".strip()

    return [system_msg, {"role": "user", "content": user_content}]


# ---------- Public orchestrator functions ----------


async def handle_ticket(req: TicketCreateRequest) -> TicketResponse:
    """
    Orchestrate a new ticket:
      - generate ticket_id
      - store ticket root
      - call LLM for answer + actions + questions
      - store first user + agent messages
      - return TicketResponse (including thread)
    """
    ticket_id = generate_ticket_id()
    created_at = _now_iso()

    # 1) Similar incidents
    similar_raw = vector_store.query_similar(req.description, k=5)
    similar_incidents: List[SimilarIncident] = [
        SimilarIncident(
            ticket_id=sr.get("ticket_id"),
            subject=sr.get("subject"),
            description=sr.get("description"),
            similarity_score=sr.get("similarity_score"),
        )
        for sr in similar_raw
    ]

    # 2) Call LLM
    messages = _build_messages_for_new_ticket(req, similar_incidents)
    llm_raw = await call_llm(messages)
    parsed = _parse_llm_jsonish(llm_raw)

    answer_text: str = parsed.get("answer", "").strip()

    suggested_actions: List[SuggestedAction] = []
    for a in parsed.get("suggested_actions", []):
        suggested_actions.append(
            SuggestedAction(
                title=a.get("title", "Action"),
                steps=a.get("steps", []),
            )
        )

    followup_questions: List[FollowupQuestion] = []
    for q in parsed.get("followup_questions", []):
        followup_questions.append(
            FollowupQuestion(text=q.get("text", "").strip())
        )

    # 3) Persist ticket + first messages in vector store
    vector_store.add_ticket_root(
        ticket_id=ticket_id,
        subject=req.subject,
        description=req.description,
        user_upn=req.user_upn,
        severity=req.severity,
        status="open",
        created_at=created_at,
    )

    # store first user + agent messages as separate docs
    vector_store.append_message(
        ticket_id=ticket_id,
        role="user",
        content=req.description,
        created_at=created_at,
    )
    vector_store.append_message(
        ticket_id=ticket_id,
        role="agent",
        content=answer_text,
        created_at=_now_iso(),
    )

    # Build thread as returned to UI
    thread: List[TicketMessage] = [
        TicketMessage(
            role="user",
            content=req.description,
            timestamp=created_at,
        ),
        TicketMessage(
            role="agent",
            content=answer_text,
            timestamp=_now_iso(),
        ),
    ]

    return TicketResponse(
        ticket_id=ticket_id,
        subject=req.subject,
        description=req.description,
        user_upn=req.user_upn,
        severity=req.severity,
        status="open",
        answer=answer_text,
        suggested_actions=suggested_actions,
        followup_questions=followup_questions,
        similar_incidents=similar_incidents,
        thread=thread,
    )


async def list_ticket_history(limit: int = 50) -> List[TicketHistoryItem]:
    """
    Return the list of tickets for the history sidebar.
    """
    items_raw = vector_store.list_tickets(limit=limit)
    history: List[TicketHistoryItem] = []

    for item in items_raw:
        created_at = item.get("created_at", _now_iso())

        history.append(
            TicketHistoryItem(
                ticket_id=item.get("ticket_id"),
                subject=item.get("subject", ""),
                severity=item.get("severity", "medium"),
                status=item.get("status", "open"),
                created_at=created_at,
            )
        )

    return history


async def get_ticket_thread(ticket_id: str) -> Optional[TicketThreadResponse]:
    """
    Load the full thread for one ticket.
    If ticket not found, return None (router will turn into 404).
    """
    data = vector_store.get_ticket_and_messages(ticket_id)
    ticket_meta = data.get("ticket")
    messages_raw = data.get("messages", [])

    if not ticket_meta:
        return None

    subject = ticket_meta.get("subject", "")
    description = ticket_meta.get("description", "")
    severity = ticket_meta.get("severity", "medium")
    status = ticket_meta.get("status", "open")

    # Build thread from stored messages
    thread: List[TicketMessage] = []
    for m in messages_raw:
        thread.append(
            TicketMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=m.get("created_at", _now_iso()),
            )
        )

    # Re-ask the LLM for a summary + next actions based on the conversation
    # (this keeps answer/suggested_actions/followup_questions fresh)
    similar_raw = vector_store.query_similar(description, k=5)
    similar_incidents: List[SimilarIncident] = [
        SimilarIncident(
            ticket_id=sr.get("ticket_id"),
            subject=sr.get("subject"),
            description=sr.get("description"),
            similarity_score=sr.get("similarity_score"),
        )
        for sr in similar_raw
    ]

    messages = _build_messages_for_followup(
        ticket_subject=subject,
        ticket_description=description,
        history_messages=thread,
        new_user_message="(No new message – just summarize current state and propose next actions.)",
        similar_incidents=similar_incidents,
    )
    llm_raw = await call_llm(messages)
    parsed = _parse_llm_jsonish(llm_raw)

    answer_text: str = parsed.get("answer", "").strip()

    suggested_actions: List[SuggestedAction] = []
    for a in parsed.get("suggested_actions", []):
        suggested_actions.append(
            SuggestedAction(
                title=a.get("title", "Action"),
                steps=a.get("steps", []),
            )
        )

    followup_questions: List[FollowupQuestion] = []
    for q in parsed.get("followup_questions", []):
        followup_questions.append(
            FollowupQuestion(text=q.get("text", "").strip())
        )

    return TicketThreadResponse(
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        severity=severity,
        status=status,
        answer=answer_text,
        suggested_actions=suggested_actions,
        followup_questions=followup_questions,
        thread=thread,
        similar_incidents=similar_incidents,
    )


async def handle_followup(ticket_id: str, user_message: str) -> TicketThreadResponse:
    """
    Append a follow-up message to the ticket, call LLM again,
    and return the updated thread.
    """
    # 1) Load ticket + existing messages
    data = vector_store.get_ticket_and_messages(ticket_id)
    ticket_meta = data.get("ticket")
    messages_raw = data.get("messages", [])

    if not ticket_meta:
        raise ValueError(f"Ticket {ticket_id} not found")

    subject = ticket_meta.get("subject", "")
    description = ticket_meta.get("description", "")
    severity = ticket_meta.get("severity", "medium")
    status = ticket_meta.get("status", "open")

    # Build current thread objects
    thread: List[TicketMessage] = []
    for m in messages_raw:
        thread.append(
            TicketMessage(
                role=m.get("role", "user"),
                content=m.get("content", ""),
                timestamp=m.get("created_at", _now_iso()),
            )
        )

    # Append the new user message to both vector store and thread
    now_ts = _now_iso()
    vector_store.append_message(ticket_id, "user", user_message, created_at=now_ts)
    thread.append(
        TicketMessage(
            role="user",
            content=user_message,
            timestamp=now_ts,
        )
    )

    # 2) Similar incidents based on latest user message
    similar_raw = vector_store.query_similar(user_message, k=5)
    similar_incidents: List[SimilarIncident] = [
        SimilarIncident(
            ticket_id=sr.get("ticket_id"),
            subject=sr.get("subject"),
            description=sr.get("description"),
            similarity_score=sr.get("similarity_score"),
        )
        for sr in similar_raw
    ]

    # 3) Call LLM with updated conversation
    messages = _build_messages_for_followup(
        ticket_subject=subject,
        ticket_description=description,
        history_messages=thread,
        new_user_message=user_message,
        similar_incidents=similar_incidents,
    )
    llm_raw = await call_llm(messages)
    parsed = _parse_llm_jsonish(llm_raw)

    answer_text: str = parsed.get("answer", "").strip()

    suggested_actions: List[SuggestedAction] = []
    for a in parsed.get("suggested_actions", []):
        suggested_actions.append(
            SuggestedAction(
                title=a.get("title", "Action"),
                steps=a.get("steps", []),
            )
        )

    followup_questions: List[FollowupQuestion] = []
    for q in parsed.get("followup_questions", []):
        followup_questions.append(
            FollowupQuestion(text=q.get("text", "").strip())
        )

    # 4) Persist agent reply as a message
    agent_ts = _now_iso()
    vector_store.append_message(ticket_id, "agent", answer_text, created_at=agent_ts)
    thread.append(
        TicketMessage(
            role="agent",
            content=answer_text,
            timestamp=agent_ts,
        )
    )

    return TicketThreadResponse(
        ticket_id=ticket_id,
        subject=subject,
        description=description,
        severity=severity,
        status=status,
        answer=answer_text,
        suggested_actions=suggested_actions,
        followup_questions=followup_questions,
        thread=thread,
        similar_incidents=similar_incidents,
    )
