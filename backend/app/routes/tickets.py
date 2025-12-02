from typing import List

from fastapi import APIRouter, HTTPException

from ..models.tickets import (
    TicketCreateRequest,
    TicketResponse,
    TicketHistoryItem,
    TicketThreadResponse,
    FollowupRequest,
)
from ..services.agent_orchestrator import (
    handle_ticket,
    list_ticket_history,
    get_ticket_thread,
    handle_followup,
)
from ..services.vector_service import vector_store

router = APIRouter(prefix="/tickets", tags=["tickets"])


# ---------- Create ticket ----------

@router.post("/", response_model=TicketResponse)
async def create_ticket(req: TicketCreateRequest) -> TicketResponse:
    """
    Create a new ticket:
      - store root ticket + initial messages
      - call LLM
      - return structured response + thread
    """
    try:
        return await handle_ticket(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Ticket history (left sidebar) ----------

@router.get("/", response_model=List[TicketHistoryItem])
async def get_ticket_history(limit: int = 50) -> List[TicketHistoryItem]:
    """
    Return the latest tickets to populate the Ticket History list.
    """
    try:
        return await list_ticket_history(limit=limit)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Thread view for a single ticket ----------

@router.get("/{ticket_id}/thread", response_model=TicketThreadResponse)
async def get_thread(ticket_id: str) -> TicketThreadResponse:
    """
    Load the full conversation + AI answer for a single ticket.
    """
    try:
        thread = await get_ticket_thread(ticket_id)
        if thread is None:
            raise HTTPException(status_code=404, detail="Ticket not found")
        return thread
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Follow-up (chat-style) ----------

@router.post("/{ticket_id}/followup", response_model=TicketThreadResponse)
async def post_followup(ticket_id: str, body: FollowupRequest) -> TicketThreadResponse:
    """
    Append a follow-up question / message to an existing ticket,
    call the LLM again, and return the updated thread.
    """
    try:
        return await handle_followup(ticket_id, body.message)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ---------- Close ticket ----------

@router.post("/{ticket_id}/close")
async def close_ticket_route(ticket_id: str):
    """
    Mark the ticket as closed. The UI can use this to disable follow-ups.
    """
    try:
        vector_store.close_ticket(ticket_id)
        return {"ticket_id": ticket_id, "status": "closed"}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
